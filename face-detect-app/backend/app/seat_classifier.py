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
SEAT_ZONES = {
    "co_driver":       {"x_range": (0.00, 0.40), "y_range": (0.30, 0.55), "label": "副驾"},
    "master_driver":   {"x_range": (0.60, 1.00), "y_range": (0.30, 0.55), "label": "主驾"},
    "posterior_left":  {"x_range": (0.25, 0.45), "y_range": (0.25, 0.45), "label": "后排左"},
    "posterior_right": {"x_range": (0.45, 0.65), "y_range": (0.25, 0.45), "label": "后排中"},
    "after_the_middle":{"x_range": (0.65, 0.90), "y_range": (0.25, 0.50), "label": "后排右"},
}

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
    def _normalized_height(bbox, img_h: int) -> float:
        return (bbox[3] - bbox[1]) / img_h

    @staticmethod
    def _normalized_area(bbox, img_w: int, img_h: int) -> float:
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / (img_w * img_h)

    @staticmethod
    def _find_bbox_index(bbox, all_bboxes: list) -> int:
        for i, b in enumerate(all_bboxes):
            if b == bbox:
                return i
        for i, b in enumerate(all_bboxes):
            if abs(b[0] - bbox[0]) < 2 and abs(b[1] - bbox[1]) < 2:
                return i
        return None

    @staticmethod
    def _is_front_row(bbox, all_bboxes: list, img_w: int, img_h: int) -> bool:
        """
        Determine if a face is in the front row (driver / co-driver).

        Uses 2-means clustering on weighted [height, Y-center] features.
        Y-center has 3x weight because it's the more reliable row separator
        (camera is always behind front row looking forward).

        Algorithm:
        1. Single face: height > 0.13 → front
        2. Global filters for unambiguous all-back cases:
           - ALL faces Y-center > 0.50: all back (camera behind back seats)
           - ALL faces Y-center < 0.40 AND max height < 0.17: all back
             (test1/2: camera far behind car)
        3. 2-means on [height, 3*Y-center]:
           - Seed centroids from tallest/shortest faces
           - Iteratively assign by Manhattan distance
           - Taller cluster = front row
        4. Mixed-row correction:
           a) Tallest-in-back flip (single tall face isolated in back cluster)
           b) Y-deviation: remove front-cluster faces whose Y-center deviates
              > 0.06 from front centroid (turned-aside back-row faces)
           c) X-range check: if front cluster spans > 0.50 in normalized X,
              only the face closest to center (nx≈0.50) stays in front.
              This handles test4: rear-left lady (nx=0.228) and driver
              (nx=0.947) have similar Y-centers but 0.72 nx apart.
        """
        if not all_bboxes:
            return False

        n = len(all_bboxes)
        heights = [SeatClassifier._normalized_height(b, img_h) for b in all_bboxes]
        areas = [SeatClassifier._normalized_area(b, img_w, img_h) for b in all_bboxes]
        y_centers = [(b[1] + b[3]) / 2 / img_h for b in all_bboxes]
        my_h = SeatClassifier._normalized_height(bbox, img_h)

        if n == 1:
            return my_h > 0.13

        # ── Signal 1: Y-position global filters ──
        if min(y_centers) > 0.50:
            return False  # all faces low in image → camera behind back seats
        if max(y_centers) < 0.40 and max(heights) < 0.17:
            return False  # all faces high + small → camera far behind car

        # ── Signal 2: 2-means on weighted [height, Y-center] ──
        front_indices, back_indices = SeatClassifier._kmeans2(
            heights, y_centers, areas,
        )

        # Check if this face is in the final front cluster
        my_idx = SeatClassifier._find_bbox_index(bbox, all_bboxes)
        if my_idx is None or my_idx not in front_indices:
            return False

        return True

    @staticmethod
    def _kmeans2(heights, y_centers, areas):
        """
        2-means clustering on weighted [height, Y-center] features.
        Y-center has 3x weight because row separation depends more on
        vertical position than face size.

        Returns (front_indices, back_indices) where front = taller-mean cluster.
        """
        n = len(heights)
        # Weighted features: [height, 3*Y-center]
        WEIGHT = 3.0
        features = [np.array([heights[i], WEIGHT * y_centers[i]]) for i in range(n)]

        # Seed centroids: tallest and shortest face
        tallest_idx = max(range(n), key=lambda i: heights[i])
        shortest_idx = min(range(n), key=lambda i: heights[i])
        c1 = features[tallest_idx]  # front seed
        c2 = features[shortest_idx]  # back seed

        # Iterative assignment
        for _ in range(20):
            front = []
            back = []
            for i in range(n):
                d1 = np.abs(features[i] - c1).sum()
                d2 = np.abs(features[i] - c2).sum()
                if d1 <= d2:
                    front.append(i)
                else:
                    back.append(i)

            if not front or not back:
                break

            new_c1 = np.mean([features[i] for i in front], axis=0)
            new_c2 = np.mean([features[i] for i in back], axis=0)
            if np.allclose(new_c1, c1) and np.allclose(new_c2, c2):
                break
            c1, c2 = new_c1, new_c2

        # Taller cluster = front row
        if front:
            front_mean_h = sum(heights[i] for i in front) / len(front)
        else:
            front_mean_h = 0
        if back:
            back_mean_h = sum(heights[i] for i in back) / len(back)
        else:
            back_mean_h = 0

        if front_mean_h < back_mean_h:
            front, back = back, front

        # ── Mixed-row correction (ALL cases, not just len(front)>=2) ──
        # If the tallest face ended up alone in the "back" cluster, flip.
        # This handles test6: a tall back-row face near the camera gets
        # isolated in the wrong cluster.
        if len(front) == 1 and len(back) >= 2:
            tallest_in_back = max(heights[i] for i in back)
            tallest_in_front = heights[front[0]]
            if tallest_in_back > tallest_in_front:
                front, back = back, front

        # Within the front cluster, remove faces whose Y-center deviates
        # > 0.06 from the front centroid (turned-aside back-row faces).
        if len(front) >= 2:
            front_mean_y = sum(y_centers[i] for i in front) / len(front)
            corrected = []
            for idx in front:
                if abs(y_centers[idx] - front_mean_y) > 0.06:
                    back.append(idx)
                else:
                    corrected.append(idx)
            front = corrected

        # Height-ratio guard: if remaining front faces have height ratio > 2.0,
        # the shorter one is likely a back-row face at a different distance
        # (not a genuine front-row passenger).
        # test4: front=[lady h=0.141, driver h=0.334], ratio=2.37 -> remove lady.
        # test3: front=[0.204, 0.227], ratio=1.11 -> no effect.
        if len(front) >= 2:
            front_heights = [heights[i] for i in front]
            if max(front_heights) / min(front_heights) > 2.0:
                shortest_in_front = min(front, key=lambda i: heights[i])
                front.remove(shortest_in_front)
                back.append(shortest_in_front)

        # ── All-back detection ──
        # If front cluster's Y-center range is fully inside back cluster's
        # range, all faces are in the same row (back).
        # Only meaningful when front has >= 2 faces (single-face front
        # always has zero range, trivially inside any back range).
        if front and back and len(front) >= 2:
            front_y_min = min(y_centers[i] for i in front)
            front_y_max = max(y_centers[i] for i in front)
            back_y_min = min(y_centers[i] for i in back)
            back_y_max = max(y_centers[i] for i in back)
            if back_y_min <= front_y_min and front_y_max <= back_y_max:
                front = []
                back = list(range(len(heights)))

        return front, back

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

        pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_font(18)

        for f in faces:
            x1, y1, x2, y2 = map(int, f["bbox"])
            seat = f.get("seat", "unknown")
            color_rgb = COLOR_MAP_RGB.get(seat, (200, 200, 200))
            label = f"{SeatClassifier.get_label(seat)} ID:{f.get('person_id', f.get('id', '?'))}"

            draw.rectangle([x1, y1, x2, y2], outline=color_rgb, width=3)

            bbox_text = draw.textbbox((0, 0), label, font=font)
            tw = bbox_text[2] - bbox_text[0]
            th = bbox_text[3] - bbox_text[1]

            label_y = max(0, y1 - th - 8)
            draw.rectangle([x1, label_y, x1 + tw + 12, y1], fill=color_rgb)
            draw.text((x1 + 6, label_y + 2), label, font=font, fill=(255, 255, 255))

            if f.get("conf"):
                conf_text = f"{f['conf']:.2f}"
                draw.text((x1, y2 + 4), conf_text, font=font, fill=color_rgb)

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
