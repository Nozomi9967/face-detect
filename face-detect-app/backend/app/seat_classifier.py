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

# ─── 座位区域定义（基于图像坐标的比例，归一化到0-1）───
# 布局：后排（上）← 前排（下）
#     左      中      右
SEAT_ZONES = {
    "posterior_left":  {"x_range": (0.00, 0.33), "y_range": (0.00, 0.50), "label": "后排左"},
    "posterior_right": {"x_range": (0.33, 0.66), "y_range": (0.00, 0.50), "label": "后排中"},
    "after_the_middle":{"x_range": (0.66, 1.00), "y_range": (0.00, 0.50), "label": "后排右"},
    "co_driver":       {"x_range": (0.00, 0.50), "y_range": (0.50, 1.00), "label": "副驾"},
    "master_driver":   {"x_range": (0.50, 1.00), "y_range": (0.50, 1.00), "label": "主驾"},
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

# 中文字体路径
FONT_PATHS = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
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
    """基于人脸框中心坐标的规则座位分类"""

    @staticmethod
    def classify(bbox, img_w: int, img_h: int) -> str:
        cx = (bbox[0] + bbox[2]) / 2 / img_w
        cy = (bbox[1] + bbox[3]) / 2 / img_h
        for seat_id, zone in SEAT_ZONES.items():
            xr = zone["x_range"]
            yr = zone["y_range"]
            if xr[0] <= cx <= xr[1] and yr[0] <= cy <= yr[1]:
                return seat_id
        return "master_driver"

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
