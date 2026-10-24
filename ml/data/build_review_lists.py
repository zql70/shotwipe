"""Build human-review lists from the TinyCLIP score table.

Outputs (under ml/data/):
    review_screen_photo_candidates.csv  # high-recall candidates, sorted by score
    review_low_score_photos.csv         # random low-score sample for false negatives
    review_screenshots.csv              # random screenshot sample for label audit
    review_summary.json

The CSVs have empty `human_label` / `notes` columns ready for annotation.
Labels should be one of: screenshot, screen_photo, other, ignore.

Usage (from ml/):
    .venv/Scripts/python.exe data/build_review_lists.py \
        --scores data/iphone_scores.csv \
        --out-dir data
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path


def hamming(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", default="data/iphone_scores.csv")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--candidate-threshold", type=float, default=0.20)
    parser.add_argument("--top-candidates", type=int, default=500)
    parser.add_argument("--low-sample", type=int, default=500)
    parser.add_argument("--screenshot-sample", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    rows = list(csv.DictReader(Path(args.scores).open(encoding="utf-8")))
    for row in rows:
        row["p_screen_photo"] = float(row["p_screen_photo"] or 0.0)
        row["p_screenshot"] = float(row["p_screenshot"] or 0.0)
        row["p_other"] = float(row["p_other"] or 0.0)

    candidates = [
        row
        for row in rows
        if row["auto_label"] != "screenshot"
        and row["p_screen_photo"] >= args.candidate_threshold
        and not row["error"]
    ]
    candidates.sort(key=lambda row: row["p_screen_photo"], reverse=True)

    # Greedy pHash dedupe: keep the highest-scoring frame of a near-duplicate group.
    deduped: list[dict] = []
    for row in candidates:
        if any(hamming(row["phash"], kept["phash"]) <= 4 for kept in deduped):
            continue
        deduped.append(row)
    candidates = deduped

    low_pool = [
        row
        for row in rows
        if row["auto_label"] in ("photo_candidate", "other_png")
        and row["p_screen_photo"] < args.candidate_threshold
        and not row["error"]
    ]
    low_sample = random.sample(low_pool, min(args.low_sample, len(low_pool)))

    screenshot_pool = [row for row in rows if row["auto_label"] == "screenshot"]
    screenshot_sample = random.sample(
        screenshot_pool, min(args.screenshot_sample, len(screenshot_pool))
    )

    fields = [
        "id",
        "relative_path",
        "auto_label",
        "taken_at",
        "width",
        "height",
        "phash",
        "p_screen_photo",
        "p_screenshot",
        "p_other",
        "predicted",
        "error",
        "human_label",
        "notes",
    ]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        out_dir / "review_screen_photo_candidates.csv",
        [{**row, "human_label": "", "notes": ""} for row in candidates[: args.top_candidates]],
        fields,
    )
    write_csv(
        out_dir / "review_low_score_photos.csv",
        [{**row, "human_label": "", "notes": ""} for row in low_sample],
        fields,
    )
    write_csv(
        out_dir / "review_screenshots.csv",
        [{**row, "human_label": "", "notes": ""} for row in screenshot_sample],
        fields,
    )

    summary = {
        "images_scored": len(rows),
        "candidate_threshold": args.candidate_threshold,
        "candidate_rows_before_dedupe": len(
            [
                row
                for row in rows
                if row["auto_label"] != "screenshot"
                and row["p_screen_photo"] >= args.candidate_threshold
            ]
        ),
        "candidate_rows_after_dedupe": len(candidates),
        "candidates_at_035": sum(1 for row in candidates if row["p_screen_photo"] >= 0.35),
        "candidates_at_055": sum(1 for row in candidates if row["p_screen_photo"] >= 0.55),
        "low_score_pool": len(low_pool),
        "screenshot_pool": len(screenshot_pool),
        "by_auto_label": dict(Counter(row["auto_label"] for row in rows)),
    }
    (out_dir / "review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote review lists to {out_dir}")


if __name__ == "__main__":
    main()
