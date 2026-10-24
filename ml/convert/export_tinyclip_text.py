"""Precompute TinyCLIP text embeddings in the app's prompts JSON format.

Usage (from ml/):
    .venv/Scripts/python.exe convert/export_tinyclip_text.py \
        --model-dir tinyclip_40m32 \
        --prompts convert/prompts.json \
        --out ../app/assets/models/tinyclip_40m32_prompts.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=str(ROOT / "tinyclip_40m32"))
    parser.add_argument("--prompts", default=str(ROOT / "convert" / "prompts.json"))
    parser.add_argument(
        "--out",
        default=str(
            ROOT.parent / "app" / "assets" / "models" / "tinyclip_40m32_prompts.json"
        ),
    )
    args = parser.parse_args()

    config = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    model = CLIPModel.from_pretrained(args.model_dir).eval()
    processor = CLIPProcessor.from_pretrained(args.model_dir)
    tokenizer = processor.tokenizer

    output = {
        "model": "tinyclip_40m32",
        "resolution": 224,
        "embedding_dim": None,
        "logit_scale": 100.0,
        "categories": {},
    }
    for category, prompts in config["prompts"].items():
        tokens = tokenizer(
            prompts,
            padding=True,
            truncation=True,
            max_length=77,
            return_tensors="pt",
        )
        with torch.no_grad():
            text_output = model.text_model(**tokens)
            embeddings = model.text_projection(text_output.pooler_output)
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        embeddings = embeddings.numpy()
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
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
