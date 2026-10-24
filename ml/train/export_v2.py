"""Export the trained v2 student to ONNX and a calibration set for int8 TFLite.

Input is 224x224 RGB 0-1 (NHWC at TFLite), ImageNet normalization is baked into
the graph. Output is 3 logits [screenshot, screen_photo, other].

Usage (from ml/):
    .venv/Scripts/python.exe train/export_v2.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn

import timm

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
MODELS = HERE / "models"
CHECKPOINT = DATA / "v2_student_distill.pt"
ONNX_OUT = MODELS / "v2_screen_classifier.onnx"
CALIB = DATA / "calib_v2.npy"
MANIFEST = DATA / "train_manifest_v2.csv"
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


class Student(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.backbone = timm.create_model(
            "mobilenetv4_conv_small.e2400_r224_in1k", pretrained=False, num_classes=0
        )
        self.feature_dim = 1280
        self.classifier = nn.Linear(self.feature_dim, 3)
        self.projector = nn.Linear(self.feature_dim, 768)

    def forward(self, x):
        return self.classifier(self.backbone(x))


class ExportModel(nn.Module):
    def __init__(self, model: Student) -> None:
        super().__init__()
        self.model = model
        self.register_buffer("mean", torch.tensor(MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(STD).view(1, 3, 1, 1))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        normalized = (image - self.mean) / self.std
        return self.model(normalized)


def preprocess(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image = image.convert("RGB").resize((224, 224), Image.BILINEAR)
        return np.asarray(image, dtype=np.float32) / 255.0


def main() -> None:
    checkpoint = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
    state = checkpoint["model"]
    model = Student()
    # Infer the actual feature dimension from the checkpoint.
    weight = state.get("classifier.weight")
    if weight is not None:
        model.feature_dim = weight.shape[1]
        model.classifier = nn.Linear(model.feature_dim, 3)
    model.projector = nn.Linear(model.feature_dim, 768)
    model.load_state_dict(state)
    model.eval()
    export = ExportModel(model).eval()

    MODELS.mkdir(exist_ok=True)
    dummy = torch.rand(1, 3, 224, 224)
    with torch.no_grad():
        expected = export(dummy).numpy()
    torch.onnx.export(
        export,
        (dummy,),
        str(ONNX_OUT),
        input_names=["image"],
        output_names=["logits"],
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    import onnxruntime as ort

    session = ort.InferenceSession(str(ONNX_OUT), providers=["CPUExecutionProvider"])
    actual = session.run(None, {"image": dummy.numpy()})[0]
    print(
        f"ONNX: {ONNX_OUT} ({ONNX_OUT.stat().st_size/1e6:.1f} MB) "
        f"max_abs={np.abs(expected-actual).max():.2e}"
    )
    import onnx

    graph = onnx.load(str(ONNX_OUT))
    print("op types:", sorted({node.op_type for node in graph.graph.node}))

    # Balanced calibration set from training rows.
    rows = [
        row
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))
        if row["split"] == "train"
    ]
    buckets: dict[int, list[dict]] = {0: [], 1: [], 2: []}
    for row in rows:
        buckets.setdefault(int(row["label"]), []).append(row)
    rng = np.random.default_rng(42)
    selected = []
    for label in (0, 1, 2):
        pool = buckets.get(label, [])
        rng.shuffle(pool)
        selected.extend(pool[:70])
    calibration = np.stack(
        [preprocess(Path(row["cache_path"])) for row in selected], axis=0
    ).astype(np.float32)
    np.save(CALIB, calibration)
    print(f"calibration: {CALIB} {calibration.shape}")


if __name__ == "__main__":
    main()
