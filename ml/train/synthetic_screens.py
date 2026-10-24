"""Generate synthetic screen photos from real screenshots and real backgrounds.

Each sample composes a screenshot onto a phone/tablet/monitor/kiosk, applies
perspective, moire, glare/reflection, blur/noise/JPEG, and places it in a real
photo background. Output is 320x320 (center crop), matching the training cache.

Usage (from ml/, CPU is fine):
    .venv/Scripts/python.exe train/synthetic_screens.py \
        --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷" \
        --count 8000 --workers 8
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"
SHOT_CACHE = DATA / "synthetic_sources" / "shots"
BG_CACHE = DATA / "synthetic_sources" / "bg"
OUT_DIR = DATA / "synthetic" / "images"
PLAN = DATA / "synthetic" / "plan.csv"
MANIFEST = DATA / "synthetic" / "manifest.csv"
LABELED = DATA / "labeled_all.csv"
MANIFEST_IPHONE = DATA / "iphone_manifest.csv"
SCORES = DATA / "iphone_scores.csv"


def _cache_source(args: tuple) -> str:
    source, target, max_size = args
    if target.exists():
        return str(target)
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    try:
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((max_size, max_size))
            image.save(target, "JPEG", quality=92)
        return str(target)
    except Exception as exc:
        return f"ERROR:{source}:{exc}"


def cover(image: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = max(width / w, height / h)
    nw, nh = max(width, int(round(w * scale))), max(height, int(round(h * scale)))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    x = (nw - width) // 2
    y = (nh - height) // 2
    return resized[y : y + height, x : x + width]


def add_glare(screen: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = screen.shape[:2]
    if rng.random() < 0.25:
        return screen
    overlay = np.zeros_like(screen, dtype=np.float32)
    cx, cy = rng.randint(0, w), rng.randint(0, h)
    axes = (rng.randint(w // 5, max(w // 2, w // 5 + 1)), rng.randint(h // 6, max(h // 2, h // 6 + 1)))
    cv2.ellipse(overlay, (cx, cy), axes, rng.randint(0, 180), 0, 360, (255, 255, 255), -1)
    overlay = cv2.GaussianBlur(overlay, (0, 0), max(3, w // 20))
    alpha = rng.uniform(0.08, 0.40)
    overlay = overlay * (alpha / 255.0)
    # warm or cool tint
    tint = np.array([rng.uniform(0.9, 1.0), rng.uniform(0.9, 1.0), rng.uniform(0.9, 1.0)], dtype=np.float32)
    overlay = overlay * tint
    return np.clip(screen.astype(np.float32) * (1 - overlay) + 255 * overlay, 0, 255).astype(np.uint8)


def add_reflection(screen: np.ndarray, background: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = screen.shape[:2]
    if rng.random() < 0.35:
        return screen
    reflection = cv2.resize(background, (w, h), interpolation=cv2.INTER_AREA)
    reflection = cv2.GaussianBlur(reflection, (0, 0), max(2, w // 30))
    reflection = (reflection * 0.55).astype(np.uint8)
    side = rng.choice(["left", "right", "top", "bottom"])
    ramp = np.linspace(0.0, 1.0, w if side in ("left", "right") else h, dtype=np.float32)
    if side in ("right", "bottom"):
        ramp = ramp[::-1]
    mask = ramp.reshape(1, -1, 1) if side in ("left", "right") else ramp.reshape(-1, 1, 1)
    alpha = mask * rng.uniform(0.04, 0.22)
    return np.clip(screen.astype(np.float32) * (1 - alpha) + reflection * alpha, 0, 255).astype(np.uint8)


def add_moire(screen: np.ndarray, rng: random.Random) -> np.ndarray:
    if rng.random() < 0.30:
        return screen
    h, w = screen.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    theta = rng.uniform(0, math.pi)
    freq = rng.uniform(1.5, 6.0)
    phase = rng.uniform(0, 2 * math.pi)
    pattern = np.sin(2 * math.pi * (xx * math.cos(theta) + yy * math.sin(theta)) / freq + phase)
    alpha = rng.uniform(0.03, 0.12)
    tint = np.stack([pattern, pattern, pattern], axis=-1)
    return np.clip(screen.astype(np.float32) + tint * 255 * alpha, 0, 255).astype(np.uint8)


def build_device(
    shot: np.ndarray, background: np.ndarray, device: str, rng: random.Random
) -> np.ndarray:
    if device in ("monitor", "tv"):
        aspect = 16 / 9
        inner_w = rng.randint(360, 520)
        inner_h = int(inner_w / aspect)
        bezel = rng.randint(7, 16)
        stand = device == "monitor" and rng.random() < 0.65
    elif device == "phone":
        aspect = 9 / 19.5
        inner_h = rng.randint(380, 540)
        inner_w = int(inner_h * aspect)
        bezel = rng.randint(5, 10)
        stand = False
    elif device == "tablet":
        aspect = 4 / 3
        inner_w = rng.randint(300, 440)
        inner_h = int(inner_w / aspect)
        bezel = rng.randint(8, 14)
        stand = False
    else:  # kiosk
        aspect = 3 / 4
        inner_h = rng.randint(360, 500)
        inner_w = int(inner_h * aspect)
        bezel = rng.randint(16, 28)
        stand = True

    screen = cover(shot, inner_w, inner_h)
    # Pixel-grid aliasing + focus variation, like a real camera capture.
    if rng.random() < 0.55:
        factor = rng.uniform(0.65, 0.92)
        small = cv2.resize(
            screen,
            (max(8, int(inner_w * factor)), max(8, int(inner_h * factor))),
            interpolation=cv2.INTER_AREA,
        )
        screen = cv2.resize(small, (inner_w, inner_h), interpolation=cv2.INTER_LINEAR)
    if rng.random() < 0.4:
        screen = cv2.GaussianBlur(screen, (0, 0), rng.uniform(0.3, 0.8))
    screen = np.clip(
        screen.astype(np.float32) * rng.uniform(0.85, 1.10) + rng.uniform(-10, 10),
        0,
        255,
    ).astype(np.uint8)
    if rng.random() < 0.5:
        grad = np.linspace(0, 1, inner_h, dtype=np.float32)[:, None, None]
        grad = grad * rng.uniform(0.02, 0.10)
        screen = np.clip(
            screen.astype(np.float32) * (1 - grad) + 255 * grad, 0, 255
        ).astype(np.uint8)
    screen = add_glare(screen, rng)
    screen = add_reflection(screen, background, rng)
    screen = add_moire(screen, rng)

    bezel_color = rng.randint(10, 45)
    front = np.zeros((inner_h + 2 * bezel, inner_w + 2 * bezel, 4), dtype=np.uint8)
    front[..., :3] = bezel_color
    front[..., 3] = 255
    front[bezel : bezel + inner_h, bezel : bezel + inner_w, :3] = screen
    edge = min(255, bezel_color + rng.randint(8, 25))
    cv2.rectangle(
        front,
        (0, 0),
        (front.shape[1] - 1, front.shape[0] - 1),
        (edge, edge, edge, 255),
        1,
    )
    if rng.random() < 0.5:
        cv2.line(front, (0, 1), (front.shape[1] - 1, 1), (edge + 20, edge + 20, edge + 20, 255), 1)

    if stand:
        base_w = int(front.shape[1] * rng.uniform(0.22, 0.34))
        base_h = rng.randint(10, 24)
        stem_w = max(8, base_w // 4)
        cx = front.shape[1] // 2
        stem_top = front.shape[0] - 2
        canvas_h = front.shape[0] + base_h + 18
        extended = np.zeros((canvas_h, front.shape[1], 4), dtype=np.uint8)
        extended[: front.shape[0]] = front
        cv2.rectangle(
            extended,
            (cx - stem_w // 2, stem_top),
            (cx + stem_w // 2, stem_top + 16),
            (bezel_color, bezel_color, bezel_color, 255),
            -1,
        )
        cv2.ellipse(
            extended,
            (cx, stem_top + 16 + base_h // 2),
            (base_w // 2, base_h // 2),
            0,
            0,
            360,
            (bezel_color - 4, bezel_color - 4, bezel_color - 4, 255),
            -1,
        )
        front = extended

    h, w = front.shape[:2]
    scale = rng.uniform(0.55, 0.92)
    tw = max(80, int(w * scale))
    th = max(80, int(h * scale))
    front = cv2.resize(front, (tw, th), interpolation=cv2.INTER_AREA)
    cx = 320 + rng.randint(-45, 45)
    cy = 320 + rng.randint(-45, 45)
    jitter = rng.uniform(0.03, 0.12)
    dx, dy = tw / 2, th / 2
    jx, jy = tw * jitter, th * jitter
    dst = np.float32(
        [
            [cx - dx + rng.uniform(-jx, jx), cy - dy + rng.uniform(-jy, jy)],
            [cx + dx + rng.uniform(-jx, jx), cy - dy + rng.uniform(-jy, jy)],
            [cx + dx + rng.uniform(-jx, jx), cy + dy + rng.uniform(-jy, jy)],
            [cx - dx + rng.uniform(-jx, jx), cy + dy + rng.uniform(-jy, jy)],
        ]
    )
    src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(
        front,
        matrix,
        (640, 640),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    alpha = (warped[..., 3].astype(np.float32) / 255.0)[..., None]
    mask = warped[..., 3]
    shadow = cv2.GaussianBlur(mask, (0, 0), 12).astype(np.float32) / 255.0
    shadow = np.roll(shadow, rng.randint(4, 14), axis=0)
    shadow = np.roll(shadow, rng.randint(-8, 8), axis=1)
    background = np.clip(background.astype(np.float32) * (1 - 0.35 * shadow[..., None]), 0, 255)
    return np.clip(
        background * (1 - alpha) + warped[..., :3].astype(np.float32) * alpha, 0, 255
    ).astype(np.uint8)


def finish(image: np.ndarray, rng: random.Random) -> np.ndarray:
    image = image.astype(np.float32)
    image *= rng.uniform(0.82, 1.08)
    image += rng.uniform(-8, 8)
    image = np.clip(image, 0, 255)
    if rng.random() < 0.5:
        image = cv2.GaussianBlur(image, (0, 0), rng.uniform(0.2, 0.9))
    if rng.random() < 0.6:
        noise = np.random.RandomState(rng.randint(0, 2**31)).normal(0, rng.uniform(1, 5), image.shape)
        image = np.clip(image + noise, 0, 255)
    # Vignette.
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - w / 2) ** 2 + (yy - h / 2) ** 2) / (math.hypot(w / 2, h / 2))
    vignette = np.clip(1.0 - rng.uniform(0.0, 0.25) * d, 0.7, 1.0)
    image *= vignette[..., None]
    # Center crop to 320, matching the app's thumbnail crop.
    image = image[160:480, 160:480]
    return np.clip(image, 0, 255).astype(np.uint8)


def generate(row: dict) -> dict:
    rng = random.Random(int(row["seed"]))
    shot = cv2.imread(row["shot_path"])
    background = cv2.imread(row["bg_path"])
    if shot is None or background is None:
        return {"error": "read failed"}
    background = cover(background, 640, 640)
    if rng.random() < 0.6:
        background = cv2.GaussianBlur(background, (0, 0), rng.uniform(0.4, 1.8))
    background = np.clip(background.astype(np.float32) * rng.uniform(0.55, 0.9), 0, 255).astype(np.uint8)
    out = build_device(shot, background, row["device"], rng)
    out = finish(out, rng)
    cv2.imwrite(row["out_path"], out, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return {"out_path": row["out_path"], "error": ""}


def prepare_sources(root: Path, count: int, workers: int, rng: random.Random) -> tuple[list[Path], list[Path]]:
    labeled = {row["relative_path"] for row in csv.DictReader(LABELED.open(encoding="utf-8-sig"))}
    manifest = list(csv.DictReader(MANIFEST_IPHONE.open(encoding="utf-8")))
    screenshots = [
        root / row["relative_path"]
        for row in manifest
        if row["auto_label"] == "screenshot" and row["relative_path"] not in labeled
    ]
    scores = {
        row["relative_path"]: row
        for row in csv.DictReader(SCORES.open(encoding="utf-8"))
    }
    backgrounds = [
        root / path
        for path, row in scores.items()
        if row["auto_label"] in ("photo_candidate", "other_png")
        and path not in labeled
        and not row["error"]
        and float(row["p_screen_photo"] or 0) < 0.02
    ]
    rng.shuffle(screenshots)
    rng.shuffle(backgrounds)
    screenshots = screenshots[: min(1200, len(screenshots))]
    backgrounds = backgrounds[: min(600, len(backgrounds))]

    SHOT_CACHE.mkdir(parents=True, exist_ok=True)
    BG_CACHE.mkdir(parents=True, exist_ok=True)

    shot_paths = [SHOT_CACHE / f"shot_{i:04d}.jpg" for i in range(len(screenshots))]
    bg_paths = [BG_CACHE / f"bg_{i:04d}.jpg" for i in range(len(backgrounds))]
    tasks = list(zip(screenshots, shot_paths, [1280] * len(screenshots))) + list(
        zip(backgrounds, bg_paths, [900] * len(backgrounds))
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_cache_source, tasks, chunksize=8))
    errors = [r for r in results if str(r).startswith("ERROR")]
    print(f"source cache: shots={len(screenshots)} backgrounds={len(backgrounds)} errors={len(errors)}")
    if len(screenshots) == 0 or len(backgrounds) == 0:
        raise SystemExit("no sources")
    return shot_paths, bg_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--count", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    root = Path(args.root)
    shot_paths, bg_paths = prepare_sources(root, args.count, args.workers, rng)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN.parent.mkdir(parents=True, exist_ok=True)

    orientations = {}
    for shot in shot_paths:
        probe = cv2.imread(str(shot))
        orientations[shot] = probe is not None and probe.shape[0] > probe.shape[1]

    plans = []
    for i in range(args.count):
        shot = rng.choice(shot_paths)
        portrait = orientations[shot]
        if portrait:
            device = rng.choices(["phone", "tablet", "kiosk"], weights=[0.70, 0.20, 0.10])[0]
        else:
            device = rng.choices(["monitor", "tv", "tablet"], weights=[0.55, 0.35, 0.10])[0]
        plans.append(
            {
                "index": i,
                "shot_path": str(shot),
                "bg_path": str(rng.choice(bg_paths)),
                "device": device,
                "seed": rng.randint(0, 2**31 - 1),
                "out_path": str(OUT_DIR / f"syn_{i:06d}.jpg"),
            }
        )
    with PLAN.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(plans[0].keys()))
        writer.writeheader()
        writer.writerows(plans)

    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(generate, plans, chunksize=8))
    errors = [r for r in results if r["error"]]
    print(f"generated {len(plans) - len(errors)}/{len(plans)} in {(time.time()-started)/60:.1f} min")
    if errors:
        print("errors", len(errors), errors[:3])

    fields = ["relative_path", "shot_source", "bg_source", "device", "seed"]
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for plan, result in zip(plans, results):
            if result["error"]:
                continue
            writer.writerow(
                {
                    "relative_path": os.path.basename(result["out_path"]),
                    "shot_source": os.path.basename(plan["shot_path"]),
                    "bg_source": os.path.basename(plan["bg_path"]),
                    "device": plan["device"],
                    "seed": plan["seed"],
                }
            )
    print(f"manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
