"""Merge all human labels, build pools and a stratified v0 golden split.

Now the review export covers three strata:
  * candidates: top 500 by TinyCLIP score (all ~>=0.90)
  * low: random 500 of the p<0.20 photo pool
  * screenshots: random 200 of the auto-labelled screenshot pool

The middle score band (0.20-0.90) of the candidate pool is still unsampled, so
this is `v0`, not the final golden. The summary reports that explicitly.

Usage (from ml/):
    .venv/Scripts/python.exe data/build_labeled_sets.py
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / "shotwipe_review_labels.csv"
SCORES = HERE / "iphone_scores.csv"


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


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def main() -> None:
    labels = {
        row["relative_path"]: row
        for row in csv.DictReader(LABELS.open(encoding="utf-8-sig"))
        if (row.get("human_label") or "").strip()
    }
    scores = {
        row["relative_path"]: row
        for row in csv.DictReader(SCORES.open(encoding="utf-8"))
    }

    merged = []
    for path, label_row in labels.items():
        score_row = scores.get(path)
        if score_row is None:
            continue
        score = float(score_row.get("p_screen_photo") or 0)
        merged.append(
            {
                "relative_path": path,
                "human_label": label_row["human_label"],
                "notes": label_row.get("notes", ""),
                "source_list": label_row.get("list", ""),
                "auto_label": score_row.get("auto_label", ""),
                "taken_at": score_row.get("taken_at", ""),
                "width": score_row.get("width", ""),
                "height": score_row.get("height", ""),
                "p_screenshot": score_row.get("p_screenshot", ""),
                "p_screen_photo": score_row.get("p_screen_photo", ""),
                "p_other": score_row.get("p_other", ""),
                "predicted": score_row.get("predicted", ""),
                "phash": score_row.get("phash", ""),
                "score_band": (
                    "screenshot_audit"
                    if label_row.get("list") == "screenshots"
                    else "low"
                    if score < 0.20
                    else "mid"
                    if score < 0.90
                    else "high"
                ),
            }
        )
    merged.sort(key=lambda r: float(r["p_screen_photo"] or 0), reverse=True)
    fields = list(merged[0].keys())
    write_csv(HERE / "labeled_all.csv", merged, fields)

    positives = [r for r in merged if r["human_label"] == "screen_photo"]
    others = [r for r in merged if r["human_label"] == "other"]
    screenshots = [r for r in merged if r["human_label"] == "screenshot"]
    write_csv(HERE / "screen_photo_positives.csv", positives, fields)
    write_csv(HERE / "hard_negatives.csv", others, fields)
    write_csv(HERE / "labeled_screenshots.csv", screenshots, fields)

    # Group by date + near-duplicate pHash, then split whole groups.
    n = len(merged)
    dsu = DSU(n)
    by_date: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(merged):
        by_date[row["taken_at"][:10]].append(i)
    for indices in by_date.values():
        for index in indices[1:]:
            dsu.union(indices[0], index)
    for i in range(n):
        for j in range(i + 1, n):
            if hamming(merged[i]["phash"], merged[j]["phash"]) <= 4:
                dsu.union(i, j)

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, row in enumerate(merged):
        groups[dsu.find(i)].append(row)
    group_list = list(groups.values())
    random.Random(42).shuffle(group_list)

    test: list[dict] = []
    calibration: list[dict] = []
    train: list[dict] = []
    for group in group_list:
        if len(test) < 500:
            test.extend(group)
        elif len(calibration) < 200:
            calibration.extend(group)
        else:
            train.extend(group)

    def annotate(rows: list[dict], split: str) -> list[dict]:
        return [{**row, "split": split, "group": row["taken_at"][:10]} for row in rows]

    write_csv(HERE / "golden_test_v1.csv", annotate(test, "golden_test"), fields + ["split", "group"])
    write_csv(
        HERE / "golden_calibration_v1.csv",
        annotate(calibration, "golden_calibration"),
        fields + ["split", "group"],
    )
    write_csv(HERE / "train_labeled_v1.csv", annotate(train, "train"), fields + ["split", "group"])

    def counts(rows: list[dict]) -> dict[str, int]:
        return dict(Counter(row["human_label"] for row in rows))

    # High-score candidates were a census of the top-500 band; low/screenshots
    # were random samples of their pools, so report per-stratum metrics.
    high = [r for r in merged if r["source_list"] == "candidates" and float(r["p_screen_photo"] or 0) >= 0.90]
    high_tp = sum(1 for r in high if r["human_label"] == "screen_photo")
    low = [r for r in merged if r["source_list"] == "low"]
    low_tp = sum(1 for r in low if r["human_label"] == "screen_photo")
    low_ci = wilson(low_tp, len(low))
    shots = [r for r in merged if r["source_list"] == "screenshots"]
    shot_ok = sum(1 for r in shots if r["human_label"] == "screenshot")

    mid = [r for r in merged if r["source_list"] == "mid"]
    mid_quarters = []
    mid_estimate = 0.0
    mid_var = 0.0
    for low_b, high_b, pool in (
        (0.20, 0.40, 903),
        (0.40, 0.60, 582),
        (0.60, 0.80, 494),
        (0.80, 0.90, 257),
    ):
        selected = [
            r
            for r in mid
            if low_b <= float(r["p_screen_photo"] or 0) < high_b
        ]
        tp = sum(1 for r in selected if r["human_label"] == "screen_photo")
        prevalence = tp / len(selected) if selected else 0.0
        ci = wilson(tp, len(selected))
        estimate = prevalence * pool
        mid_estimate += estimate
        mid_var += (pool * pool) * (prevalence * (1 - prevalence) / len(selected)) if selected else 0
        mid_quarters.append(
            {
                "band": f"{low_b:.2f}-{high_b:.2f}",
                "rows": len(selected),
                "screen_photo": tp,
                "prevalence": prevalence,
                "prevalence_ci95": list(ci),
                "pool_size": pool,
                "estimated_screen_photos": round(estimate),
            }
        )
    mid_ci = (
        max(0, mid_estimate - 1.96 * math.sqrt(mid_var)),
        mid_estimate + 1.96 * math.sqrt(mid_var),
    )
    low_estimate = round((low_tp / len(low)) * 9035) if low else 0
    screenshot_pos_estimate = round((1 / len(shots)) * 3777) if shots else 0
    high_pos = high_tp
    total_estimate = high_pos + mid_estimate + low_estimate + screenshot_pos_estimate
    summary = {
        "labeled_rows": len(merged),
        "empty_rows_in_export": 1500 - len(labels),
        "label_counts": dict(Counter(r["human_label"] for r in merged)),
        "by_source": {
            name: dict(Counter(r["human_label"] for r in merged if r["source_list"] == name))
            for name in ("candidates", "low", "mid", "screenshots")
        },
        "high_score_band": {
            "rows": len(high),
            "precision": high_tp / len(high) if high else 0.0,
            "note": "top-500 reviewed candidates (~p>=0.90); 61 additional high-band items were not in the review list",
        },
        "mid_score_sample": {
            "rows": len(mid),
            "screen_photo": sum(1 for r in mid if r["human_label"] == "screen_photo"),
            "prevalence": (
                sum(1 for r in mid if r["human_label"] == "screen_photo") / len(mid)
                if mid
                else 0.0
            ),
            "quarters": mid_quarters,
            "estimated_screen_photos": round(mid_estimate),
            "estimate_ci95": [round(mid_ci[0]), round(mid_ci[1])],
        },
        "low_score_sample": {
            "rows": len(low),
            "screen_photo": low_tp,
            "prevalence": low_tp / len(low) if low else 0.0,
            "prevalence_ci95": list(low_ci),
            "pool_size": 9035,
            "estimated_screen_photos_in_pool": low_estimate,
            "estimate_ci95": [
                round(low_ci[0] * 9035),
                round(low_ci[1] * 9035),
            ],
        },
        "screenshot_audit": {
            "rows": len(shots),
            "screenshot": shot_ok,
            "accuracy": shot_ok / len(shots) if shots else 0.0,
            "screen_photo_confusions": len(shots) - shot_ok,
        },
        "rough_total_screen_photos": {
            "high": high_pos,
            "mid_estimate": round(mid_estimate),
            "low_estimate": low_estimate,
            "screenshot_pool_estimate": screenshot_pos_estimate,
            "total_estimate": round(total_estimate),
            "high_band_recall_estimate": high_pos / total_estimate if total_estimate else 0.0,
            "note": "High is the reviewed top-500; mid/low/screenshot are extrapolated from samples. Treat as an order-of-magnitude estimate, not a precise census.",
        },
        "splits": {
            "golden_test": {
                "rows": len(test),
                "labels": counts(test),
                "bands": dict(Counter(r["score_band"] for r in test)),
            },
            "golden_calibration": {
                "rows": len(calibration),
                "labels": counts(calibration),
                "bands": dict(Counter(r["score_band"] for r in calibration)),
            },
            "train": {
                "rows": len(train),
                "labels": counts(train),
                "bands": dict(Counter(r["score_band"] for r in train)),
            },
        },
        "sampling_design": (
            "candidates: top 500 by score (high band, truncated); "
            "low: random 500 of 9,035 p<0.20 photos; "
            "mid: stratified 75 per 0.2-wide quarter of p 0.20-0.90; "
            "screenshots: random 200 of 3,777 auto-labelled screenshots. "
            "The golden is stratified, not a simple random sample; report per-stratum metrics."
        ),
        "missing": (
            "No major score band is unlabeled for the reviewed samples. "
            "The 61 high-band candidates outside the top-500 review list and all Android photos remain unseen; "
            "add them before treating this as a final product golden."
        ),
    }
    (HERE / "labeled_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
