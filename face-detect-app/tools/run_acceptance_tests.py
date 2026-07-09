#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run acceptance checks on curated project images.

The script uses existing local samples only. It does not download datasets,
train models, or change API contracts. Results are written to
data/acceptance_test_records.csv so the project has a repeatable acceptance
artifact for the fixed-view rule-based version.
"""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

import cv2


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR / "backend"
DATA_DIR = APP_DIR / "data"
ACCEPTANCE_CSV = DATA_DIR / "acceptance_test_records.csv"

CURATED_CASES = [
    {
        "case_id": "TC-FIXED-001",
        "image_file": "data/curated/five_seat/five_seat_001.png",
        "mode": "single",
        "expected_faces": "5",
        "expected_seats": "主驾;副驾;后排左;后排中;后排右",
    },
    {
        "case_id": "TC-FIXED-002",
        "image_file": "data/curated/five_seat/five_seat_002.png",
        "mode": "single",
        "expected_faces": "5",
        "expected_seats": "主驾;副驾;后排左;后排中;后排右",
    },
    {
        "case_id": "TC-FIXED-003",
        "image_file": "data/curated/batch/batch_001.png",
        "mode": "single",
        "expected_faces": "unknown",
        "expected_seats": "unknown",
    },
    {
        "case_id": "TC-FIXED-004",
        "image_file": "data/curated/batch/batch_002.png",
        "mode": "single",
        "expected_faces": "unknown",
        "expected_seats": "unknown",
    },
    {
        "case_id": "TC-FIXED-005",
        "image_file": "data/curated/edge/edge_001.jpg",
        "mode": "single",
        "expected_faces": "unknown",
        "expected_seats": "unknown",
    },
    {
        "case_id": "TC-FIXED-006",
        "image_file": (
            "data/curated/batch/batch_001.png;"
            "data/curated/batch/batch_002.png;"
            "data/curated/batch/batch_003.png;"
            "data/curated/batch/batch_004.png;"
            "data/curated/batch/batch_005.png;"
            "data/curated/batch/batch_006.png"
        ),
        "mode": "batch",
        "expected_faces": "unknown",
        "expected_seats": "unknown",
    },
]

SEAT_LABEL_ORDER = ["主驾", "副驾", "后排左", "后排中", "后排右"]
FIELDNAMES = [
    "case_id",
    "image_file",
    "mode",
    "expected_faces",
    "actual_faces",
    "expected_seats",
    "actual_seats",
    "result",
    "issue_note",
    "tester",
]


def load_pipeline():
    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    from app.pipeline import Pipeline  # noqa: PLC0415

    return Pipeline(detector_conf=0.1, similarity_threshold=0.5, use_recognition=False)


def seat_summary(faces: list[dict]) -> str:
    labels = [face.get("seat_label", "") for face in faces]
    ordered = [label for label in SEAT_LABEL_ORDER if label in labels]
    extras = [label for label in labels if label and label not in ordered]
    return ";".join(ordered + extras)


def expected_faces_match(expected: str, actual: int) -> bool:
    if not expected or expected == "unknown":
        return True
    try:
        return int(expected) == actual
    except ValueError:
        return False


def expected_seats_match(expected: str, actual: str) -> bool:
    if not expected or expected == "unknown":
        return True
    expected_set = {item.strip() for item in expected.split(";") if item.strip()}
    actual_set = {item.strip() for item in actual.split(";") if item.strip()}
    return expected_set.issubset(actual_set)


def failure_row(case: dict[str, str], reason: str) -> dict[str, str]:
    return {
        **case,
        "actual_faces": "",
        "actual_seats": "",
        "result": "fail",
        "issue_note": reason,
        "tester": "侯贺升",
    }


def read_image(rel_path: str):
    image_path = APP_DIR / rel_path
    if not image_path.exists():
        return None, "image_not_found"
    image = cv2.imread(str(image_path))
    if image is None:
        return None, "image_unreadable"
    return image, ""


def make_result_row(case: dict[str, str], actual_faces: int, actual_seats: str, elapsed_ms: float) -> dict[str, str]:
    faces_ok = expected_faces_match(case["expected_faces"], actual_faces)
    seats_ok = expected_seats_match(case["expected_seats"], actual_seats)
    passed = faces_ok and seats_ok

    notes = [f"elapsed_ms={elapsed_ms:.1f}"]
    if not faces_ok:
        notes.append("face_count_mismatch")
    if not seats_ok:
        notes.append("seat_mismatch")
    if case["expected_faces"] == "unknown" or case["expected_seats"] == "unknown":
        notes.append("manual_review_case")

    return {
        **case,
        "actual_faces": str(actual_faces),
        "actual_seats": actual_seats or "none",
        "result": "pass" if passed else "review",
        "issue_note": ";".join(notes),
        "tester": "侯贺升",
    }


def run_single_case(pipeline, case: dict[str, str]) -> dict[str, str]:
    image, error = read_image(case["image_file"])
    if error:
        return failure_row(case, error)

    start = time.perf_counter()
    result = pipeline.process_image(image, image_id=0)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return make_result_row(
        case,
        int(result["num_faces"]),
        seat_summary(result["faces"]),
        elapsed_ms,
    )


def run_batch_case(pipeline, case: dict[str, str]) -> dict[str, str]:
    rel_paths = [item.strip() for item in case["image_file"].split(";") if item.strip()]
    images = []
    for rel_path in rel_paths:
        image, error = read_image(rel_path)
        if error:
            return failure_row(case, f"{error}:{rel_path}")
        images.append(image)

    start = time.perf_counter()
    results, _annotated_images = pipeline.process_batch(images)
    elapsed_ms = (time.perf_counter() - start) * 1000

    faces = [face for result in results for face in result["faces"]]
    actual_faces = sum(int(result["num_faces"]) for result in results)
    return make_result_row(case, actual_faces, seat_summary(faces), elapsed_ms)


def run_case(pipeline, case: dict[str, str]) -> dict[str, str]:
    if case["mode"] == "batch":
        return run_batch_case(pipeline, case)
    return run_single_case(pipeline, case)


def main() -> None:
    pipeline = load_pipeline()
    rows = [run_case(pipeline, case) for case in CURATED_CASES]

    with ACCEPTANCE_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    pass_count = sum(1 for row in rows if row["result"] == "pass")
    review_count = sum(1 for row in rows if row["result"] == "review")
    fail_count = sum(1 for row in rows if row["result"] == "fail")
    print(f"Wrote: {ACCEPTANCE_CSV.relative_to(APP_DIR)}")
    print(f"pass={pass_count}, review={review_count}, fail={fail_count}")


if __name__ == "__main__":
    main()
