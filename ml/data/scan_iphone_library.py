"""Scan a camera roll folder and build an image manifest.

First pass is metadata-only (fast): path, size, dimensions, date parsed from the
iPhone filename, extension, and a high-precision auto-label for screenshots.

Outputs (under ml/data/, local only):
    iphone_manifest.csv
    iphone_manifest_summary.json

Usage (from ml/):
    .venv/Scripts/python.exe data/scan_iphone_library.py \
        --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷" \
        --out data/iphone_manifest.csv
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

IMAGE_EXTS = {".heic", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".pic"}
VIDEO_EXTS = {".mov", ".mp4", ".m4v"}
DATE_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_")

# Full-screen iPhone/iPad screenshots. Portrait and landscape.
HIGH_SCREEN_DIMS = {
    (1170, 2532),
    (2532, 1170),
    (1284, 2778),
    (2778, 1284),
    (1125, 2436),
    (2436, 1125),
    (828, 1792),
    (1792, 828),
    (750, 1334),
    (1334, 750),
    (1242, 2688),
    (2688, 1242),
    (2732, 2048),
    (2048, 2732),
    (1620, 2160),
    (2160, 1620),
    (1668, 2388),
    (2388, 1668),
    (1668, 2224),
    (2224, 1668),
    (2048, 1536),
    (1536, 2048),
    (1290, 2796),
    (2796, 1290),
    (1179, 2556),
    (2556, 1179),
    (1206, 2622),
    (2622, 1206),
}
# Screenshot-like but not a standard full-screen capture (game screenshots,
# resized exports, desktop resolutions). Needs review.
LOW_SCREEN_DIMS = {
    (800, 480),
    (480, 800),
    (1080, 1920),
    (1920, 1080),
    (720, 1280),
    (1280, 720),
    (3840, 2160),
    (2160, 3840),
}

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
    "is_video",
    "auto_label",
    "label_confidence",
    "label_reason",
]


def parse_date(filename: str, path: str) -> datetime:
    match = DATE_RE.match(filename)
    if match:
        try:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                int(match.group(5)),
            )
        except ValueError:
            pass
    return datetime.fromtimestamp(os.path.getmtime(path))


def classify(filename: str, ext: str, width: int | None, height: int | None) -> tuple[str, str, str]:
    if ext in VIDEO_EXTS:
        return "video", "n/a", "video file (excluded from v1)"
    if ext not in IMAGE_EXTS:
        return "unsupported", "n/a", "unsupported extension"
    if width is None or height is None:
        return "unsupported", "low", "image header could not be decoded"
    dims = (width, height)
    if ext == ".png" and dims in HIGH_SCREEN_DIMS:
        return "screenshot", "high", f"PNG {width}x{height} matches iPhone/iPad screen size"
    if ext == ".png" and dims in LOW_SCREEN_DIMS:
        return "screenshot_candidate_low", "medium", f"PNG {width}x{height} screenshot-like"
    if ext == ".png":
        return "other_png", "low", f"PNG {width}x{height} not a standard screen size"
    return "photo_candidate", "medium", f"{ext.upper()[1:]} {width}x{height}; may contain screen photos"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="data/iphone_manifest.csv")
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    rows = []
    by_ext = Counter()
    by_label = Counter()
    by_year = Counter()
    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        if not entry.is_file():
            continue
        filename = entry.name
        ext = Path(filename).suffix.lower()
        by_ext[ext] += 1
        size = entry.stat().st_size
        taken = parse_date(filename, entry.path)
        width = height = None
        if ext in IMAGE_EXTS:
            try:
                with Image.open(entry.path) as image:
                    width, height = image.size
            except Exception:
                pass
        label, confidence, reason = classify(filename, ext, width, height)
        by_label[label] += 1
        by_year[taken.year] += 1
        rows.append(
            {
                "id": len(rows) + 1,
                "relative_path": filename,
                "filename": filename,
                "ext": ext,
                "size_bytes": size,
                "width": width or "",
                "height": height or "",
                "taken_at": taken.isoformat(sep=" "),
                "year": taken.year,
                "month": f"{taken.year}-{taken.month:02d}",
                "is_video": 1 if ext in VIDEO_EXTS else 0,
                "auto_label": label,
                "label_confidence": confidence,
                "label_reason": reason,
            }
        )
        if len(rows) % 2000 == 0:
            print(f"\r{len(rows)} files", end="", flush=True)

    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "root": str(root),
        "files": len(rows),
        "images": sum(1 for row in rows if not row["is_video"] and row["auto_label"] != "unsupported"),
        "videos": sum(row["is_video"] for row in rows),
        "by_extension": dict(by_ext.most_common()),
        "by_auto_label": dict(by_label.most_common()),
        "by_year": dict(sorted(by_year.items())),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {out} ({len(rows)} files) in {summary['elapsed_seconds']}s")
    print(json.dumps(summary["by_auto_label"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
