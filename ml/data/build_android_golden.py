"""Build the Android labeled pools, golden test/calibration and training split.

Deduplicates the candidate/mid overlap, enforces the iPhone-duplicate exclusions,
and groups by date + pHash to avoid near-duplicate leakage.

Usage (from ml/):
    .venv/Scripts/python.exe data/build_android_golden.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / "android_review_labels.csv"
SCORES = HERE / "android_scores.csv"
MANIFEST = HERE / "android_manifest.csv"
FLAGS = HERE / "android_iphone_flags.csv"


def hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


class DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    labels = list(csv.DictReader(LABELS.open(encoding="utf-8-sig")))
    scores = {
        row["relative_path"]: row
        for row in csv.DictReader(SCORES.open(encoding="utf-8"))
    }
    manifest = {
        row["relative_path"]: row
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))
    }
    flags = {
        row["relative_path"]: row
        for row in csv.DictReader(FLAGS.open(encoding="utf-8-sig"))
    }

    unique: dict[str, dict] = {}
    duplicates = 0
    conflicts = 0
    for row in labels:
        label = (row.get("human_label") or "").strip()
        if not label:
            continue
        path = row["relative_path"]
        score = scores.get(path, {})
        meta = manifest.get(path, {})
        flag = flags.get(path, {})
        folder = meta.get("source_folder", "").replace("\\", "/")
        if folder.startswith("DCIM/Camera/APPLE"):
            continue
        if flag.get("dup_test_cal") == "True" or flag.get("dup_train") == "True":
            continue
        record = {
            "relative_path": path,
            "human_label": label,
            "notes": row.get("notes", ""),
            "source_list": row.get("list", ""),
            "auto_label": meta.get("auto_label", ""),
            "source_folder": meta.get("source_folder", ""),
            "taken_at": meta.get("taken_at", ""),
            "width": meta.get("width", ""),
            "height": meta.get("height", ""),
            "phash": score.get("phash", ""),
            "p_screenshot": score.get("p_screenshot", ""),
            "p_screen_photo": score.get("p_screen_photo", ""),
            "p_other": score.get("p_other", ""),
            "predicted": score.get("predicted", ""),
        }
        if path in unique:
            duplicates += 1
            if unique[path]["human_label"] != label:
                conflicts += 1
            continue
        unique[path] = record

    rows = list(unique.values())
    rows.sort(key=lambda r: float(r["p_screen_photo"] or 0), reverse=True)
    fields = list(rows[0].keys())
    write_csv(HERE / "android_labeled.csv", rows, fields)

    positives = [r for r in rows if r["human_label"] == "screen_photo"]
    others = [r for r in rows if r["human_label"] == "other"]
    screenshots = [r for r in rows if r["human_label"] == "screenshot"]
    write_csv(HERE / "android_screen_photo_positives.csv", positives, fields)
    write_csv(HERE / "android_hard_negatives.csv", others, fields)
    write_csv(HERE / "android_screenshots.csv", screenshots, fields)

    # Group by date + pHash, then split whole groups.
    n = len(rows)
    dsu = DSU(n)
    by_date: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        by_date[row["taken_at"][:10]].append(i)
    for indices in by_date.values():
        for index in indices[1:]:
            dsu.union(indices[0], index)
    for i in range(n):
        for j in range(i + 1, n):
            if hamming(rows[i]["phash"], rows[j]["phash"]) <= 4:
                dsu.union(i, j)
    groups: dict[int, list[dict]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[dsu.find(i)].append(row)
    group_list = list(groups.values())
    random.Random(31).shuffle(group_list)

    test: list[dict] = []
    calibration: list[dict] = []
    train: list[dict] = []
    for group in group_list:
        if len(test) < 320:
            test.extend(group)
        elif len(calibration) < 120:
            calibration.extend(group)
        else:
            train.extend(group)

    def annotate(items: list[dict], split: str) -> list[dict]:
        return [{**row, "split": split} for row in items]

    write_csv(HERE / "android_golden_test.csv", annotate(test, "test"), fields + ["split"])
    write_csv(
        HERE / "android_golden_calibration.csv",
        annotate(calibration, "calibration"),
        fields + ["split"],
    )
    write_csv(HERE / "android_train_labeled.csv", annotate(train, "train"), fields + ["split"])

    def counts(items: list[dict]) -> dict[str, int]:
        return dict(Counter(row["human_label"] for row in items))

    # v2 precision by score band on the unique labels.
    band_metrics = {}
    for name, low, high in (
        ("p>=0.90", 0.90, 2.0),
        ("0.80-0.90", 0.80, 0.90),
        ("0.65-0.80", 0.65, 0.80),
        ("0.35-0.65", 0.35, 0.65),
        ("0.20-0.35", 0.20, 0.35),
        ("p<0.20", 0.0, 0.20),
    ):
        selected = [
            row
            for row in rows
            if low <= float(row["p_screen_photo"] or 0) < high
            and row["auto_label"] != "screenshot"
        ]
        tp = sum(1 for row in selected if row["human_label"] == "screen_photo")
        band_metrics[name] = {
            "rows": len(selected),
            "screen_photo": tp,
            "precision": tp / len(selected) if selected else 0.0,
        }

    summary = {
        "unique_labeled": len(rows),
        "duplicates_removed": duplicates,
        "conflicts": conflicts,
        "label_counts": counts(rows),
        "positives": len(positives),
        "hard_negatives": len(others),
        "screenshots": len(screenshots),
        "by_source": {
            name: dict(Counter(row["human_label"] for row in rows if row["source_list"] == name))
            for name in ("candidates", "mid", "low", "screenshots")
        },
        "v2_precision_by_band": band_metrics,
        "splits": {
            "test": {"rows": len(test), "labels": counts(test)},
            "calibration": {"rows": len(calibration), "labels": counts(calibration)},
            "train": {"rows": len(train), "labels": counts(train)},
        },
        "warning": (
            "Android test is a stratified sample of the Android-unique album, "
            "with limited screen-photo positives; report it separately from the iPhone golden."
        ),
    }
    (HERE / "android_labeled_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    files = [
        "android_labeled.csv",
        "android_screen_photo_positives.csv",
        "android_hard_negatives.csv",
        "android_screenshots.csv",
        "android_golden_test.csv",
        "android_golden_calibration.csv",
        "android_train_labeled.csv",
    ]
    manifest_out = {
        "version": "android_golden_v1_2026-10-20",
        "files": {
            name: {
                "sha256": hashlib.sha256((HERE / name).read_bytes()).hexdigest(),
                "bytes": (HERE / name).stat().st_size,
            }
            for name in files
        },
        "summary": summary,
    }
    (HERE / "android_golden_manifest.json").write_text(
        json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
