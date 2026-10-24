"""Offline evaluation for the MobileCLIP screen-photo classifier.

Runs the exported ONNX (or TFLite) image encoder on a labelled folder tree:

    eval/data/screenshot/*.jpg
    eval/data/screen_photo/*.jpg
    eval/data/photo/*.jpg

and reports the confidence-tier precision/recall used by the app:
  * confirmed:  predicted class == screen_photo and p >= 0.85
  * suspicious: predicted class == screen_photo and 0.60 <= p < 0.85
  * recall:     true screen photos in confirmed / all true screen photos

This is also the regression harness for every future model/prompt change.

Usage (from ml/):
    .venv/Scripts/python.exe eval/evaluate.py
    .venv/Scripts/python.exe eval/evaluate.py --tflite ../app/assets/models/mobileclip_s0_image.tflite
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "eval" / "data"
DEFAULT_ONNX = ROOT / "models" / "mobileclip_s0_image.onnx"
DEFAULT_PROMPTS = ROOT / "models" / "mobileclip_prompts.json"
INPUT_SIZE = 256
LABELS = ("screenshot", "screen_photo", "photo")
TIER_CONFIRMED = 0.65
TIER_SUSPICIOUS = 0.50


def preprocess(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize(
        (INPUT_SIZE, INPUT_SIZE), Image.BILINEAR
    )
    array = np.asarray(image, dtype=np.float32) / 255.0
    return array.transpose(2, 0, 1)[None, ...]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


class OnnxEncoder:
    def __init__(self, path: Path) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(path), providers=["CPUExecutionProvider"]
        )
        self.name = self.session.get_inputs()[0].name

    def encode(self, tensor: np.ndarray) -> np.ndarray:
        return self.session.run(None, {self.name: tensor})[0][0]


class TfliteEncoder:
    def __init__(self, path: Path) -> None:
        from ai_edge_litert.interpreter import Interpreter

        self.interpreter = Interpreter(model_path=str(path), num_threads=4)
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]

    def encode(self, tensor: np.ndarray) -> np.ndarray:
        x = tensor.transpose(0, 2, 3, 1).astype(np.float32)
        self.interpreter.set_tensor(self.input["index"], x)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output["index"])[0]


def load_prompts(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["categories"]


def score_prototypes(embedding: np.ndarray, categories: dict) -> dict[str, float]:
    logits = {}
    for category, value in categories.items():
        prototype = np.asarray(value["prototype"], dtype=np.float32)
        prototype /= np.linalg.norm(prototype)
        logits[category] = float(embedding @ prototype) * 100.0
    probs = softmax(np.array(list(logits.values())))
    return dict(zip(logits.keys(), probs.tolist()))


def score_prompt_max(embedding: np.ndarray, categories: dict) -> dict[str, float]:
    logits = {}
    for category, value in categories.items():
        sims = []
        for prompt in value["prompts"]:
            vector = np.asarray(prompt["embedding"], dtype=np.float32)
            vector /= np.linalg.norm(vector)
            sims.append(float(embedding @ vector))
        logits[category] = max(sims) * 100.0
    probs = softmax(np.array(list(logits.values())))
    return dict(zip(logits.keys(), probs.tolist()))


def metrics(rows: list[dict], strategy: str) -> dict:
    result = {}
    for target in ("screen_photo", "screenshot"):
        positives = [r for r in rows if r["label"] == target]
        confirmed = [
            r
            for r in rows
            if r["predicted"] == target and r["scores"][target] >= TIER_CONFIRMED
        ]
        suspicious = [
            r
            for r in rows
            if r["predicted"] == target
            and TIER_SUSPICIOUS <= r["scores"][target] < TIER_CONFIRMED
        ]
        tp = sum(1 for r in confirmed if r["label"] == target)
        result[target] = {
            "confirmed": len(confirmed),
            "confirmed_precision": tp / len(confirmed) if confirmed else 0.0,
            "confirmed_recall": tp / len(positives) if positives else 0.0,
            "suspicious": len(suspicious),
            "suspicious_precision": (
                sum(1 for r in suspicious if r["label"] == target) / len(suspicious)
                if suspicious
                else 0.0
            ),
            "recall_with_suspicious": (
                (tp + sum(1 for r in suspicious if r["label"] == target))
                / len(positives)
                if positives
                else 0.0
            ),
            "positives": len(positives),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--onnx", default=str(DEFAULT_ONNX))
    parser.add_argument("--tflite", default="")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    parser.add_argument("--out", default=str(ROOT / "eval" / "results.csv"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    encoder = TfliteEncoder(Path(args.tflite)) if args.tflite else OnnxEncoder(
        Path(args.onnx)
    )
    categories = load_prompts(Path(args.prompts))
    data_dir = Path(args.data)

    rows = []
    for label in LABELS:
        folder = data_dir / label
        if not folder.exists():
            continue
        files = sorted(
            p
            for p in folder.iterdir()
            if p.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        if args.limit:
            files = files[: args.limit]
        for path in files:
            embedding = encoder.encode(preprocess(path))
            embedding = embedding / np.linalg.norm(embedding)
            prototype_scores = score_prototypes(embedding, categories)
            prompt_scores = score_prompt_max(embedding, categories)
            rows.append(
                {
                    "file": str(path.relative_to(data_dir)),
                    "label": label,
                    "prototype": prototype_scores,
                    "prompt_max": prompt_scores,
                }
            )
            print(f"\r{len(rows)} images", end="", flush=True)
    print()

    out_lines = ["file,label,strategy,predicted,confidence,screenshot,screen_photo,other"]
    reports = {}
    for strategy in ("prototype", "prompt_max"):
        for row in rows:
            scores = row[strategy]
            predicted = max(scores, key=scores.get)
            row[f"{strategy}_predicted"] = predicted
            out_lines.append(
                f"{row['file']},{row['label']},{strategy},{predicted},"
                f"{scores[predicted]:.4f},{scores['screenshot']:.4f},"
                f"{scores['screen_photo']:.4f},{scores['other']:.4f}"
            )
        strategy_rows = [
            {
                "label": row["label"],
                "predicted": row[f"{strategy}_predicted"],
                "scores": row[strategy],
            }
            for row in rows
        ]
        reports[strategy] = metrics(strategy_rows, strategy)

    Path(args.out).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    report_path = Path(args.out).with_suffix(".json")
    report_path.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for strategy, report in reports.items():
        print(f"\n== scoring: {strategy} ==")
        for target, m in report.items():
            print(
                f"{target:13s} positives={m['positives']:3d} "
                f"confirmed={m['confirmed']:3d} precision={m['confirmed_precision']:.3f} "
                f"recall={m['confirmed_recall']:.3f} "
                f"suspicious={m['suspicious']:3d} "
                f"recall+susp={m['recall_with_suspicious']:.3f}"
            )
    print(f"\nrows: {len(rows)}  csv: {args.out}  json: {report_path}")


if __name__ == "__main__":
    main()
