"""Evaluate v2 and v2.1 on iPhone and Android golden test sets.

Uses the app-equivalent preprocessing (resize 224 square) and reports:
  * iPhone test at the iPhone-calibrated threshold and at 0.65
  * Android test at the Android/combined-calibrated threshold and at 0.65
  * screenshot accuracy and normal-photo false-positive rate

Usage (from ml/):
    .venv-gpu/Scripts/python.exe train/eval_cross_device.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_student import (  # noqa: E402
    IMAGENET_MEAN,
    IMAGENET_STD,
    ManifestDataset,
    Student,
    choose_threshold,
    metrics_for_threshold,
    predict,
)

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
MANIFEST = DATA / "train_manifest_v21.csv"
TEACHER = DATA / "teacher_embeddings_v21.npy"
OUT = DATA / "cross_device_metrics.json"
CHECKPOINTS = {
    "v2": DATA / "v2_student_distill.pt",
    "v21": DATA / "v2_student_v21.pt",
    "v21b": DATA / "v2_student_v21b.pt",
}
SPLITS = {
    "iphone_cal": "cal",
    "iphone_test": "test",
    "android_cal": "android_cal",
    "android_test": "android_test",
}
APP_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
)


def load_model(path: Path, device: torch.device) -> Student:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model = Student(pretrained=False).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = [
        row
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))
        if Path(row["cache_path"]).exists()
    ]
    teacher = np.load(TEACHER)
    datasets = {}
    for name, split in SPLITS.items():
        dataset = ManifestDataset(
            [row for row in rows if row["split"] == split], teacher, train=False
        )
        dataset.transform = APP_TRANSFORM
        datasets[name] = dataset

    results = {}
    for name, path in CHECKPOINTS.items():
        if not path.exists():
            print("missing checkpoint", path)
            continue
        model = load_model(path, device)
        predictions = {}
        for split_name, dataset in datasets.items():
            loader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=0)
            probs, labels, _ = predict(model, loader, device)
            predictions[split_name] = (probs, labels)
            print(f"{name} {split_name}: n={len(labels)} pos={int((labels==1).sum())}")

        iphone_threshold = choose_threshold(
            predictions["iphone_cal"][1], predictions["iphone_cal"][0], 0.95
        )
        android_threshold = choose_threshold(
            predictions["android_cal"][1], predictions["android_cal"][0], 0.95
        )
        combined_probs = np.concatenate(
            [predictions["iphone_cal"][0], predictions["android_cal"][0]]
        )
        combined_labels = np.concatenate(
            [predictions["iphone_cal"][1], predictions["android_cal"][1]]
        )
        combined_threshold = choose_threshold(combined_labels, combined_probs, 0.95)

        def metrics_for(split_name: str, threshold: float) -> dict:
            probs, labels = predictions[split_name]
            m = metrics_for_threshold(labels, probs, threshold)
            m["screenshot_accuracy"] = float(
                np.mean(
                    (probs.argmax(axis=1) == 0)[labels == 0]
                )
            ) if (labels == 0).any() else 0.0
            return m

        results[name] = {
            "thresholds": {
                "iphone_cal": iphone_threshold,
                "android_cal": android_threshold,
                "combined_cal": combined_threshold,
                "app_0.65": metrics_for_threshold(
                    predictions["iphone_test"][1],
                    predictions["iphone_test"][0],
                    0.65,
                ),
            },
            "iphone_test_at_iphone_threshold": metrics_for(
                "iphone_test", iphone_threshold["threshold"]
            ),
            "iphone_test_at_0.65": metrics_for("iphone_test", 0.65),
            "android_test_at_android_threshold": metrics_for(
                "android_test", android_threshold["threshold"]
            ),
            "android_test_at_combined_threshold": metrics_for(
                "android_test", combined_threshold["threshold"]
            ),
            "android_test_at_0.65": metrics_for("android_test", 0.65),
        }
        print(name, json.dumps(results[name], ensure_ascii=False, indent=2)[:1200])

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", OUT)


if __name__ == "__main__":
    main()
