"""
多人脸检测与座位分类引擎
技术栈：YOLOv8-face（检测）+ 像素特征匹配 + 规则（座位分类）
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from collections import defaultdict
from typing import Optional

# ─── 座位区域定义（基于真实车内俯视视角）───
# 前排人脸中心通常在 y=0.30-0.50，后排在 y=0.25-0.40
# 通过Y坐标细分为前排/后排，再通过X区分左右
SEAT_ZONES = {
    "co_driver":       {"x_range": (0.00, 0.40), "y_range": (0.30, 0.55), "label": "副驾"},
    "master_driver":   {"x_range": (0.60, 1.00), "y_range": (0.30, 0.55), "label": "主驾"},
    "posterior_left":  {"x_range": (0.25, 0.45), "y_range": (0.25, 0.45), "label": "后排左"},
    "posterior_right": {"x_range": (0.45, 0.65), "y_range": (0.25, 0.45), "label": "后排中"},
    "after_the_middle":{"x_range": (0.65, 0.90), "y_range": (0.25, 0.50), "label": "后排右"},
}

# 颜色映射 (RGB for PIL, BGR for cv2)
COLOR_MAP_RGB = {
    "posterior_left":  (255, 100, 100),
    "posterior_right": (100, 255, 100),
    "after_the_middle":(100, 100, 255),
    "co_driver":       (255, 200, 100),
    "master_driver":   (100, 200, 255),
}
COLOR_MAP_BGR = {k: (v[2], v[1], v[0]) for k, v in COLOR_MAP_RGB.items()}

# Font paths: bundled font first (works on Linux without system Chinese fonts),
# then system fonts (faster on Windows where they already exist).
_BUNDLED_FONT = str(Path(__file__).resolve().parent.parent / "fonts" / "simhei.ttf")
FONT_PATHS = [
    _BUNDLED_FONT,
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


def _get_font(size: int = 20):
    """加载中文字体"""
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


class SeatClassifier:
    """基于人脸框坐标 + 大小的规则座位分类"""

    @staticmethod
    def _bbox_key(bbox) -> tuple:
        return tuple(round(float(v), 3) for v in bbox)

    @staticmethod
    def classify(bbox, img_w: int, img_h: int, all_bboxes: list = None) -> str:
        cx = (bbox[0] + bbox[2]) / 2
        nx = cx / img_w
        is_front = SeatClassifier._is_front_row(bbox, all_bboxes, img_w, img_h)
        if is_front:
            return "co_driver" if nx < 0.50 else "master_driver"
        else:
            if nx < 0.44:
                return "posterior_left"
            elif nx < 0.56:
                return "posterior_right"
            else:
                return "after_the_middle"

    @staticmethod
    def _is_front_row(bbox, all_bboxes: list, img_w: int, img_h: int) -> bool:
        if not all_bboxes or len(all_bboxes) == 1:
            x1, y1, x2, y2 = map(float, bbox)
            nx = ((x1 + x2) / 2) / img_w
            ny = ((y1 + y2) / 2) / img_h
            width = (x2 - x1) / img_w
            area = ((x2 - x1) * (y2 - y1)) / (img_w * img_h)
            side_position = abs(nx - 0.5) >= 0.18
            front_sized = width >= 0.08 or area >= 0.010
            lower_half = ny >= 0.28
            return front_sized and (side_position or lower_half)

        n = len(all_bboxes)
        metrics = []
        for b in all_bboxes:
            x1, y1, x2, y2 = map(float, b)
            bw = max(1.0, x2 - x1)
            bh = max(1.0, y2 - y1)
            metrics.append({
                "bbox": b,
                "key": SeatClassifier._bbox_key(b),
                "nx": ((x1 + x2) / 2) / img_w,
                "ny": ((y1 + y2) / 2) / img_h,
                "w": bw / img_w,
                "area": (bw * bh) / (img_w * img_h),
            })

        y_coords = [(b[1] + b[3]) / 2 / img_h for b in all_bboxes]
        sorted_y = sorted(y_coords)
        y_span = sorted_y[-1] - sorted_y[0]

        # 车内广角图里，前排乘员通常在画面左右两侧且脸框更大；
        # 仅靠 Y 坐标会把前排误判成后排，尤其是三人/五人座舱图。
        if n >= 3:
            front_keys = SeatClassifier._front_candidates_by_position(metrics)
            if front_keys:
                return SeatClassifier._bbox_key(bbox) in front_keys

        if n >= 3 and y_span < 0.06:
            # Y集中 -> 用宽度聚类区分前排/后排
            widths = [(b[2]-b[0])/img_w for b in all_bboxes]
            sorted_w = sorted(widths)
            # 找最大相对间隙作为分界
            max_ratio = 0
            split_i = 0
            for i in range(len(sorted_w)-1):
                if sorted_w[i] > 1e-6:
                    r = sorted_w[i+1] / sorted_w[i]
                    if r > max_ratio:
                        max_ratio = r
                        split_i = i
            if max_ratio > 2.0:
                # 有宽度分层 -> 间隙右侧(更宽)的是前排
                my_w = (bbox[2]-bbox[0])/img_w
                return my_w >= sorted_w[split_i + 1] - 1e-9
            # 宽度相近 -> 后排
            return False

        if n == 2:
            if y_span > 0.12:
                my_ny = (bbox[1] + bbox[3]) / 2 / img_h
                return my_ny > (sorted_y[0] + sorted_y[-1]) / 2
            avg_w = sum((b[2]-b[0])/img_w for b in all_bboxes) / 2
            return avg_w > 0.08

        # 3+脸, Y有分层 -> K-means K=2
        c0, c1 = sorted_y[0], sorted_y[-1]
        for _ in range(20):
            g0, g1 = [], []
            for y in y_coords:
                if abs(y - c0) <= abs(y - c1):
                    g0.append(y)
                else:
                    g1.append(y)
            if not g0 or not g1:
                break
            nc0, nc1 = sum(g0)/len(g0), sum(g1)/len(g1)
            if abs(nc0-c0) < 1e-8 and abs(nc1-c1) < 1e-8:
                break
            c0, c1 = nc0, nc1

        cnt0 = sum(1 for y in y_coords if abs(y-c0) <= abs(y-c1))
        cnt1 = n - cnt0

        if cnt0 <= 2 and cnt1 > 2:
            fc = 0
        elif cnt1 <= 2 and cnt0 > 2:
            fc = 1
        elif cnt0 <= 2 and cnt1 <= 2:
            fc = 1 if c1 > c0 else 0
        else:
            avg_w = sum((b[2]-b[0])/img_w for b in all_bboxes) / n
            return avg_w > 0.06

        my_ny = (bbox[1] + bbox[3]) / 2 / img_h
        mc = 0 if abs(my_ny-c0) <= abs(my_ny-c1) else 1
        return mc == fc

    @staticmethod
    def _front_candidates_by_position(metrics: list[dict]) -> set:
        if not metrics:
            return set()

        widths = sorted(m["w"] for m in metrics)
        median_w = widths[len(widths) // 2]
        areas = sorted(m["area"] for m in metrics)
        median_area = areas[len(areas) // 2]
        median_y = sorted(m["ny"] for m in metrics)[len(metrics) // 2]

        if len(metrics) == 3:
            by_x = sorted(metrics, key=lambda m: m["nx"])
            middle = by_x[1]
            side_width_ratio = min(by_x[0]["w"], by_x[2]["w"]) / max(middle["w"], 1e-6)
            side_area_ratio = min(by_x[0]["area"], by_x[2]["area"]) / max(middle["area"], 1e-6)
            y_span = max(m["ny"] for m in metrics) - min(m["ny"] for m in metrics)
            # 三人后排横向排布时，人脸通常同一高度且大小接近。
            # 只有左右两侧明显比中间更大时，才认为它们可能是前排。
            if y_span < 0.08 and side_width_ratio < 1.35 and side_area_ratio < 1.55:
                return set()

        def score(m):
            side_score = abs(m["nx"] - 0.5)
            width_score = m["w"] / max(widths[-1], 1e-6)
            area_score = m["area"] / max(areas[-1], 1e-6)
            # 前排常常更靠下，但广角图里驾驶员脸框可能偏高，所以只作为弱信号。
            y_score = 0.12 if m["ny"] >= median_y else 0.0
            return side_score * 0.35 + width_score * 0.45 + area_score * 0.20 + y_score

        def plausible_front(m):
            side_enough = abs(m["nx"] - 0.5) >= 0.12
            size_enough = m["w"] >= median_w * 0.90 or m["area"] >= median_area * 0.90
            return side_enough and size_enough

        front = []
        left = [m for m in metrics if m["nx"] < 0.5]
        right = [m for m in metrics if m["nx"] >= 0.5]

        for group in (left, right):
            if not group:
                continue
            best = max(group, key=score)
            if plausible_front(best):
                front.append(best)

        if len(front) == 2:
            return {m["key"] for m in front}

        # 如果某侧没有候选，退化为全局挑选最多两个最像前排的人脸。
        ranked = [m for m in sorted(metrics, key=score, reverse=True) if plausible_front(m)]
        return {m["key"] for m in ranked[:2]} if len(ranked) >= 2 else set()

    @staticmethod
    def get_label(seat_id: str) -> str:
        return SEAT_ZONES.get(seat_id, {}).get("label", seat_id)

    @staticmethod
    def get_color(seat_id: str):
        return COLOR_MAP_BGR.get(seat_id, (200, 200, 200))


class FaceAnnotator:
    """使用 PIL 绘制支持中文的标注"""

    @staticmethod
    def draw(image: np.ndarray, faces: list[dict]) -> np.ndarray:
        vis = image.copy()
        h, w = vis.shape[:2]

        # 转换为 PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_font(18)

        for f in faces:
            x1, y1, x2, y2 = map(int, f["bbox"])
            seat = f.get("seat", "unknown")
            color_rgb = COLOR_MAP_RGB.get(seat, (200, 200, 200))
            label = f"{SeatClassifier.get_label(seat)} ID:{f.get('person_id', f.get('id', '?'))}"

            # 绘制矩形框
            draw.rectangle([x1, y1, x2, y2], outline=color_rgb, width=3)

            # 计算文字大小
            bbox_text = draw.textbbox((0, 0), label, font=font)
            tw = bbox_text[2] - bbox_text[0]
            th = bbox_text[3] - bbox_text[1]

            # 标签背景
            label_y = max(0, y1 - th - 8)
            draw.rectangle([x1, label_y, x1 + tw + 12, y1], fill=color_rgb)

            # 标签文字（白色）
            draw.text((x1 + 6, label_y + 2), label, font=font, fill=(255, 255, 255))

            # 置信度
            if f.get("conf"):
                conf_text = f"{f['conf']:.2f}"
                draw.text((x1, y2 + 4), conf_text, font=font, fill=color_rgb)

        # 转回 OpenCV 格式
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def draw_seat_zones(image: np.ndarray, alpha: float = 0.15) -> np.ndarray:
        vis = image.copy()
        h, w = vis.shape[:2]
        pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_font(16)

        for seat_id, zone in SEAT_ZONES.items():
            x1, x2 = int(zone["x_range"][0] * w), int(zone["x_range"][1] * w)
            y1, y2 = int(zone["y_range"][0] * h), int(zone["y_range"][1] * h)
            color_rgb = COLOR_MAP_RGB.get(seat_id, (200, 200, 200))
            draw.rectangle([x1, y1, x2, y2], fill=(*color_rgb, 80))
            draw.text((x1 + 5, y1 + 5), SeatClassifier.get_label(seat_id),
                      font=font, fill=color_rgb)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
