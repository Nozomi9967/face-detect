"""
人脸识别引擎 - 使用 InsightFace/ArcFace 做人脸特征匹配
模型已下载到 ~/.insightface/models/buffalo_l/
"""

import cv2
import numpy as np
from typing import Optional
from collections import defaultdict


class FaceRecognizer:
    """基于 InsightFace ArcFace 的人脸特征匹配"""

    def __init__(self):
        self.app = None
        self.available = False
        self._load_model()

    def _load_model(self):
        """加载 InsightFace 模型"""
        try:
            from insightface.app import FaceAnalysis

            self.app = FaceAnalysis(
                name="buffalo_l",
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self.available = True
            print("[FaceRecognizer] InsightFace ArcFace 就绪 (512维特征)")
        except Exception as e:
            self.available = False
            print(f"[FaceRecognizer] 模型加载失败: {e}")
            print("[FaceRecognizer] 降级为像素特征匹配模式")

    def extract_embedding(self, image: np.ndarray, bbox: list[float]) -> Optional[np.ndarray]:
        """提取人脸 512 维特征向量"""
        if not self.available or self.app is None:
            return self._extract_fallback(image, bbox)

        try:
            h, w = image.shape[:2]
            x1, y1, x2, y2 = bbox
            bw, bh = x2 - x1, y2 - y1
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            expand = 0.2
            x1 = max(0, int(cx - bw * (1 + expand) / 2))
            y1 = max(0, int(cy - bh * (1 + expand) / 2))
            x2 = min(w, int(cx + bw * (1 + expand) / 2))
            y2 = min(h, int(cy + bh * (1 + expand) / 2))

            face_img = image[y1:y2, x1:x2]
            if face_img.size == 0:
                return None

            faces = self.app.get(face_img)
            if len(faces) == 0:
                return None

            best_face = max(faces, key=lambda f: f.det_score)
            return best_face.normed_embedding
        except Exception:
            return None

    def _extract_fallback(self, image: np.ndarray, bbox: list[float]) -> Optional[np.ndarray]:
        """降级：像素直方图特征"""
        try:
            x1, y1, x2, y2 = map(int, bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            if x2 <= x1 or y2 <= y1:
                return None
            face_roi = image[y1:y2, x1:x2]
            if face_roi.size == 0:
                return None
            face_resized = cv2.resize(face_roi, (16, 16))
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            emb = gray.astype(np.float32).flatten()
            norm = np.linalg.norm(emb)
            return emb / norm if norm > 1e-6 else None
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
        """跨图片匹配人脸分配统一ID"""
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
