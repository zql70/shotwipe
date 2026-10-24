"""Build the v2 training manifest and 320px image cache.

Training data:
  * real labeled train split (from golden_v1 train_labeled)
  * auto-labelled screenshots (excluding all 1,499 reviewed paths)
  * weak negatives sampled from TinyCLIP p<0.02 photos (excluding reviewed paths)
  * 8,000 synthetic screen photos

Evaluation:
  * golden_calibration_v1 / golden_test_v1 (never trained on)

Usage (from ml/):
    .venv/Scripts/python.exe train/build_manifest.py \
        --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
CACHE = DATA / "cache_320" / "real"
SYNTH = DATA / "synthetic"
MANIFEST = DATA / "train_manifest_v2.csv"
LABELED = DATA / "labeled_all.csv"
IPHONE_MANIFEST = DATA / "iphone_manifest.csv"
SCORES = DATA / "iphone_scores.csv"
TRAIN_LABELED = DATA / "train_labeled_v1.csv"
GOLDEN_CAL = DATA / "golden_calibration_v1.csv"
GOLDEN_TEST = DATA / "golden_test_v1.csv"
SYNTH_MANIFEST = SYNTH / "manifest.csv"

LABEL_NAMES = {"screenshot": 0, "screen_photo": 1, "other": 2}
WEIGHTS = {
    "labeled_screen_photo": 8.0,
    "labeled_hard_negative": 3.0,
    "labeled_screenshot": 2.0,
    "auto_screenshot": 1.0,
    "weak_negative": 0.4,
    "synthetic": 1.0,
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


def grouped_val_split(rows: list[dict], fraction: float = 0.15) -> tuple[set[str], set[str]]:
    by_date: dict[str, list[str]] = {}
    for row in rows:
        by_date.setdefault(row["taken_at"][:10], []).append(row["relative_path"])
    dates = list(by_date)
    random.Random(7).shuffle(dates)
    target = int(len(rows) * fraction)
    val: set[str] = set()
    for date in dates:
        if len(val) >= target:
            break
        val.update(by_date[date])
    train = {row["relative_path"] for row in rows} - val
    return train, val


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    CACHE.mkdir(parents=True, exist_ok=True)

    labeled = {row["relative_path"] for row in csv.DictReader(LABELED.open(encoding="utf-8-sig"))}
    scores = {row["relative_path"]: row for row in csv.DictReader(SCORES.open(encoding="utf-8"))}
    iphone = list(csv.DictReader(IPHONE_MANIFEST.open(encoding="utf-8")))
    train_labeled = list(csv.DictReader(TRAIN_LABELED.open(encoding="utf-8-sig")))
    cal = list(csv.DictReader(GOLDEN_CAL.open(encoding="utf-8-sig")))
    test = list(csv.DictReader(GOLDEN_TEST.open(encoding="utf-8-sig")))
    synthetic = list(csv.DictReader(SYNTH_MANIFEST.open(encoding="utf-8")))

    val_paths = set()
    train_paths, val_paths = grouped_val_split(train_labeled, 0.15)

    records: list[dict] = []

    def add_real(row: dict, split: str, source: str) -> None:
        label_name = row["human_label"]
        if label_name not in LABEL_NAMES:
            return
        target = CACHE / (hashlib.sha1(row["relative_path"].encode("utf-8")).hexdigest() + ".jpg")
        records.append(
            {
                "source_path": row["relative_path"],
                "cache_path": str(target),
                "label": LABEL_NAMES[label_name],
                "label_name": label_name,
                "source": source,
                "split": split,
                "sample_weight": WEIGHTS.get(source, 0.0) if split == "train" else 0.0,
                "group": row.get("taken_at", "")[:10],
            }
        )

    for row in train_labeled:
        label = row["human_label"]
        source = {
            "screen_photo": "labeled_screen_photo",
            "other": "labeled_hard_negative",
            "screenshot": "labeled_screenshot",
        }.get(label)
        if not source:
            continue
        add_real(row, "val" if row["relative_path"] in val_paths else "train", source)

    # Auto-labelled screenshots, excluding every reviewed path.
    candidates = [
        row
        for row in iphone
        if row["auto_label"] == "screenshot" and row["relative_path"] not in labeled
    ]
    random.Random(11).shuffle(candidates)
    for row in candidates[:3000]:
        records.append(
            {
                "source_path": row["relative_path"],
                "cache_path": str(
                    CACHE
                    / (hashlib.sha1(row["relative_path"].encode("utf-8")).hexdigest() + ".jpg")
                ),
                "label": LABEL_NAMES["screenshot"],
                "label_name": "screenshot",
                "source": "auto_screenshot",
                "split": "train",
                "sample_weight": WEIGHTS["auto_screenshot"],
                "group": row["taken_at"][:10],
            }
        )

    # Weak negatives: TinyCLIP p<0.02, excluding all reviewed paths.
    weak_pool = [
        row
        for path, row in scores.items()
        if path not in labeled
        and row["auto_label"] in ("photo_candidate", "other_png")
        and not row["error"]
        and float(row["p_screen_photo"] or 0) < 0.02
    ]
    random.Random(13).shuffle(weak_pool)
    for row in weak_pool[:2000]:
        records.append(
            {
                "source_path": row["relative_path"],
                "cache_path": str(
                    CACHE
                    / (hashlib.sha1(row["relative_path"].encode("utf-8")).hexdigest() + ".jpg")
                ),
                "label": LABEL_NAMES["other"],
                "label_name": "other",
                "source": "weak_negative",
                "split": "train",
                "sample_weight": WEIGHTS["weak_negative"],
                "group": row["taken_at"][:10],
            }
        )

    # Synthetic screen photos (already 320x320).
    for row in synthetic:
        path = SYNTH / "images" / row["relative_path"]
        if not path.exists():
            continue
        records.append(
            {
                "source_path": str(path.relative_to(HERE)),
                "cache_path": str(path),
                "label": LABEL_NAMES["screen_photo"],
                "label_name": "screen_photo",
                "source": "synthetic",
                "split": "train",
                "sample_weight": WEIGHTS["synthetic"],
                "group": "synthetic",
            }
        )

    for row in cal:
        add_real(row, "cal", "golden_cal")
    for row in test:
        add_real(row, "test", "golden_test")

    # Cache real images; synthetic already cached.
    tasks = []
    for record in records:
        if record["source"] == "synthetic":
            continue
        target = Path(record["cache_path"])
        if target.exists():
            continue
        tasks.append((record["source_path"], str(root), str(target)))
    print(f"caching {len(tasks)} real images with 10 workers…")
    started = time.time()
    errors = []
    if tasks:
        with ProcessPoolExecutor(max_workers=10) as pool:
            for relative, result in pool.map(cache_one, tasks, chunksize=16):
                if result.startswith("ERROR"):
                    errors.append((relative, result))
    print(f"cache done in {(time.time()-started)/60:.1f} min; errors={len(errors)}")
    if errors:
        print(errors[:3])

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
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, record in enumerate(records):
            writer.writerow({**record, "teacher_idx": index})
    from collections import Counter

    print("rows", len(records))
    print("splits", Counter(r["split"] for r in records))
    print("sources", Counter(r["source"] for r in records))
    print("labels", Counter(r["label_name"] for r in records))
    print("manifest", MANIFEST)


if __name__ == "__main__":
    main()
