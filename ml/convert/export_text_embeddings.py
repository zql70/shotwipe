"""Precompute MobileCLIP-S0 text embeddings for the classification prompts.

The text encoder never ships to the device: only the resulting 512-d vectors
are bundled as JSON, which keeps the app model small and makes the class
definition editable from Python.

Usage (from the ml/ directory):
    .venv/Scripts/python.exe convert/export_text_embeddings.py \
        --checkpoint mobileclip_s0.pt \
        --out ../app/assets/models/mobileclip_prompts.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-mobileclip"))

import mobileclip  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=str(ROOT / "mobileclip_s0.pt"))
    parser.add_argument("--prompts", default=str(ROOT / "convert" / "prompts.json"))
    parser.add_argument(
        "--out",
        default=str(ROOT / "models" / "mobileclip_prompts.json"),
    )
    args = parser.parse_args()

    config = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    model, _, _ = mobileclip.create_model_and_transforms(
        config["model"], pretrained=args.checkpoint, reparameterize=True
    )
    model.eval()
    tokenizer = mobileclip.get_tokenizer(config["model"])

    output = {
        "model": config["model"],
        "resolution": config["resolution"],
        "embedding_dim": None,
        "logit_scale": 100.0,
        "categories": {},
    }

    for category, prompts in config["prompts"].items():
        tokens = tokenizer(prompts)
        with torch.no_grad():
            embeddings = model.encode_text(tokens, normalize=True).numpy()
        # Class prototype = normalized mean of its prompt embeddings; the
        # individual prompts are kept so the eval script can compare scoring
        # strategies without recomputing the text tower.
        mean = embeddings.mean(axis=0)
        mean /= np.linalg.norm(mean)
        output["categories"][category] = {
            "prototype": [round(float(v), 6) for v in mean],
            "prompts": [
                {"text": text, "embedding": [round(float(v), 6) for v in emb]}
                for text, emb in zip(prompts, embeddings)
            ],
        }
        output["embedding_dim"] = int(embeddings.shape[1])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
