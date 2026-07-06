"""
人脸识别引擎
使用纯 OpenCV 离线方案：Haar 检测 + 像素统计特征
无需下载任何外部模型文件
"""

import numpy as np
import cv2
from typing import Optional
from collections import defaultdict


class FaceRecognizer:
    """离线人脸特征匹配（纯OpenCV实现）"""

    def __init__(self):
        self.available = True  # Haar + 像素特征始终可用
        self._lbph_cascade = None

    def _get_cascade(self):
        """懒加载 Haar Cascade"""
        if self._lbph_cascade is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._lbph_cascade = cv2.CascadeClassifier(cascade_path)
        return self._lbph_cascade

    def extract_embedding(self, image: np.ndarray, bbox: list[float]) -> Optional[np.ndarray]:
        """
        提取人脸特征向量（128维）
        方法：灰度化 → 缩小到16x16 → 展平 → L2归一化
        """
        try:
            x1, y1, x2, y2 = map(int, bbox)
            h_img, w_img = image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_img, x2), min(h_img, y2)

            if x2 <= x1 or y2 <= y1:
                return None

            face_roi = image[y1:y2, x1:x2]
            if face_roi.size == 0:
                return None

            # 缩放 + 灰度
            face_resized = cv2.resize(face_roi, (16, 16))
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

            # 直方图均衡化（光照归一化）
            gray = cv2.equalizeHist(gray)

            # 展平为特征向量并归一化
            emb = gray.astype(np.float32).flatten()
            norm = np.linalg.norm(emb)
            if norm > 1e-6:
                emb = emb / norm
            else:
                return None

            return emb

        except Exception:
            return None

    @staticmethod
    def cosine_similarity(emb1: Optional[np.ndarray], emb2: Optional[np.ndarray]) -> float:
        if emb1 is None or emb2 is None:
            return 0.0
        return float(np.dot(emb1, emb2))

    def match_faces_across_images(
        self,
        all_faces: list[dict],
        similarity_threshold: float = 0.5
    ) -> list[dict]:
        """
        跨图片匹配人脸，分配统一ID
        """
        by_image = defaultdict(list)
        for i, face in enumerate(all_faces):
            by_image[face["image_id"]].append(i)

        person_db: dict[int, list[np.ndarray]] = {}
        next_person_id = 1

        for img_id in sorted(by_image.keys()):
            for idx in by_image[img_id]:
                face = all_faces[idx]
                if face.get("embedding") is None:
                    face["person_id"] = next_person_id
                    next_person_id += 1
                    continue

                best_match = None
                best_sim = -1.0
                for pid, embeddings in person_db.items():
                    for emb in embeddings:
                        sim = self.cosine_similarity(face["embedding"], emb)
                        if sim > best_sim:
                            best_sim = sim
                            best_match = pid

                if best_match is not None and best_sim >= similarity_threshold:
                    face["person_id"] = best_match
                    person_db[best_match].append(face["embedding"])
                else:
                    face["person_id"] = next_person_id
                    person_db[next_person_id] = [face["embedding"]]
                    next_person_id += 1

        return all_faces
