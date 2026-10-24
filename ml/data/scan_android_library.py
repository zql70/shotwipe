"""Scan the copied Xiaomi album and build an image manifest.

Includes DCIM + Pictures, skips hidden dirs and Pictures/.thumbnails, skips
videos, and auto-labels screenshots by folder/filename.

Usage (from ml/):
    .venv/Scripts/python.exe data/scan_android_library.py \
        --root "C:/Users/killian/Desktop/文档/xiaomi" \
        --out data/android_manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".3gp", ".webm", ".wmv"}
SKIP_DIRS = {".thumbnails", ".gs", ".gs_fs0", ".gs_fs6", ".android", ".globalTrash", ".tmfs"}

DATE_PATTERNS = [
    re.compile(r"(?:IMG|MVIMG|PXL|VID)_(\d{8})_(\d{6})"),
    re.compile(r"Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"Screenshot_(\d{8})_(\d{6})"),
]
MMEXPORT = re.compile(r"mmexport(\d{13})")

FIELDS = [
    "id",
    "relative_path",
    "filename",
    "ext",
    "size_bytes",
    "width",
    "height",
    "taken_at",
    "year",
    "month",
    "source_folder",
    "auto_label",
    "label_confidence",
    "label_reason",
]


def parse_date(filename: str, path: str) -> datetime:
    for pattern in DATE_PATTERNS:
        match = pattern.search(filename)
        if not match:
            continue
        try:
            groups = match.groups()
            if len(groups) == 2:
                return datetime.strptime(groups[0] + groups[1], "%Y%m%d%H%M%S")
            return datetime(*[int(v) for v in groups])
        except ValueError:
            pass
    match = MMEXPORT.search(filename)
    if match:
        try:
            return datetime.fromtimestamp(int(match.group(1)) / 1000)
        except ValueError:
            pass
    return datetime.fromtimestamp(os.path.getmtime(path))


def classify(relative: str, filename: str) -> tuple[str, str, str]:
    lower = filename.lower()
    parts = {p.lower() for p in Path(relative).parts}
    if "screenshots" in parts or lower.startswith("screenshot") or "截屏" in filename or "截图" in filename:
        return "screenshot", "high", "screenshot folder/filename"
    return "photo_candidate", "medium", "photo candidate; model will score"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="data/android_manifest.csv")
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    rows = []
    by_ext = Counter()
    by_label = Counter()
    by_folder = Counter()
    videos = 0
    skipped = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS
        ]
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            ext = path.suffix.lower()
            if ext in VIDEO_EXTS:
                videos += 1
                continue
            if ext not in IMAGE_EXTS:
                skipped += 1
                continue
            relative = str(path.relative_to(root))
            try:
                size = path.stat().st_size
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:
                skipped += 1
                continue
            taken = parse_date(filename, str(path))
            label, confidence, reason = classify(relative, filename)
            folder = str(Path(relative).parent)
            by_ext[ext] += 1
            by_label[label] += 1
            by_folder[folder] += 1
            rows.append(
                {
                    "id": len(rows) + 1,
                    "relative_path": relative,
                    "filename": filename,
                    "ext": ext,
                    "size_bytes": size,
                    "width": width,
                    "height": height,
                    "taken_at": taken.isoformat(sep=" "),
                    "year": taken.year,
                    "month": f"{taken.year}-{taken.month:02d}",
                    "source_folder": folder,
                    "auto_label": label,
                    "label_confidence": confidence,
                    "label_reason": reason,
                }
            )
            if len(rows) % 1000 == 0:
                print(f"\r{len(rows)} images", end="", flush=True)

    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "root": str(root),
        "images": len(rows),
        "videos_skipped": videos,
        "unsupported_skipped": skipped,
        "by_ext": dict(by_ext.most_common()),
        "by_label": dict(by_label.most_common()),
        "top_folders": dict(by_folder.most_common(15)),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {out} ({len(rows)} images) in {summary['elapsed_seconds']}s")
    print(json.dumps(summary["by_label"], ensure_ascii=False))


if __name__ == "__main__":
    main()
