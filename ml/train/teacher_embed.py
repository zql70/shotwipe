"""Cache SigLIP 2 image embeddings for the v2 training manifest.

The teacher is only used offline for feature distillation; it is not shipped.
Rows are aligned with train_manifest_v2.csv by index.

Usage (from ml/, GPU env):
    .venv-gpu/Scripts/python.exe train/teacher_embed.py
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import AutoImageProcessor, SiglipModel

HERE = Path(__file__).resolve().parents[1]
MANIFEST = HERE / "data" / "train_manifest_v2.csv"
OUT = HERE / "data" / "teacher_embeddings.npy"
META = HERE / "data" / "teacher_embeddings.json"
MODEL_ID = "google/siglip2-base-patch16-224"


class CacheImages(Dataset):
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        path = self.paths[index]
        try:
            with Image.open(path) as image:
                return image.convert("RGB"), index
        except Exception:
            return None, index


def collate(batch):
    images, indices = [], []
    for image, index in batch:
        if image is not None:
            images.append(image)
            indices.append(index)
    return images, indices


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--meta", default=str(META))
    args = parser.parse_args()
    manifest = Path(args.manifest)
    out = Path(args.out)
    meta = Path(args.meta)
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    paths = [row["cache_path"] for row in rows]
    print(f"rows={len(rows)}")
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = SiglipModel.from_pretrained(MODEL_ID).eval().cuda()
    dataset = CacheImages(paths)
    loader = DataLoader(
        dataset,
        batch_size=64,
        shuffle=False,
        num_workers=8,
        pin_memory=True,
        collate_fn=collate,
        prefetch_factor=4,
    )
    output = np.zeros((len(rows), 768), dtype=np.float32)
    started = time.time()
    done = 0
    with torch.no_grad():
        for images, indices in loader:
            if not images:
                continue
            inputs = processor(images=images, return_tensors="pt").to("cuda")
            with torch.autocast("cuda", dtype=torch.float16):
                features = model.get_image_features(**inputs)
            features = features.float()
            features = features / features.norm(dim=-1, keepdim=True)
            for row, feature in zip(indices, features.cpu().numpy()):
                output[row] = feature
            done += len(images)
            if done % 1280 == 0:
                elapsed = time.time() - started
                print(
                    f"\r{done}/{len(rows)}  {done/elapsed:.1f} img/s  "
                    f"eta {(len(rows)-done)/max(done/elapsed, 1e-6)/60:.1f} min",
                    end="",
                    flush=True,
                )
    print()
    np.save(out, output)
    meta.write_text(
        json.dumps(
            {
                "model": MODEL_ID,
                "dim": 768,
                "rows": len(rows),
                "seconds": round(time.time() - started, 1),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB) in {(time.time()-started)/60:.1f} min")


if __name__ == "__main__":
    main()
