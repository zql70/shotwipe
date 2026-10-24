"""Score the Android manifest with the v2 MobileNetV4 TFLite model.

Input 224x224 NHWC 0-1 (normalization baked in the model), output 3 logits
[screenshot, screen_photo, other]. Also computes a dHash for dedupe.

Usage (from ml/):
    .venv/Scripts/python.exe data/mine_android_v2.py \
        --root "C:/Users/killian/Desktop/文档/xiaomi" \
        --manifest data/android_manifest.csv --workers 8
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
MODEL = HERE.parent / "app" / "assets" / "models" / "v2_screen_classifier.tflite"
INPUT_SIZE = 224
_WORKER = {}


def _init_worker(model_path: str) -> None:
    import pillow_heif
    from ai_edge_litert.interpreter import Interpreter

    pillow_heif.register_heif_opener()
    interpreter = Interpreter(model_path=model_path, num_threads=2)
    interpreter.allocate_tensors()
    _WORKER.update(
        interpreter=interpreter,
        input=interpreter.get_input_details()[0],
        output=interpreter.get_output_details()[0],
    )


def _phash(gray: np.ndarray) -> str:
    from PIL import Image

    image = Image.fromarray(gray).resize((9, 8), Image.BILINEAR)
    pixels = np.asarray(image, dtype=np.int16)
    bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def _score(task: tuple[str, str]) -> dict:
    relative, path = task
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    try:
        image = Image.open(path).convert("RGB")
    except Exception as exc:
        return {"relative_path": relative, "error": str(exc)[:120]}
    width, height = image.size
    side = min(width, height)
    square = image.crop(
        (
            (width - side) // 2,
            (height - side) // 2,
            (width + side) // 2,
            (height + side) // 2,
        )
    )
    phash = _phash(np.asarray(square.convert("L").resize((64, 64))))
    resized = square.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    interpreter = _WORKER["interpreter"]
    interpreter.set_tensor(_WORKER["input"]["index"], array[None, ...])
    interpreter.invoke()
    logits = interpreter.get_tensor(_WORKER["output"]["index"])[0]
    logits = logits - logits.max()
    exp = np.exp(logits)
    probs = exp / exp.sum()
    categories = ("screenshot", "screen_photo", "other")
    predicted = categories[int(np.argmax(probs))]
    return {
        "relative_path": relative,
        "width": width,
        "height": height,
        "phash": phash,
        "p_screenshot": float(probs[0]),
        "p_screen_photo": float(probs[1]),
        "p_other": float(probs[2]),
        "predicted": predicted,
        "error": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", default="data/android_manifest.csv")
    parser.add_argument("--out", default="data/android_scores.csv")
    parser.add_argument("--candidates", default="data/android_candidates.csv")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.20)
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    root = Path(args.root)
    tasks = [(row["relative_path"], str(root / row["relative_path"])) for row in rows]
    print(f"scoring {len(tasks)} images with {args.workers} workers", flush=True)
    started = time.time()
    results = {}
    with ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=_init_worker,
        initargs=(str(MODEL),),
    ) as pool:
        for index, result in enumerate(
            pool.map(_score, tasks, chunksize=8), 1
        ):
            results[result["relative_path"]] = result
            if index % 200 == 0:
                elapsed = time.time() - started
                rate = index / elapsed if elapsed else 0
                print(
                    f"\r{index}/{len(tasks)}  {rate:.1f} img/s  "
                    f"eta {(len(tasks)-index)/max(rate,1e-6)/60:.1f} min",
                    flush=True,
                )
    print()

    by_path = {row["relative_path"]: row for row in rows}
    fields = [
        "id",
        "relative_path",
        "auto_label",
        "taken_at",
        "width",
        "height",
        "phash",
        "p_screenshot",
        "p_screen_photo",
        "p_other",
        "predicted",
        "error",
    ]
    all_records = []
    candidates = []
    for path, meta in by_path.items():
        result = results.get(path, {})
        record = {
            "id": meta["id"],
            "relative_path": path,
            "auto_label": meta["auto_label"],
            "taken_at": meta["taken_at"],
            "width": result.get("width", meta.get("width", "")),
            "height": result.get("height", meta.get("height", "")),
            "phash": result.get("phash", ""),
            "p_screenshot": round(result.get("p_screenshot", 0.0), 4),
            "p_screen_photo": round(result.get("p_screen_photo", 0.0), 4),
            "p_other": round(result.get("p_other", 0.0), 4),
            "predicted": result.get("predicted", ""),
            "error": result.get("error", ""),
        }
        all_records.append(record)
        if (
            meta["auto_label"] != "screenshot"
            and not record["error"]
            and record["p_screen_photo"] >= args.threshold
        ):
            candidates.append(record)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_records)
    candidates.sort(key=lambda row: row["p_screen_photo"], reverse=True)
    with Path(args.candidates).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)

    buckets = {
        t: sum(1 for row in candidates if row["p_screen_photo"] >= t)
        for t in (0.65, 0.35, 0.20)
    }
    summary = {
        "images": len(all_records),
        "candidates": len(candidates),
        "buckets": buckets,
        "seconds": round(time.time() - started, 1),
    }
    (out.with_suffix(".summary.json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"scores={out} candidates={args.candidates}")


if __name__ == "__main__":
    main()
