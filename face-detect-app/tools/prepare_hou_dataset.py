#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare Hou Hesheng's dataset deliverables.

The script scans existing project images, creates a curated copy set, and
generates CSV files for dataset inventory, cleaning review, and acceptance tests.
It never deletes or moves original files.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
SCAN_DIRS = [DATA_DIR / "samples", DATA_DIR / "uploads", DATA_DIR / "results"]
CURATED_DIR = DATA_DIR / "curated"
MANIFEST_CSV = DATA_DIR / "dataset_manifest.csv"
CLEANING_CSV = DATA_DIR / "cleaning_report.csv"
ACCEPTANCE_CSV = DATA_DIR / "acceptance_test_records.csv"

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
MIN_WIDTH = 320
MIN_HEIGHT = 240
NEAR_DUP_DISTANCE = 4

SEAT_ALL = "主驾;副驾;后排左;后排中;后排右"


@dataclass
class ImageInfo:
    path: Path
    rel_path: str
    file_name: str
    readable: bool
    fmt: str
    width: str
    height: str
    sha256: str
    phash: str
    duplicate_of: str
    action: str
    reason: str


def rel(path: Path) -> str:
    return path.relative_to(APP_DIR).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_hash(image: Image.Image) -> str:
    gray = image.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
    values = list(gray.tobytes())
    avg = sum(values) / len(values)
    bits = 0
    for value in values:
        bits = (bits << 1) | int(value >= avg)
    return f"{bits:016x}"


