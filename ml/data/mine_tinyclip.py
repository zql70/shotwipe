"""Score every image in a manifest with TinyCLIP and compute a perceptual hash.

Runs the same 224px center-crop + prompt-max scoring as the app. High-confidence
screenshots skip model inference (they are metadata-labeled) but still get a
pHash. Writes a full score table and a screen-photo candidate list for review.

Usage (from ml/):
    .venv/Scripts/python.exe data/mine_tinyclip.py \
        --manifest data/iphone_manifest.csv \
        --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷" \
        --workers 6
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TFLITE = ROOT.parent / "app" / "assets" / "models" / "tinyclip_40m32_image.tflite"
PROMPTS = ROOT.parent / "app" / "assets" / "models" / "tinyclip_40m32_prompts.json"
INPUT_SIZE = 224

_WORKER = {}


def _init_worker(tflite: str, prompts: str) -> None:
    import pillow_heif
    from ai_edge_litert.interpreter import Interpreter

    pillow_heif.register_heif_opener()
    interpreter = Interpreter(model_path=tflite, num_threads=2)
    interpreter.allocate_tensors()
    categories = json.loads(Path(prompts).read_text(encoding="utf-8"))["categories"]
    vectors = []
    labels = []
    for category, value in categories.items():
        for item in value["prompts"]:
            vector = np.asarray(item["embedding"], dtype=np.float32)
            vectors.append(vector / np.linalg.norm(vector))
            labels.append(category)
    _WORKER.update(
        interpreter=interpreter,
        input=interpreter.get_input_details()[0],
        output=interpreter.get_output_details()[0],
        vectors=np.stack(vectors),
        labels=np.array(labels),
    )


def _phash(gray: np.ndarray) -> str:
    """Simple 64-bit dHash on a 9x8 grayscale crop; dependency-free."""
    from PIL import Image

    image = Image.fromarray(gray).resize((9, 8), Image.BILINEAR)
    pixels = np.asarray(image, dtype=np.int16)
    bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def _score(path: str, skip_model: bool) -> dict:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    try:
        image = Image.open(path).convert("RGB")
    except Exception as exc:
        return {"error": str(exc)[:120]}
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
    if skip_model:
        return {"width": width, "height": height, "phash": phash, "scores": None}
    resized = square.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    interpreter = _WORKER["interpreter"]
    interpreter.set_tensor(_WORKER["input"]["index"], array[None, ...])
    interpreter.invoke()
    embedding = interpreter.get_tensor(_WORKER["output"]["index"])[0]
    embedding /= np.linalg.norm(embedding)
    sims = _WORKER["vectors"] @ embedding
    labels = _WORKER["labels"]
    logits = {}
    for category in sorted(set(labels.tolist())):
        logits[category] = float(sims[labels == category].max()) * 100.0
    maximum = max(logits.values())
    exp = {category: math.exp(value - maximum) for category, value in logits.items()}
    total = sum(exp.values())
    return {
        "width": width,
        "height": height,
        "phash": phash,
        "scores": {category: value / total for category, value in exp.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", default="data/iphone_scores.csv")
    parser.add_argument("--candidates", default="data/iphone_screen_photo_candidates.csv")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--threshold", type=float, default=0.20)
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    tasks = []
    for row in rows:
        if row["is_video"] == "1" or row["auto_label"] == "unsupported":
            continue
        skip_model = row["auto_label"] == "screenshot"
        tasks.append((str(Path(args.root) / row["relative_path"]), skip_model))
    print(f"scoring {len(tasks)} images with {args.workers} workers", flush=True)

    started = time.time()
    results = []
    with ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=_init_worker,
        initargs=(str(TFLITE), str(PROMPTS)),
    ) as pool:
        futures = {pool.submit(_score, path, skip): (path, skip) for path, skip in tasks}
        for index, future in enumerate(futures, 1):
            path, skip = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"error": str(exc)[:120]}
            results.append((path, skip, result))
            if index % 100 == 0:
                elapsed = time.time() - started
                rate = index / elapsed if elapsed else 0
                print(
                    f"\r{index}/{len(tasks)}  {rate:.2f} img/s  "
                    f"eta {(len(tasks) - index) / rate / 60:.1f} min",
                    flush=True,
                )
    print()

    by_path = {row["relative_path"]: row for row in rows}
    score_fields = [
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
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    candidate_rows = []
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=score_fields)
        writer.writeheader()
        for path, skip, result in results:
            relative = os.path.relpath(path, args.root)
            row = by_path.get(relative) or {}
            scores = result.get("scores") or {}
            record = {
                "id": row.get("id", ""),
                "relative_path": relative,
                "auto_label": row.get("auto_label", ""),
                "taken_at": row.get("taken_at", ""),
                "width": result.get("width", row.get("width", "")),
                "height": result.get("height", row.get("height", "")),
                "phash": result.get("phash", ""),
                "p_screenshot": round(scores.get("screenshot", 0.0), 4) if scores else "",
                "p_screen_photo": round(scores.get("screen_photo", 0.0), 4) if scores else "",
                "p_other": round(scores.get("other", 0.0), 4) if scores else "",
                "predicted": max(scores, key=scores.get) if scores else "",
                "error": result.get("error", ""),
            }
            writer.writerow(record)
            if scores and scores.get("screen_photo", 0) >= args.threshold:
                candidate_rows.append(record)
    candidate_rows.sort(key=lambda r: float(r["p_screen_photo"]), reverse=True)
    with Path(args.candidates).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=score_fields)
        writer.writeheader()
        writer.writerows(candidate_rows)

    buckets = {}
    for record in candidate_rows:
        score = float(record["p_screen_photo"])
        for threshold in (0.55, 0.35, 0.20):
            if score >= threshold:
                buckets[threshold] = buckets.get(threshold, 0) + 1
    print(
        f"done in {(time.time() - started) / 60:.1f} min; "
        f"candidates {len(candidate_rows)}; thresholds {buckets}"
    )
    print(f"scores: {out}")
    print(f"candidates: {args.candidates}")


if __name__ == "__main__":
    main()
