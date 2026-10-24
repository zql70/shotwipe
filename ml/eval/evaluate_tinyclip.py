"""Evaluate TinyCLIP on the labelled sample set.

Supports the quantized TFLite shipped in the app and the original PyTorch
checkpoint. Uses the same prompt-max + softmax(cos*100) scoring as the app.

Usage (from ml/):
    .venv/Scripts/python.exe eval/evaluate_tinyclip.py \
        --tflite ../app/assets/models/tinyclip_40m32_image.tflite \
        --prompts ../app/assets/models/tinyclip_40m32_prompts.json

    .venv/Scripts/python.exe eval/evaluate_tinyclip.py --model-dir tinyclip_40m32
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "eval" / "data"
DEFAULT_TFLITE = (
    ROOT.parent / "app" / "assets" / "models" / "tinyclip_40m32_image.tflite"
)
DEFAULT_PROMPTS = (
    ROOT.parent / "app" / "assets" / "models" / "tinyclip_40m32_prompts.json"
)
INPUT_SIZE = 224
TIER_CONFIRMED = 0.55
TIER_SUSPICIOUS = 0.35


def preprocess(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    side = min(image.size)
    image = image.crop(
        (
            (image.width - side) // 2,
            (image.height - side) // 2,
            (image.width + side) // 2,
            (image.height + side) // 2,
        )
    ).resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return array[None, ...]  # NHWC


class TfliteEncoder:
    def __init__(self, path: Path) -> None:
        from ai_edge_litert.interpreter import Interpreter

        self.interpreter = Interpreter(model_path=str(path))
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]

    def encode(self, path: Path) -> np.ndarray:
        self.interpreter.set_tensor(self.input["index"], preprocess(path))
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output["index"])[0]


class TorchEncoder:
    def __init__(self, model_dir: Path) -> None:
        import torch
        from transformers import CLIPModel

        self.torch = torch
        self.model = CLIPModel.from_pretrained(str(model_dir)).eval()

    def encode(self, path: Path) -> np.ndarray:
        image = Image.open(path).convert("RGB")
        side = min(image.size)
        image = image.crop(
            (
                (image.width - side) // 2,
                (image.height - side) // 2,
                (image.width + side) // 2,
                (image.height + side) // 2,
            )
        ).resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
        x = np.asarray(image, dtype=np.float32) / 255.0
        x = (x - np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)) / np.array(
            [0.26862954, 0.26130258, 0.27577711], dtype=np.float32
        )
        tensor = self.torch.from_numpy(x.transpose(2, 0, 1))[None]
        with self.torch.no_grad():
            out = self.model.vision_model(pixel_values=tensor)
            feat = self.model.visual_projection(out.pooler_output)
        return feat[0].numpy()


def load_prompts(path: Path) -> tuple[list[np.ndarray], list[str]]:
    categories = json.loads(path.read_text(encoding="utf-8"))["categories"]
    vectors: list[np.ndarray] = []
    labels: list[str] = []
    for category, value in categories.items():
        for item in value["prompts"]:
            vector = np.asarray(item["embedding"], dtype=np.float32)
            vectors.append(vector / np.linalg.norm(vector))
            labels.append(category)
    return vectors, labels


def score(embedding: np.ndarray, vectors: list[np.ndarray], labels: list[str]) -> dict[str, float]:
    sims = np.stack(vectors) @ embedding
    logits = {}
    for category in sorted(set(labels)):
        mask = np.array(labels) == category
        logits[category] = float(sims[mask].max()) * 100.0
    maximum = max(logits.values())
    exp = {c: math.exp(v - maximum) for c, v in logits.items()}
    total = sum(exp.values())
    return {c: v / total for c, v in exp.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--tflite", default="")
    parser.add_argument("--model-dir", default="")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    parser.add_argument("--out", default=str(ROOT / "eval" / "tinyclip_results.csv"))
    parser.add_argument("--confirmed", type=float, default=TIER_CONFIRMED)
    parser.add_argument("--suspicious", type=float, default=TIER_SUSPICIOUS)
    args = parser.parse_args()

    if args.model_dir:
        encoder = TorchEncoder(Path(args.model_dir))
    else:
        encoder = TfliteEncoder(Path(args.tflite) if args.tflite else DEFAULT_TFLITE)
    vectors, labels = load_prompts(Path(args.prompts))

    rows = []
    for label in ("screenshot", "screen_photo", "photo"):
        folder = Path(args.data) / label
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            embedding = encoder.encode(path)
            embedding /= np.linalg.norm(embedding)
            probs = score(embedding, vectors, labels)
            rows.append(
                {
                    "file": str(path.relative_to(args.data)),
                    "label": label,
                    "predicted": max(probs, key=probs.get),
                    "scores": probs,
                }
            )
            print(f"\r{len(rows)} images", end="", flush=True)
    print()

    positives = sum(1 for r in rows if r["label"] == "screen_photo")
    for name, threshold in (
        ("confirmed", args.confirmed),
        ("candidate", args.suspicious),
    ):
        selected = [r for r in rows if r["scores"]["screen_photo"] >= threshold]
        tp = sum(1 for r in selected if r["label"] == "screen_photo")
        precision = tp / len(selected) if selected else 0.0
        recall = tp / positives if positives else 0.0
        print(
            f"{name} (>={threshold:.2f}): n={len(selected)} "
            f"precision={precision:.3f} recall={recall:.3f}"
        )

    out = Path(args.out)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "label", "predicted", "screenshot", "screen_photo", "other"])
        for row in rows:
            scores = row["scores"]
            writer.writerow(
                [
                    row["file"],
                    row["label"],
                    row["predicted"],
                    scores["screenshot"],
                    scores["screen_photo"],
                    scores["other"],
                ]
            )
    print(f"rows={len(rows)} csv={out}")


if __name__ == "__main__":
    main()