def hamming_hex(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def classify_for_manifest(info: ImageInfo) -> dict[str, str]:
    path_text = info.rel_path
    name = info.file_name.lower()

    subset = "batch"
    image_type = "uploaded_original"
    expected_faces = "unknown"
    expected_seats = "unknown"
    test_purpose = "历史上传原图/批量清洗候选"
    status = info.action
    note = info.reason

    if "/results/" in path_text:
        subset = "results"
        image_type = "annotated_result"
        test_purpose = "检测结果复核/文档截图候选"
        status = "reference" if info.readable else info.action
    elif "/samples/" in path_text:
        image_type = "ai_cabin_sample"
        status = "candidate" if info.action == "keep" else info.action
        if name.startswith("sample_five_seat_") or "five_seat" in name or "5人" in name:
            subset = "five_seat"
            expected_faces = "5"
            expected_seats = SEAT_ALL
            test_purpose = "五座位检测/多人人脸检测"
        elif name.startswith("sample_edge_") or "edge" in name or "tmp" in name:
            subset = "edge"
            test_purpose = "边界样例/需人工复核"
            status = "review"
        else:
            subset = "batch"
            test_purpose = "批量清洗候选/基础检测样例"

    return {
        "file_path": path_text,
        "file_name": info.file_name,
        "subset": subset,
        "image_type": image_type,
        "expected_faces": expected_faces,
        "expected_seats": expected_seats,
        "test_purpose": test_purpose,
        "status": status,
        "note": note,
    }


def scan_images() -> list[ImageInfo]:
    image_paths = []
    for folder in SCAN_DIRS:
        if folder.exists():
            image_paths.extend(
                p for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            )

    seen_sha: dict[str, str] = {}
    seen_phash: dict[str, str] = {}
    infos: list[ImageInfo] = []

    for path in sorted(image_paths):
        readable = False
        fmt = ""
        width = ""
        height = ""
        file_hash = ""
        phash = ""
        duplicate_of = ""
        action = "keep"
        reasons: list[str] = []

        if path.suffix.lower() not in IMAGE_EXTS:
            action = "exclude"
            reasons.append("unsupported_format")

        try:
            file_hash = sha256_file(path)
            with Image.open(path) as image:
                image.load()
                readable = True
                fmt = image.format or path.suffix.lower().lstrip(".").upper()
                width, height = str(image.width), str(image.height)
                phash = average_hash(image)
        except Exception as exc:  # noqa: BLE001 - report scan failures, do not stop batch.
            action = "exclude"
            reasons.append(f"unreadable:{exc.__class__.__name__}")

        if readable:
            if int(width) < MIN_WIDTH or int(height) < MIN_HEIGHT:
                action = "review"
                reasons.append("too_small")

            if file_hash in seen_sha:
                duplicate_of = seen_sha[file_hash]
                action = "exclude"
                reasons.append("exact_duplicate")
            else:
                seen_sha[file_hash] = rel(path)

            if not duplicate_of and phash:
                for old_hash, old_path in seen_phash.items():
                    if hamming_hex(phash, old_hash) <= NEAR_DUP_DISTANCE:
                        duplicate_of = old_path
                        if action == "keep":
                            action = "review"
                        reasons.append("possible_visual_duplicate")
                        break
                seen_phash.setdefault(phash, rel(path))

        infos.append(
            ImageInfo(
                path=path,
                rel_path=rel(path),
                file_name=path.name,
                readable=readable,
                fmt=fmt,
                width=width,
                height=height,
                sha256=file_hash,
                phash=phash,
                duplicate_of=duplicate_of,
                action=action,
                reason=";".join(reasons) if reasons else "ok",
            )
        )

    return infos


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def suffix_for_copy(source: Path) -> str:
    return ".jpg" if source.suffix.lower() in {".jpg", ".jpeg"} else ".png"


def copy_curated(manifest_rows: list[dict[str, str]], info_by_rel: dict[str, ImageInfo]) -> list[dict[str, str]]:
    counters = {"single": 0, "multi": 0, "five_seat": 0, "batch": 0, "edge": 0}
    curated_rows: list[dict[str, str]] = []

    for row in manifest_rows:
        info = info_by_rel[row["file_path"]]
        if not info.readable:
            continue
        if row["subset"] == "results":
            continue
        if row["status"] == "exclude":
            continue

        subset = row["subset"]
        prefix = subset if subset in counters else "batch"
        counters[prefix] += 1

        target_dir = CURATED_DIR / prefix
        target_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{prefix}_{counters[prefix]:03d}{suffix_for_copy(info.path)}"
        target_path = target_dir / target_name
        shutil.copy2(info.path, target_path)

        curated_row = dict(row)
        curated_row["file_path"] = rel(target_path)
        curated_row["file_name"] = target_name
        curated_row["note"] = f"curated copy from {row['file_path']}; {row['note']}"
        curated_rows.append(curated_row)

    return curated_rows


def make_acceptance_rows(curated_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, row in enumerate(curated_rows, start=1):
        mode = "batch" if row["subset"] == "batch" else "single"
        rows.append(
            {
                "case_id": f"TC-HH-{index:03d}",
                "image_file": row["file_path"],
                "mode": mode,
                "expected_faces": row["expected_faces"],
                "actual_faces": "",
                "expected_seats": row["expected_seats"],
                "actual_seats": "",
                "result": "pending",
                "issue_note": "待后端接口稳定后填写实际检测结果",
                "tester": "侯贺升",
            }
        )
    return rows


def main() -> None:
    infos = scan_images()
    info_by_rel = {info.rel_path: info for info in infos}

    manifest_rows = [classify_for_manifest(info) for info in infos]
    curated_rows = copy_curated(manifest_rows, info_by_rel)
    all_manifest_rows = manifest_rows + curated_rows

    write_csv(
        MANIFEST_CSV,
        [
            "file_path",
            "file_name",
            "subset",
            "image_type",
            "expected_faces",
            "expected_seats",
            "test_purpose",
            "status",
            "note",
        ],
        all_manifest_rows,
    )

    write_csv(
        CLEANING_CSV,
        [
            "file_path",
            "readable",
            "format",
            "width",
            "height",
            "sha256",
            "phash",
            "duplicate_of",
            "action",
            "reason",
        ],
        [
            {
                "file_path": info.rel_path,
                "readable": str(info.readable).lower(),
                "format": info.fmt,
                "width": info.width,
                "height": info.height,
                "sha256": info.sha256,
                "phash": info.phash,
                "duplicate_of": info.duplicate_of,
                "action": info.action,
                "reason": info.reason,
            }
            for info in infos
        ],
    )

    write_csv(
        ACCEPTANCE_CSV,
        [
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
        ],
        make_acceptance_rows(curated_rows),
    )

    print(f"Scanned images: {len(infos)}")
    print(f"Curated images: {len(curated_rows)}")
    print(f"Wrote: {rel(MANIFEST_CSV)}")
    print(f"Wrote: {rel(CLEANING_CSV)}")
    print(f"Wrote: {rel(ACCEPTANCE_CSV)}")


if __name__ == "__main__":
    main()
