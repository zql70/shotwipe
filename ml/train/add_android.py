"""Append Android labeled rows to the v2 manifest for v2.1 fine-tuning.

Caches Android images at 320px, keeps the existing iPhone/synthetic rows, adds
Android train/cal/test rows, and reassigns teacher_idx.

Usage (from ml/):
    .venv/Scripts/python.exe train/add_android.py \
        --root "C:/Users/killian/Desktop/文档/xiaomi"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
BASE = DATA / "train_manifest_v2.csv"
OUT = DATA / "train_manifest_v21.csv"
CACHE = DATA / "cache_320" / "android"
LABEL_NAMES = {"screenshot": 0, "screen_photo": 1, "other": 2}
ANDROID_FILES = {
    "train": (DATA / "android_train_labeled.csv", "train"),
    "android_cal": (DATA / "android_golden_calibration.csv", "android_cal"),
    "android_test": (DATA / "android_golden_test.csv", "android_test"),
}
SOURCE_WEIGHTS = {
    "android_screen_photo": 12.0,
    "android_hard_negative": 4.0,
    "android_screenshot": 2.0,
}


def cache_one(args: tuple) -> tuple[str, str]:
    relative, root, target = args
    source = Path(root) / relative
    target = Path(target)
    if target.exists():
        return relative, str(target)
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            side = min(image.size)
            image = image.crop(
                (
                    (image.width - side) // 2,
                    (image.height - side) // 2,
                    (image.width + side) // 2,
                    (image.height + side) // 2,
                )
            ).resize((320, 320), Image.BILINEAR)
            image.save(target, "JPEG", quality=90)
        return relative, str(target)
    except Exception as exc:
        return relative, f"ERROR:{exc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    CACHE.mkdir(parents=True, exist_ok=True)

    base = list(csv.DictReader(BASE.open(encoding="utf-8")))
    android_rows = []
    tasks = []
    for split, (path, _) in ANDROID_FILES.items():
        for row in csv.DictReader(path.open(encoding="utf-8-sig")):
            relative = row["relative_path"]
            target = CACHE / (
                "android_" + hashlib.sha1(relative.encode("utf-8")).hexdigest() + ".jpg"
            )
            tasks.append((relative, str(root), str(target)))
            label_name = row["human_label"]
            if label_name not in LABEL_NAMES:
                continue
            if label_name == "screen_photo":
                source = "android_screen_photo"
            elif label_name == "screenshot":
                source = "android_screenshot"
            else:
                source = "android_hard_negative"
            android_rows.append(
                {
                    "source_path": relative,
                    "cache_path": str(target),
                    "label": LABEL_NAMES[label_name],
                    "label_name": label_name,
                    "source": source,
                    "split": split,
                    "sample_weight": SOURCE_WEIGHTS[source] if split == "train" else 0.0,
                    "group": row.get("taken_at", "")[:10],
                }
            )

    print(f"caching {len(tasks)} Android images")
    errors = []
    with ProcessPoolExecutor(max_workers=10) as pool:
        for relative, result in pool.map(cache_one, tasks, chunksize=16):
            if result.startswith("ERROR"):
                errors.append((relative, result))
    print("cache errors", len(errors), errors[:3])

    fields = [
        "source_path",
        "cache_path",
        "label",
        "label_name",
        "source",
        "split",
        "sample_weight",
        "group",
        "teacher_idx",
    ]
    rows = []
    for row in base:
        rows.append(
            {
                "source_path": row["source_path"],
                "cache_path": row["cache_path"],
                "label": row["label"],
                "label_name": row["label_name"],
                "source": row["source"],
                "split": row["split"],
                "sample_weight": row["sample_weight"],
                "group": row["group"],
                "teacher_idx": len(rows),
            }
        )
    for row in android_rows:
        rows.append({**row, "teacher_idx": len(rows)})

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter

    print("total rows", len(rows))
    print("splits", Counter(row["split"] for row in rows))
    print("android sources", Counter(row["source"] for row in android_rows))
    print("android labels", Counter(row["label_name"] for row in android_rows))
    print("manifest", OUT)


if __name__ == "__main__":
    main()
