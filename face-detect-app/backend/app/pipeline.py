"""
多人脸素材清洗 - 核心检测流程
整合：YOLOv8-face检测 + InsightFace特征匹配 + 规则座位分类
"""

from typing import Optional
import numpy as np
from .detector import FaceDetector
from .recognizer import FaceRecognizer
from .seat_classifier import SeatClassifier, FaceAnnotator


class Pipeline:
    """完整的人脸检测→特征匹配→座位分类→标注流程"""

    def __init__(
        self,
        detector_conf: float = 0.5,
        similarity_threshold: float = 0.5,
    ):
        self.detector = FaceDetector(conf_threshold=detector_conf)
        self.recognizer = FaceRecognizer()
        self.classifier = SeatClassifier()
        self.annotator = FaceAnnotator()

    def process_image(self, image: np.ndarray, image_id: int = 0) -> dict:
        """
        处理单张图片

        返回:
            {
                "image_id": int,
                "num_faces": int,
                "faces": [
                    {"bbox": [x1,y1,x2,y2], "conf": float, "seat": str, "person_id": int},
                    ...
                ],
                "annotated_image": np.ndarray (base64 encoded str in actual use)
            }
        """
        # 1. 人脸检测
        raw_faces = self.detector.detect(image)

        # 2. 提取人脸特征
        for face in raw_faces:
            face["embedding"] = self.recognizer.extract_embedding(image, face["bbox"])
            face["image_id"] = image_id

        # 3. 跨图片人脸匹配（分配统一ID）
        matched_faces = self.recognizer.match_faces_across_images(
            raw_faces, similarity_threshold=0.5
        )

        # 4. 座位分类
        h, w = image.shape[:2]
        for face in matched_faces:
            face["seat"] = self.classifier.classify(face["bbox"], w, h)

        # 5. 可视化标注
        annotated = self.annotator.draw(image, matched_faces)

        return {
            "image_id": image_id,
            "num_faces": len(matched_faces),
            "faces": [
                {
                    "bbox": f["bbox"],
                    "conf": f["conf"],
                    "seat": f["seat"],
                    "seat_label": SeatClassifier.get_label(f["seat"]),
                    "person_id": f["person_id"],
                }
                for f in matched_faces
            ],
            "annotated_image": annotated,
        }

    def process_batch(
        self, images: list[np.ndarray]
    ) -> tuple[list[dict], list[np.ndarray]]:
        """
        批量处理多张图片（batch processing for better ID matching）

        返回: (results_list, annotated_images)
        """
        all_faces = []
        annotated_images = []

        for i, img in enumerate(images):
            raw_faces = self.detector.detect(img)
            for face in raw_faces:
                face["embedding"] = self.recognizer.extract_embedding(img, face["bbox"])
                face["image_id"] = i
            all_faces.extend(raw_faces)

        # 跨所有图片做人脸匹配
        matched_faces = self.recognizer.match_faces_across_images(
            all_faces, similarity_threshold=0.5
        )

        # 重新按图片分组
        results = []
        for i, img in enumerate(images):
            h, w = img.shape[:2]
            img_faces = [f for f in matched_faces if f["image_id"] == i]
            for face in img_faces:
                face["seat"] = self.classifier.classify(face["bbox"], w, h)

            annotated = self.annotator.draw(img, img_faces)
            annotated_images.append(annotated)

            results.append({
                "image_id": i,
                "num_faces": len(img_faces),
                "faces": [
                    {
                        "bbox": f["bbox"],
                        "conf": f["conf"],
                        "seat": f["seat"],
                        "seat_label": SeatClassifier.get_label(f["seat"]),
                        "person_id": f["person_id"],
                    }
                    for f in img_faces
                ],
            })

        return results, annotated_images
