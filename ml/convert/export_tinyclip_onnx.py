"""Export TinyCLIP's image tower to ONNX.

TinyCLIP is used as the commercially licensed interim model (MIT weights).
The wrapper takes RGB 0..1 at 224x224, applies CLIP normalization inside the
graph, and returns an L2-normalized 512-d embedding. Keeping normalization in
the graph means the Flutter preprocessing stays identical to MobileCLIP's.

Usage (from ml/):
    .venv/Scripts/python.exe convert/export_tinyclip_onnx.py \
        --model-dir tinyclip_40m32 \
        --out models/tinyclip_40m32_image.onnx
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from transformers import CLIPModel

ROOT = Path(__file__).resolve().parents[1]
MEAN = (0.48145466, 0.4578275, 0.40821073)
STD = (0.26862954, 0.26130258, 0.27577711)


class ImageEncoderExport(nn.Module):
    def __init__(self, model: CLIPModel) -> None:
        super().__init__()
        self.model = model
        self.register_buffer("mean", torch.tensor(MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(STD).view(1, 3, 1, 1))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        normalized = (image - self.mean) / self.std
        output = self.model.vision_model(pixel_values=normalized)
        features = self.model.visual_projection(output.pooler_output)
        return F.normalize(features, dim=-1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=str(ROOT / "tinyclip_40m32"))
    parser.add_argument(
        "--out", default=str(ROOT / "models" / "tinyclip_40m32_image.onnx")
    )
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()

    model = CLIPModel.from_pretrained(args.model_dir).eval()
    wrapper = ImageEncoderExport(model).eval()
    dummy = torch.rand(1, 3, 224, 224)
    with torch.no_grad():
        expected = wrapper(dummy).numpy()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        (dummy,),
        str(out_path),
        input_names=["image"],
        output_names=["embedding"],
        opset_version=args.opset,
        do_constant_folding=True,
        dynamo=False,
    )

    import onnxruntime as ort

    session = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
    actual = session.run(None, {"image": dummy.numpy()})[0]
    diff = np.abs(expected - actual)
    cosine = float(np.sum(expected * actual, axis=-1)[0])
    print(f"exported: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
    print(f"max_abs_diff={diff.max():.2e} cosine={cosine:.6f}")
    if diff.max() > 1e-4 or cosine < 0.9999:
        raise SystemExit("ONNX output does not match PyTorch")


if __name__ == "__main__":
    main()
