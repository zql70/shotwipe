"""Train the v2 MobileNetV4-Conv-S screen-photo classifier.

Stage 1: synthetic + real + auto-labelled screenshots + weak negatives.
Stage 2: real data fine-tune (hard negatives, labelled screenshots, a little synthetic).

Distillation: CE + cosine feature matching to SigLIP 2 image embeddings.
Evaluation: golden_calibration_v1 for threshold selection, golden_test_v1 once.

Usage (from ml/, GPU env):
    .venv-gpu/Scripts/python.exe train/train_student.py --epochs 6 --finetune-epochs 2
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

import timm

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
MANIFEST = DATA / "train_manifest_v2.csv"
TEACHER = DATA / "teacher_embeddings.npy"
CAL = DATA / "golden_calibration_v1.csv"
TEST = DATA / "golden_test_v1.csv"
CHECKPOINT = DATA / "v2_student.pt"
METRICS = DATA / "v2_metrics.json"
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
CLASS_NAMES = {0: "screenshot", 1: "screen_photo", 2: "other"}


class ManifestDataset(Dataset):
    def __init__(self, rows: list[dict], teacher: np.ndarray, train: bool) -> None:
        self.rows = rows
        self.teacher = teacher
        if train:
            self.transform = transforms.Compose(
                [
                    transforms.RandomResizedCrop(224, scale=(0.70, 1.0), ratio=(0.85, 1.15)),
                    transforms.ColorJitter(0.20, 0.20, 0.20, 0.02),
                    transforms.RandomRotation(3, fill=128),
                    transforms.ToTensor(),
                    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
                ]
            )
        else:
            self.transform = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
                ]
            )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with Image.open(row["cache_path"]) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        teacher = self.teacher[int(row["teacher_idx"])].astype(np.float32)
        teacher = torch.from_numpy(teacher)
        return tensor, int(row["label"]), teacher, index


class Student(nn.Module):
    def __init__(self, teacher_dim: int = 768, pretrained: bool = True) -> None:
        super().__init__()
        self.backbone = timm.create_model(
            "mobilenetv4_conv_small.e2400_r224_in1k",
            pretrained=pretrained,
            num_classes=0,
        )
        self.backbone.eval()
        with torch.no_grad():
            self.feature_dim = int(
                self.backbone(torch.zeros(2, 3, 224, 224)).shape[1]
            )
        self.backbone.train()
        feature_dim = self.feature_dim
        self.classifier = nn.Linear(feature_dim, 3)
        self.projector = nn.Linear(feature_dim, teacher_dim)

    def forward(self, x: torch.Tensor):
        features = self.backbone(x)
        logits = self.classifier(features)
        projected = F.normalize(self.projector(features), dim=-1)
        return logits, projected


def softmax_probs(logits: torch.Tensor) -> torch.Tensor:
    return torch.softmax(logits, dim=-1)


def metrics_for_threshold(labels: np.ndarray, probs: np.ndarray, threshold: float) -> dict:
    pred_screen = probs[:, 1] >= threshold
    labels_screen = labels == 1
    tp = int(np.sum(pred_screen & labels_screen))
    fp = int(np.sum(pred_screen & ~labels_screen))
    fn = int(np.sum(~pred_screen & labels_screen))
    tn = int(np.sum(~pred_screen & ~labels_screen))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    other_fp = int(np.sum(pred_screen & (labels == 2)))
    normal_total = int(np.sum(labels == 2))
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "other_false_positive_rate": other_fp / normal_total if normal_total else 0.0,
    }


def choose_threshold(labels: np.ndarray, probs: np.ndarray, target_precision: float = 0.95):
    candidates = np.unique(np.round(probs[:, 1], 4))
    best = None
    for threshold in candidates:
        m = metrics_for_threshold(labels, probs, float(threshold))
        if m["precision"] >= target_precision and (best is None or m["recall"] > best["recall"]):
            best = m
    if best is None:
        # fall back to max F1
        for threshold in candidates:
            m = metrics_for_threshold(labels, probs, float(threshold))
            if best is None or (2 * m["precision"] * m["recall"] / max(m["precision"] + m["recall"], 1e-9)) > (
                2 * best["precision"] * best["recall"] / max(best["precision"] + best["recall"], 1e-9)
            ):
                best = m
    return best


def run_epoch(model, loader, optimizer, scaler, device, train: bool, feature_weight: float):
    model.train(train)
    total_loss = 0.0
    correct = 0
    total = 0
    for images, labels, teacher, _ in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        teacher = teacher.to(device, non_blocking=True)
        with torch.set_grad_enabled(train):
            with torch.autocast("cuda", dtype=torch.float16):
                logits, projected = model(images)
                ce = F.cross_entropy(logits, labels, label_smoothing=0.1)
                if feature_weight > 0:
                    cosine = (projected * teacher).sum(dim=-1)
                    feature = (1.0 - cosine).mean()
                else:
                    feature = torch.zeros((), device=device)
                loss = ce + feature_weight * feature
            if train:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(optimizer)
                scaler.update()
        total_loss += float(loss.item()) * len(labels)
        correct += int((logits.argmax(dim=-1) == labels).sum().item())
        total += len(labels)
    return total_loss / max(total, 1), correct / max(total, 1)


@torch.no_grad()
def predict(model, loader, device):
    model.eval()
    probs = []
    labels = []
    indices = []
    for images, batch_labels, _, batch_indices in loader:
        images = images.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16):
            logits, _ = model(images)
        probs.append(torch.softmax(logits.float(), dim=-1).cpu().numpy())
        labels.append(batch_labels.numpy())
        indices.extend([int(i) for i in batch_indices])
    return np.concatenate(probs), np.concatenate(labels), indices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--finetune-epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--finetune-lr", type=float, default=1e-4)
    parser.add_argument("--feature-weight", type=float, default=0.5)
    parser.add_argument("--hard-multiplier", type=float, default=1.0)
    parser.add_argument("--synthetic-multiplier", type=float, default=1.0)
    parser.add_argument("--stage2-synthetic-fraction", type=float, default=0.15)
    parser.add_argument("--tag", default="")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--teacher", default=str(TEACHER))
    parser.add_argument("--init-checkpoint", default="")
    args = parser.parse_args()

    global CHECKPOINT, METRICS
    if args.tag:
        CHECKPOINT = DATA / f"v2_student_{args.tag}.pt"
        METRICS = DATA / f"v2_metrics_{args.tag}.json"

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("device", device, torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    rows = [row for row in rows if Path(row["cache_path"]).exists()]
    teacher = np.load(args.teacher)
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "val"]
    cal_rows = [row for row in rows if row["split"] == "cal"]
    test_rows = [row for row in rows if row["split"] == "test"]
    print(
        f"train={len(train_rows)} val={len(val_rows)} cal={len(cal_rows)} test={len(test_rows)}"
    )

    train_ds = ManifestDataset(train_rows, teacher, train=True)
    val_ds = ManifestDataset(val_rows, teacher, train=False)
    cal_ds = ManifestDataset(cal_rows, teacher, train=False)
    test_ds = ManifestDataset(test_rows, teacher, train=False)

    def sample_weight(row: dict) -> float:
        weight = float(row["sample_weight"])
        if row["source"] == "labeled_hard_negative":
            weight *= args.hard_multiplier
        if row["source"] == "synthetic":
            weight *= args.synthetic_multiplier
        return max(weight, 0.05)

    weights = torch.tensor([sample_weight(row) for row in train_rows], dtype=torch.double)
    sampler = WeightedRandomSampler(weights, num_samples=len(train_rows), replacement=True)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=8,
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=4,
    )
    val_loader = DataLoader(
        val_ds, batch_size=128, shuffle=False, num_workers=6, pin_memory=True
    )
    cal_loader = DataLoader(
        cal_ds, batch_size=128, shuffle=False, num_workers=6, pin_memory=True
    )
    test_loader = DataLoader(
        test_ds, batch_size=128, shuffle=False, num_workers=6, pin_memory=True
    )

    model = Student(pretrained=not bool(args.init_checkpoint)).to(device)
    if args.init_checkpoint:
        checkpoint = torch.load(args.init_checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model"])
        print("initialized from", args.init_checkpoint)
    print("student params M", sum(p.numel() for p in model.parameters()) / 1e6)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(args.epochs, 1)
    )
    scaler = torch.amp.GradScaler("cuda", enabled=torch.cuda.is_available())

    best_score = -1.0
    history = []
    for epoch in range(1, args.epochs + 1):
        started = time.time()
        train_loss, train_acc = run_epoch(
            model, train_loader, optimizer, scaler, device, True, args.feature_weight
        )
        val_loss, val_acc = run_epoch(
            model, val_loader, optimizer, scaler, device, False, args.feature_weight
        )
        probs, labels, _ = predict(model, val_loader, device)
        m = choose_threshold(labels, probs, 0.90)
        f1 = 2 * m["precision"] * m["recall"] / max(m["precision"] + m["recall"], 1e-9)
        scheduler.step()
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "val_screen_precision": m["precision"],
            "val_screen_recall": m["recall"],
            "val_f1": f1,
            "seconds": round(time.time() - started, 1),
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))
        if f1 > best_score:
            best_score = f1
            torch.save(
                {
                    "model": model.state_dict(),
                    "args": vars(args),
                    "epoch": epoch,
                    "val": row,
                },
                CHECKPOINT,
            )

    # Real-data fine-tune: drop most synthetic samples, keep a small amount.
    stage2_rows = [
        row
        for row in train_rows
        if row["source"] != "synthetic" or random.random() < args.stage2_synthetic_fraction
    ]
    print("stage2 rows", len(stage2_rows))
    stage2_ds = ManifestDataset(stage2_rows, teacher, train=True)
    stage2_weights = torch.tensor(
        [max(float(row["sample_weight"]), 0.5) for row in stage2_rows], dtype=torch.double
    )
    stage2_sampler = WeightedRandomSampler(
        stage2_weights, num_samples=len(stage2_rows), replacement=True
    )
    stage2_loader = DataLoader(
        stage2_ds,
        batch_size=args.batch_size,
        sampler=stage2_sampler,
        num_workers=8,
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=4,
    )
    optimizer2 = torch.optim.AdamW(
        model.parameters(), lr=args.finetune_lr, weight_decay=1e-4
    )
    scheduler2 = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer2, T_max=max(args.finetune_epochs, 1)
    )
    for epoch in range(1, args.finetune_epochs + 1):
        started = time.time()
        train_loss, train_acc = run_epoch(
            model, stage2_loader, optimizer2, scaler, device, True, args.feature_weight
        )
        val_loss, val_acc = run_epoch(
            model, val_loader, optimizer2, scaler, device, False, args.feature_weight
        )
        probs, labels, _ = predict(model, val_loader, device)
        m = choose_threshold(labels, probs, 0.90)
        f1 = 2 * m["precision"] * m["recall"] / max(m["precision"] + m["recall"], 1e-9)
        scheduler2.step()
        row = {
            "epoch": f"ft{epoch}",
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "val_screen_precision": m["precision"],
            "val_screen_recall": m["recall"],
            "val_f1": f1,
            "seconds": round(time.time() - started, 1),
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))
        if f1 > best_score:
            best_score = f1
            torch.save(
                {
                    "model": model.state_dict(),
                    "args": vars(args),
                    "epoch": row["epoch"],
                    "val": row,
                },
                CHECKPOINT,
            )

    # Evaluate best checkpoint on calibration and test.
    checkpoint = torch.load(CHECKPOINT, map_location=device)
    model.load_state_dict(checkpoint["model"])
    cal_probs, cal_labels, _ = predict(model, cal_loader, device)
    m = choose_threshold(cal_labels, cal_probs, 0.95)
    test_probs, test_labels, test_indices = predict(model, test_loader, device)
    test_metrics = metrics_for_threshold(test_labels, test_probs, m["threshold"])

    # Per-stratum metrics on the test set.
    test_meta = {row["relative_path"]: row for row in csv.DictReader(TEST.open(encoding="utf-8-sig"))}
    strata = {}
    for index in range(len(test_rows)):
        row = test_rows[index]
        meta = test_meta.get(row["source_path"], {})
        band = meta.get("score_band", "unknown")
        label = int(test_rows[index]["label"])
        pred = int(test_probs[index, 1] >= m["threshold"])
        stat = strata.setdefault(band, {"tp": 0, "fp": 0, "fn": 0})
        if label == 1 and pred:
            stat["tp"] += 1
        elif label == 1:
            stat["fn"] += 1
        elif pred:
            stat["fp"] += 1
    for stat in strata.values():
        stat["precision"] = stat["tp"] / max(stat["tp"] + stat["fp"], 1)
        stat["recall"] = stat["tp"] / max(stat["tp"] + stat["fn"], 1)

    screenshot_correct = int(
        np.sum((test_probs.argmax(axis=1) == 0) & (test_labels == 0))
    )
    screenshot_total = int(np.sum(test_labels == 0))
    result = {
        "threshold": m["threshold"],
        "calibration": m,
        "test": test_metrics,
        "test_strata": strata,
        "screenshot_accuracy": screenshot_correct / screenshot_total if screenshot_total else 0.0,
        "history": history,
        "checkpoint": str(CHECKPOINT),
    }
    METRICS.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
