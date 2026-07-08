#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename all image files under face-detect-app/data by purpose.

The script performs a checked two-stage rename and writes data/rename_map.csv.
It does not delete images or overwrite unrelated files.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
RENAME_MAP_CSV = DATA_DIR / "rename_map.csv"
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class RenameItem:
    old_path: Path
    new_path: Path
    category: str
    reason: str


def rel(path: Path) -> str:
    return path.relative_to(APP_DIR).as_posix()


def assert_inside_data(path: Path) -> None:
    resolved_data = DATA_DIR.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_data and resolved_data not in resolved_path.parents:
        raise RuntimeError(f"Path escapes data directory: {path}")


def normalized_suffix(path: Path) -> str:
    return ".jpg" if path.suffix.lower() in {".jpg", ".jpeg"} else ".png"


def image_paths() -> list[Path]:
    return sorted(
        p
        for p in DATA_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def category_for(path: Path) -> str:
    relative = path.relative_to(DATA_DIR)
    parts = relative.parts
    name = path.name.lower()

    if parts[0] == "samples":
        if name.startswith("sample_five_seat_") or "five_seat" in name or "5人" in name:
            return "sample_five_seat"
        if name.startswith("sample_edge_") or "edge" in name or "tmp" in name:
            return "sample_edge"
        return "sample_batch"

    if parts[0] == "uploads":
        return "upload_batch"

    if parts[0] == "results":
        return "result_annotated"

    if parts[0] == "curated" and len(parts) >= 2:
        if parts[1] == "five_seat":
            return "five_seat"
        if parts[1] == "edge":
            return "edge"
        return "batch"

    return "image"


def target_for(path: Path, index: int, category: str) -> Path:
    relative = path.relative_to(DATA_DIR)
    root = relative.parts[0]
    suffix = normalized_suffix(path)

    if root == "curated" and len(relative.parts) >= 2:
        folder = DATA_DIR / "curated" / relative.parts[1]
        return folder / f"{category}_{index:03d}{suffix}"

    return DATA_DIR / root / f"{category}_{index:03d}{suffix}"


def build_plan() -> list[RenameItem]:
    counters: dict[tuple[str, str], int] = {}
    items: list[RenameItem] = []

    for old_path in image_paths():
        relative = old_path.relative_to(DATA_DIR)
        root = relative.parts[0]
        category = category_for(old_path)
        key = (root, category)
        if root == "curated" and len(relative.parts) >= 2:
            key = (f"curated/{relative.parts[1]}", category)
        counters[key] = counters.get(key, 0) + 1

        new_path = target_for(old_path, counters[key], category)
        reason = "already_named" if old_path == new_path else "rename_by_purpose"
        items.append(RenameItem(old_path=old_path, new_path=new_path, category=category, reason=reason))

    return items


def check_plan(items: list[RenameItem]) -> None:
    old_paths = {item.old_path.resolve() for item in items}
    new_paths = [item.new_path.resolve() for item in items]
    duplicate_targets = sorted({path for path in new_paths if new_paths.count(path) > 1})

    for item in items:
        assert_inside_data(item.old_path)
        assert_inside_data(item.new_path)
        item.new_path.parent.mkdir(parents=True, exist_ok=True)

    conflicts = [
        item.new_path
        for item in items
        if item.new_path.exists()
        and item.new_path.resolve() not in old_paths
    ]

    if duplicate_targets or conflicts:
        lines = ["Rename conflict detected; no files were changed."]
        if duplicate_targets:
            lines.append("Duplicate targets:")
            lines.extend(f"  {path}" for path in duplicate_targets)
        if conflicts:
            lines.append("Existing target conflicts:")
            lines.extend(f"  {path}" for path in conflicts)
        raise RuntimeError("\n".join(lines))


def write_rename_map(items: list[RenameItem]) -> None:
    with RENAME_MAP_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["old_path", "new_path", "category", "reason"])
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "old_path": rel(item.old_path),
                    "new_path": rel(item.new_path),
                    "category": item.category,
                    "reason": item.reason,
                }
            )


def perform_rename(items: list[RenameItem]) -> int:
    changing = [item for item in items if item.old_path != item.new_path]
    tmp_pairs: list[tuple[Path, Path, RenameItem]] = []

    for index, item in enumerate(changing, start=1):
        tmp_path = item.old_path.with_name(f".__rename_tmp_{index:03d}__{item.old_path.name}")
        assert_inside_data(tmp_path)
        if tmp_path.exists():
            raise RuntimeError(f"Temporary path already exists: {tmp_path}")
        tmp_pairs.append((item.old_path, tmp_path, item))

    for old_path, tmp_path, _item in tmp_pairs:
        old_path.rename(tmp_path)

    try:
        for _old_path, tmp_path, item in tmp_pairs:
            tmp_path.rename(item.new_path)
    except Exception:
        # Best-effort rollback for any temporary files that have not yet moved.
        for old_path, tmp_path, _item in tmp_pairs:
            if tmp_path.exists() and not old_path.exists():
                tmp_path.rename(old_path)
        raise

    return len(changing)


def main() -> None:
    items = build_plan()
    check_plan(items)
    changed = perform_rename(items)
    write_rename_map(items)
    print(f"Images scanned: {len(items)}")
    print(f"Images renamed: {changed}")
    print(f"Wrote: {rel(RENAME_MAP_CSV)}")


if __name__ == "__main__":
    main()
