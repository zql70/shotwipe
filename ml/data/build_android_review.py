"""Build Android review lists from the v2 score table.

Lists:
  candidates: top 500 by p_screen_photo (pHash deduped)
  low:        random 500 with p<0.20 (false-negative / hard-negative mining)
  screenshots: all auto-labelled screenshots (140)
  mid:        stratified 75 per 0.2-wide band in [0.20, 0.90)

Usage (from ml/):
    .venv/Scripts/python.exe data/build_android_review.py
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCORES = HERE / "android_scores.csv"
MANIFEST = HERE / "android_manifest.csv"
OUT = HERE


def hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    scores = list(csv.DictReader(SCORES.open(encoding="utf-8")))
    manifest = {
        row["relative_path"]: row
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))
    }
    flags = {
        row["relative_path"]: row
        for row in csv.DictReader((HERE / "android_iphone_flags.csv").open(encoding="utf-8-sig"))
    }
    excluded_apple = excluded_tc = excluded_tr = 0
    for row in scores:
        row["p_screen_photo"] = float(row["p_screen_photo"] or 0)
        row["p_screenshot"] = float(row["p_screenshot"] or 0)
        row["p_other"] = float(row["p_other"] or 0)
        row["source_folder"] = manifest.get(row["relative_path"], {}).get(
            "source_folder", ""
        )
        folder = row["source_folder"].replace("\\", "/")
        flag = flags.get(row["relative_path"], {})
        row["dup_test_cal"] = flag.get("dup_test_cal", "False") == "True"
        row["dup_train"] = flag.get("dup_train", "False") == "True"
        row["iphone_origin"] = folder.startswith("DCIM/Camera/APPLE")
        if row["iphone_origin"]:
            excluded_apple += 1
        elif row["dup_test_cal"]:
            excluded_tc += 1
        elif row["dup_train"]:
            excluded_tr += 1
    eligible = [
        row
        for row in scores
        if not row["iphone_origin"] and not row["dup_test_cal"] and not row["dup_train"]
    ]

    candidates = [
        row
        for row in eligible
        if row["auto_label"] != "screenshot"
        and not row["error"]
        and row["p_screen_photo"] >= 0.20
    ]
    candidates.sort(key=lambda row: row["p_screen_photo"], reverse=True)
    deduped = []
    for row in candidates:
        if any(hamming(row["phash"], kept["phash"]) <= 4 for kept in deduped):
            continue
        deduped.append(row)
    candidates = deduped[:500]

    low_pool = [
        row
        for row in eligible
        if row["auto_label"] == "photo_candidate"
        and not row["error"]
        and row["p_screen_photo"] < 0.20
    ]
    random.seed(23)
    low = random.sample(low_pool, min(500, len(low_pool)))

    screenshots = [row for row in eligible if row["auto_label"] == "screenshot"]

    mid = []
    for low_b, high_b in ((0.20, 0.40), (0.40, 0.60), (0.60, 0.80), (0.80, 0.90)):
        pool = [
            row
            for row in eligible
            if row["auto_label"] == "photo_candidate"
            and not row["error"]
            and low_b <= row["p_screen_photo"] < high_b
        ]
        random.shuffle(pool)
        kept = []
        for row in pool:
            if any(hamming(row["phash"], other["phash"]) <= 4 for other in kept):
                continue
            kept.append(row)
            if len(kept) >= 75:
                break
        mid.extend(kept)

    fields = [
        "id",
        "relative_path",
        "source_folder",
        "auto_label",
        "taken_at",
        "width",
        "height",
        "phash",
        "p_screenshot",
        "p_screen_photo",
        "p_other",
        "predicted",
        "error",
        "dup_test_cal",
        "dup_train",
        "iphone_origin",
        "human_label",
        "notes",
    ]

    def clean(rows: list[dict]) -> list[dict]:
        return [{**row, "human_label": "", "notes": ""} for row in rows]

    write_csv(OUT / "android_review_screen_photo_candidates.csv", clean(candidates), fields)
    write_csv(OUT / "android_review_low_score_photos.csv", clean(low), fields)
    write_csv(OUT / "android_review_screenshots.csv", clean(screenshots), fields)
    write_csv(OUT / "android_review_mid_score.csv", clean(mid), fields)

    summary = {
        "scored": len(scores),
        "excluded_iphone_origin_apple": excluded_apple,
        "excluded_test_cal_duplicates": excluded_tc,
        "excluded_train_duplicates": excluded_tr,
        "eligible_android_unique": len(eligible),
        "candidates_before_dedupe": len(
            [
                row
                for row in scores
                if row["auto_label"] != "screenshot"
                and not row["error"]
                and row["p_screen_photo"] >= 0.20
            ]
        ),
        "candidates_deduped": len(candidates),
        "candidates_at_065": sum(
            1 for row in candidates if row["p_screen_photo"] >= 0.65
        ),
        "candidates_at_035": sum(
            1 for row in candidates if row["p_screen_photo"] >= 0.35
        ),
        "low_pool": len(low_pool),
        "low_sample": len(low),
        "screenshots": len(screenshots),
        "mid_sample": len(mid),
        "by_source": dict(Counter(row["source_folder"] for row in eligible).most_common(10)),
    }
    (OUT / "android_review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
