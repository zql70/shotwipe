"""Sample the unlabeled 0.20-0.90 TinyCLIP score band for review.

The top-500 candidates (~>=0.90) and the random p<0.20 pool are already labeled;
the middle band is the missing stratum for a complete score-stratified golden.
This samples 75 images from each quarter of the band and de-duplicates by pHash.

Usage (from ml/):
    .venv/Scripts/python.exe data/build_mid_review.py
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCORES = HERE / "iphone_scores.csv"
OUT = HERE / "review_mid_score.csv"


def hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


def main() -> None:
    rows = []
    for row in csv.DictReader(SCORES.open(encoding="utf-8")):
        if row["auto_label"] == "screenshot" or row["error"]:
            continue
        try:
            score = float(row["p_screen_photo"] or 0)
        except ValueError:
            continue
        if 0.20 <= score < 0.90:
            rows.append(row)

    bands = [(0.20, 0.40), (0.40, 0.60), (0.60, 0.80), (0.80, 0.90)]
    rng = random.Random(123)
    selected = []
    for low, high in bands:
        pool = [r for r in rows if low <= float(r["p_screen_photo"]) < high]
        rng.shuffle(pool)
        kept = []
        for row in pool:
            if any(hamming(row["phash"], other["phash"]) <= 4 for other in kept):
                continue
            kept.append(row)
            if len(kept) >= 75:
                break
        selected.extend(kept)
        print(f"band {low:.2f}-{high:.2f}: pool={len(pool)} selected={len(kept)}")

    selected.sort(key=lambda r: float(r["p_screen_photo"]), reverse=True)
    fields = [
        "id",
        "relative_path",
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
        "human_label",
        "notes",
    ]
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in selected:
            writer.writerow({**row, "human_label": "", "notes": ""})
    print(f"wrote {OUT} ({len(selected)} rows)")


if __name__ == "__main__":
    main()
