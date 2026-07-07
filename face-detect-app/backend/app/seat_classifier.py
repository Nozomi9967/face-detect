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

# 中文字体路径（跨平台）
FONT_PATHS = [
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
            return (bbox[2] - bbox[0]) / img_w > 0.12

        n = len(all_bboxes)
        y_coords = [(b[1] + b[3]) / 2 / img_h for b in all_bboxes]
        sorted_y = sorted(y_coords)
        y_span = sorted_y[-1] - sorted_y[0]

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
            return avg_w > 0.10

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
