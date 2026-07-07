"""
人脸检测引擎
优先使用 YOLOv8-face，若模型不可用则回退到 OpenCV Haar Cascade
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional


class FaceDetector:
    """人脸检测器 - 支持 YOLOv8-face 和 OpenCV Haar Cascade"""

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        self.backend = "haar"  # 默认使用 Haar Cascade
        self.yolo_model = None
        self.haar_cascade = None
        self._init_detector(model_path)

    def _init_detector(self, model_path: Optional[str]):
        """初始化检测器，优先YOLOv8，fallback到Haar"""
        try:
            from ultralytics import YOLO

            # 检查模型文件（优先lindevs的face模型，再通用yolo）
            candidates = [
                model_path,
                "yolov8n-face-lindevs.pt",
                "yolov8n-face.pt",
            ]
            model_file = None
            for candidate in candidates:
                if candidate and Path(candidate).exists():
                    model_file = candidate
                    break

            if model_file:
                self.yolo_model = YOLO(model_file)
                self.backend = "yolo"
                print(f"[FaceDetector] YOLOv8-face 就绪: {model_file}")
                return

            print("[FaceDetector] 未找到face模型，使用 Haar Cascade fallback")
        except ImportError:
            print("[FaceDetector] ultralytics 未安装，使用 Haar Cascade")

        self._init_haar()

    def _init_haar(self):
        """初始化 OpenCV Haar Cascade 人脸检测器"""
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.haar_cascade = cv2.CascadeClassifier(cascade_path)
        if self.haar_cascade.empty():
            raise RuntimeError(f"无法加载 Haar Cascade 模型: {cascade_path}")
        print("[FaceDetector] Haar Cascade 人脸检测器就绪")

    def detect(self, image: np.ndarray) -> list[dict]:
        """
        检测图像中的人脸

        返回: [{"bbox": [x1,y1,x2,y2], "conf": float}, ...]
        bbox 为像素坐标，x1<y1 左上，x2>y2 右下
        """
        if self.backend == "yolo" and self.yolo_model is not None:
            return self._detect_yolo(image)
        else:
            return self._detect_haar(image)

    def _detect_yolo(self, image: np.ndarray) -> list[dict]:
        """YOLOv8-face 检测"""
        results = self.yolo_model.predict(
            source=image,
            conf=self.conf_threshold,
            verbose=False,
            device="cpu",
        )

        faces = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                faces.append({
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "conf": conf
                })

        faces.sort(key=lambda f: f["bbox"][0])
        return faces

    def _detect_haar(self, image: np.ndarray) -> list[dict]:
        """
        OpenCV Haar Cascade 检测

        Haar 不返回置信度，使用检测面积占比作为伪置信度
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 多尺度检测
        rects = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        faces = []
        h_img, w_img = image.shape[:2]
        img_area = h_img * w_img

        for (x, y, w, h) in rects:
            # 面积占比作为置信度代理
            area_ratio = (w * h) / img_area
            conf = min(0.5 + area_ratio * 10, 0.99)  # 映射到 0.5-0.99

            faces.append({
                "bbox": [float(x), float(y), float(x + w), float(y + h)],
                "conf": float(conf)
            })

        faces.sort(key=lambda f: f["bbox"][0])
        return faces

    @property
    def is_yolo(self) -> bool:
        """当前是否使用 YOLOv8 后端"""
        return self.backend == "yolo"
