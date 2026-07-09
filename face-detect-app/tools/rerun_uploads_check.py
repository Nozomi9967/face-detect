#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run detection on all images under data/uploads and write a review report."""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR / "backend"
UPLOADS_DIR = APP_DIR / "data" / "uploads"
OUT_DIR = APP_DIR / "data" / "results" / "upload_rerun"
REPORT_CSV = APP_DIR / "data" / "upload_rerun_report.csv"
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def load_pipeline():
    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    from app.pipeline import Pipeline  # noqa: PLC0415

    return Pipeline(detector_conf=0.1, similarity_threshold=0.5, use_recognition=False)


def read_image(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path: Path, image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = ".jpg" if path.suffix.lower() in {".jpg", ".jpeg"} else ".png"
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        raise RuntimeError(f"failed_to_encode:{path.name}")
    encoded.tofile(str(path))


def main() -> None:
    pipeline = load_pipeline()
    image_paths = [
        p for p in sorted(UPLOADS_DIR.rglob("*"))
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, path in enumerate(image_paths, start=1):
        start = time.perf_counter()
        rel_path = path.relative_to(APP_DIR).as_posix()
        try:
            image = read_image(path)
            if image is None:
                raise RuntimeError("unreadable_image")
            result = pipeline.process_image(image, image_id=index - 1)
            seats = ";".join(face["seat_label"] for face in result["faces"]) or "none"
            out_name = f"upload_rerun_{index:03d}{path.suffix.lower()}"
            out_path = OUT_DIR / out_name
            write_image(out_path, result["annotated_image"])
            status = "ok"
            note = ""
            actual_faces = str(result["num_faces"])
        except Exception as exc:  # noqa: BLE001 - keep full rerun going and report failures.
            status = "error"
            note = f"{exc.__class__.__name__}:{exc}"
            seats = ""
            actual_faces = ""
            out_path = Path("")

        elapsed_ms = (time.perf_counter() - start) * 1000
        rows.append({
            "file_path": rel_path,
            "actual_faces": actual_faces,
            "actual_seats": seats,
            "status": status,
            "annotated_image": out_path.relative_to(APP_DIR).as_posix() if out_path else "",
            "elapsed_ms": f"{elapsed_ms:.1f}",
            "note": note,
        })

    with REPORT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "file_path",
                "actual_faces",
                "actual_seats",
                "status",
                "annotated_image",
                "elapsed_ms",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    ok_count = sum(1 for row in rows if row["status"] == "ok")
    err_count = len(rows) - ok_count
    print(f"uploads={len(rows)}, ok={ok_count}, error={err_count}")
    print(f"report={REPORT_CSV.relative_to(APP_DIR)}")
    print(f"annotated_dir={OUT_DIR.relative_to(APP_DIR)}")


if __name__ == "__main__":
    main()
