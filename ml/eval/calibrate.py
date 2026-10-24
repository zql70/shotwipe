"""Calibrate scoring strategy, temperature and confidence thresholds.

Uses the local sample set (eval/data) and the exported image encoder. Produces
a table of precision/recall at the product thresholds, plus the best
(temperature, threshold) pair that reaches the M2 precision target.

Usage (from ml/):
    .venv/Scripts/python.exe eval/calibrate.py --strategy prompt_max
    .venv/Scripts/python.exe eval/calibrate.py --strategy prompt_top3
    .venv/Scripts/python.exe eval/calibrate.py --strategy prototype
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate import DEFAULT_DATA, DEFAULT_ONNX, DEFAULT_PROMPTS, OnnxEncoder, TfliteEncoder, preprocess

ROOT = Path(__file__).resolve().parents[1]
TEMPERATURES = (10, 15, 20, 25, 30, 40, 50, 60, 75, 100)
# Product-facing thresholds from 技术方案 §3.
UI_CONFIRMED = 0.65
UI_SUSPICIOUS = 0.50
TARGET_PRECISION = 0.95


def class_scores(embedding: np.ndarray, categories: dict, strategy: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for category, value in categories.items():
        if strategy == "prototype":
            prototype = np.asarray(value["prototype"], dtype=np.float32)
            prototype /= np.linalg.norm(prototype)
            scores[category] = float(embedding @ prototype)
            continue
        sims = np.array(
            [
                float(
                    embedding
                    @ (
                        np.asarray(prompt["embedding"], dtype=np.float32)
                        / np.linalg.norm(np.asarray(prompt["embedding"], dtype=np.float32))
                    )
                )
                for prompt in value["prompts"]
            ]
        )
        if strategy == "prompt_max":
            scores[category] = float(sims.max())
        elif strategy == "prompt_top3":
            scores[category] = float(np.sort(sims)[-3:].mean())
        else:
            raise ValueError(strategy)
    return scores


def softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    logits = values * temperature
    logits -= logits.max()
    exp = np.exp(logits)
    return exp / exp.sum()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--onnx", default=str(DEFAULT_ONNX))
    parser.add_argument("--tflite", default="")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    parser.add_argument(
        "--strategy", default="prompt_max", choices=("prototype", "prompt_max", "prompt_top3")
    )
    parser.add_argument(
        "--binary",
        action="store_true",
        help="ignore the screenshot class (metadata handles screenshots)",
    )
    args = parser.parse_args()

    encoder = (
        TfliteEncoder(Path(args.tflite))
        if args.tflite
        else OnnxEncoder(Path(args.onnx))
    )
    categories = json.loads(Path(args.prompts).read_text(encoding="utf-8"))["categories"]

    labels: list[str] = []
    raw_scores: list[dict[str, float]] = []
    matrix_rows = []
    for label in ("screenshot", "screen_photo", "photo"):
        folder = Path(args.data) / label
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            embedding = encoder.encode(preprocess(path))
            embedding /= np.linalg.norm(embedding)
            labels.append(label)
            raw_scores.append(class_scores(embedding, categories, args.strategy))
            matrix_rows.append(embedding)

    is_screen = np.array([label == "screen_photo" for label in labels])
    keys = ("screenshot", "screen_photo", "other")
    if args.binary:
        keys = ("screen_photo", "other")
    raw = np.array([[score[k] for k in keys] for score in raw_scores])
    positives = int(is_screen.sum())
    mode = "binary" if args.binary else "three-way"
    print(
        f"images={len(labels)} screen_photo={positives} "
        f"strategy={args.strategy} mode={mode}"
    )

    print("\nT     t*=best@P>=0.95  recall  confirmed   | P@0.65  R@0.65 | P@0.50  R@0.50")
    best = None
    for temperature in TEMPERATURES:
        probs = np.array([softmax(row, temperature) for row in raw])
        p_screen = probs[:, keys.index("screen_photo")]
        p_at_085 = p_screen >= UI_CONFIRMED
        tp = int((p_at_085 & is_screen).sum())
        p085 = tp / int(p_at_085.sum()) if p_at_085.any() else 0.0
        r085 = tp / positives
        p_at_060 = p_screen >= UI_SUSPICIOUS
        tp060 = int((p_at_060 & is_screen).sum())
        p060 = tp060 / int(p_at_060.sum()) if p_at_060.any() else 0.0
        r060 = tp060 / positives

        thresholds = np.unique(np.round(p_screen, 4))
        candidates: list[tuple[float, float, float]] = []
        for threshold in thresholds:
            mask = p_screen >= threshold
            count = int(mask.sum())
            if count == 0:
                continue
            precision = int((mask & is_screen).sum()) / count
            recall = int((mask & is_screen).sum()) / positives
            if precision >= TARGET_PRECISION:
                candidates.append((recall, threshold, precision))
        if candidates:
            recall, threshold, precision = max(candidates)
            if best is None or recall > best[0]:
                best = (recall, threshold, precision, temperature)
            print(
                f"{temperature:3d}   {threshold:.3f}  {recall:.3f}  {int(recall * positives):3d}       | "
                f"{p085:.3f}  {r085:.3f} | {p060:.3f}  {r060:.3f}"
            )
        else:
            print(
                f"{temperature:3d}   --       --       --        | "
                f"{p085:.3f}  {r085:.3f} | {p060:.3f}  {r060:.3f}"
            )

    if best:
        recall, threshold, precision, temperature = best
        print(
            f"\nbest: strategy={args.strategy} T={temperature} threshold={threshold:.3f} "
            f"precision={precision:.3f} recall={recall:.3f}"
        )
    else:
        print("\nno (T, threshold) reached the precision target")


if __name__ == "__main__":
    main()
