"""Export the MobileCLIP-S0 image encoder to ONNX and verify it against PyTorch.

The exported model takes a 1x3x256x256 float32 tensor with values in [0, 1]
(no per-channel normalization; the official MobileCLIP preprocessing is just
resize + center crop + ToTensor) and returns an L2-normalized 512-d embedding.

Usage (from the ml/ directory):
    .venv/Scripts/python.exe convert/export_onnx.py \
        --checkpoint mobileclip_s0.pt \
        --out ../app/assets/models/mobileclip_s0_image.onnx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-mobileclip"))

import mobileclip  # noqa: E402


class ImageEncoderExport(nn.Module):
    def __init__(self, encoder: nn.Module) -> None:
        super().__init__()
        self.encoder = encoder

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        features = self.encoder(image)
        return F.normalize(features, dim=-1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=str(ROOT / "mobileclip_s0.pt"))
    parser.add_argument(
        "--out", default=str(ROOT / "models" / "mobileclip_s0_image.onnx")
    )
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()

    # The checkpoint is a plain state_dict. Reparameterization folds MobileOne
    # branches so the exported graph only contains plain convolutions.
    model, _, _ = mobileclip.create_model_and_transforms(
        "mobileclip_s0", pretrained=args.checkpoint, reparameterize=True
    )
    model.eval()
    wrapper = ImageEncoderExport(model.image_encoder).eval()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dummy = torch.rand(1, 3, 256, 256)
    with torch.no_grad():
        expected = wrapper(dummy).numpy()

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
    print(f"opset={args.opset} max_abs_diff={diff.max():.2e} cosine={cosine:.6f}")
    if diff.max() > 1e-4 or cosine < 0.9999:
        raise SystemExit("ONNX output does not match PyTorch")


if __name__ == "__main__":
    main()
