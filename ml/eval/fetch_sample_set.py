"""Fetch a small, local-only evaluation set from Wikimedia Commons + picsum.

This is NOT the product golden set (which should be self-collected, 300-500
images). It is enough to sanity-check prompts, thresholds and the on-device
pipeline before real data exists.

Wikimedia content keeps its original license; this folder must stay local and
must not be shipped in the app.

Usage (from ml/, with HTTPS_PROXY set if needed):
    .venv/Scripts/python.exe eval/fetch_sample_set.py --count-per-source 20
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UA = "ShotWipeEval/0.1 (local offline evaluation)"
API = "https://commons.wikimedia.org/w/api.php"

SCREEN_TERMS = [
    "filetype:bitmap photograph of a computer screen",
    "filetype:bitmap photo of a television screen",
    "filetype:bitmap laptop screen photo",
    "filetype:bitmap monitor showing screen",
    "filetype:bitmap smartphone screen photograph",
    "filetype:bitmap computer screen glare",
    "filetype:bitmap screen reflection photo",
    "filetype:bitmap photograph of a display screen",
    "filetype:bitmap CRT monitor screen photo",
    "filetype:bitmap watching television screen",
]

PHOTO_TERMS = [
    "filetype:bitmap landscape photograph mountains",
    "filetype:bitmap portrait photograph person",
    "filetype:bitmap food photograph",
    "filetype:bitmap cat photograph",
    "filetype:bitmap street photograph city",
]


def commons_search(session: requests.Session, term: str, limit: int) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": term,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "1024",
    }
    for attempt in range(3):
        try:
            response = session.get(API, params=params, timeout=40)
            if response.status_code == 200 and response.headers.get(
                "content-type", ""
            ).startswith("application/json"):
                pages = response.json().get("query", {}).get("pages", {})
                return list(pages.values())
            time.sleep(2 + attempt * 2)
        except requests.RequestException:
            time.sleep(2 + attempt * 2)
    return []


def safe_name(title: str) -> str:
    name = re.sub(r"^File:", "", title)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:80] or "image"


def download(session: requests.Session, url: str, dest: Path) -> bool:
    try:
        response = session.get(url, timeout=60)
        if response.status_code != 200:
            return False
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        if min(image.size) < 320:
            return False
        image.save(dest, "JPEG", quality=88)
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count-per-source", type=int, default=20)
    args = parser.parse_args()

    screen_dir = DATA / "screen_photo"
    photo_dir = DATA / "photo"
    screen_dir.mkdir(parents=True, exist_ok=True)
    photo_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = UA
    manifest: list[dict] = []

    def collect(terms: list[str], target_dir: Path, label: str) -> None:
        seen_titles: set[str] = set()
        index = 0
        for term in terms:
            for page in commons_search(session, term, args.count_per_source):
                title = page.get("title", "")
                info = (page.get("imageinfo") or [{}])[0]
                mime = info.get("mime", "")
                if title in seen_titles or mime not in ("image/jpeg", "image/png"):
                    continue
                seen_titles.add(title)
                if (info.get("width") or 0) < 500 or (info.get("height") or 0) < 350:
                    continue
                url = info.get("thumburl") or info.get("url")
                if not url:
                    continue
                index += 1
                dest = target_dir / f"{label}_{index:03d}_{safe_name(title)}.jpg"
                if download(session, url, dest):
                    manifest.append(
                        {
                            "label": label,
                            "file": str(dest.relative_to(ROOT)),
                            "title": title,
                            "source": info.get("descriptionurl", ""),
                            "license": (info.get("extmetadata") or {})
                            .get("LicenseShortName", {})
                            .get("value", ""),
                        }
                    )
                    print(f"  saved {dest.name}")
                time.sleep(0.3)
            time.sleep(1)

    print("Wikimedia screen photos…")
    collect(SCREEN_TERMS, screen_dir, "screen")

    print("Wikimedia ordinary photos…")
    collect(PHOTO_TERMS, photo_dir, "photo")

    print("picsum negatives…")
    for i in range(1, 41):
        dest = photo_dir / f"picsum_{i:03d}.jpg"
        if download(
            session,
            f"https://picsum.photos/seed/shotwipe-{i:03d}/900/700",
            dest,
        ):
            manifest.append(
                {
                    "label": "photo",
                    "file": str(dest.relative_to(ROOT)),
                    "title": f"picsum seed shotwipe-{i:03d}",
                    "source": "https://picsum.photos",
                    "license": "Unsplash License (via picsum.photos)",
                }
            )
            print(f"  saved {dest.name}")

    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    counts: dict[str, int] = {}
    for item in manifest:
        counts[item["label"]] = counts.get(item["label"], 0) + 1
    print(f"done: {counts}")


if __name__ == "__main__":
    main()
