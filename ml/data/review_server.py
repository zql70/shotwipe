"""Local review server for ShotWipe candidate labeling.

Serves a single-page review UI, on-demand thumbnails (HEIC-aware), label saving
and CSV export. Binds to 127.0.0.1 only; no data leaves the machine.

Usage (from ml/):
    .venv/Scripts/python.exe data/review_server.py \
        --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

HERE = Path(__file__).resolve().parent
ALLOWED_LABELS = {"screen_photo", "screenshot", "other", "ignore"}
LIST_SETS = {
    "iphone": {
        "candidates": "review_screen_photo_candidates.csv",
        "low": "review_low_score_photos.csv",
        "screenshots": "review_screenshots.csv",
        "mid": "review_mid_score.csv",
    },
    "android": {
        "candidates": "android_review_screen_photo_candidates.csv",
        "low": "android_review_low_score_photos.csv",
        "screenshots": "android_review_screenshots.csv",
        "mid": "android_review_mid_score.csv",
    },
}
CACHE_DIR = HERE / ".review_cache"
CACHE_DIR.mkdir(exist_ok=True)
_LOCK = threading.Lock()


def load_lists(list_files: dict[str, str]) -> dict[str, list[dict]]:
    lists: dict[str, list[dict]] = {}
    for name, filename in list_files.items():
        path = HERE / filename
        rows = []
        if path.exists():
            for row in csv.DictReader(path.open(encoding="utf-8")):
                rows.append(
                    {
                        "path": row["relative_path"],
                        "auto_label": row.get("auto_label", ""),
                        "taken_at": row.get("taken_at", ""),
                        "width": row.get("width", ""),
                        "height": row.get("height", ""),
                        "score": row.get("p_screen_photo", ""),
                        "predicted": row.get("predicted", ""),
                        "list": name,
                    }
                )
        lists[name] = rows
    return lists


def load_labels(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_labels(path: Path, labels: dict[str, dict]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temp, path)


def thumbnail_bytes(source: Path, max_size: int, quality: int) -> bytes:
    key = hashlib.sha1(
        f"{source}|{source.stat().st_mtime_ns}|{max_size}".encode("utf-8")
    ).hexdigest()
    cache = CACHE_DIR / f"{key}.jpg"
    if cache.exists():
        return cache.read_bytes()
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True)
    data = buffer.getvalue()
    cache.write_bytes(data)
    return data


class ReviewHandler(BaseHTTPRequestHandler):
    lists: dict[str, list[dict]] = {}
    paths: dict[str, Path] = {}
    labels_file: Path = HERE / "review_labels.json"
    photo_root: Path = Path(".")
    export_name: str = "shotwipe_review_labels.csv"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(f"{self.address_string()} {format % args}")

    def _send(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            html = (HERE / "review_page.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/items":
            self._send_json(
                200,
                {
                    "lists": self.lists,
                    "labels": load_labels(self.labels_file),
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                },
            )
            return
        if parsed.path == "/api/labels":
            self._send_json(200, {"labels": load_labels(self.labels_file)})
            return
        if parsed.path == "/export":
            self._export_csv()
            return
        if parsed.path in ("/thumb", "/image"):
            query = parse_qs(parsed.query)
            relative = (query.get("path") or [""])[0]
            source = self.paths.get(relative)
            if source is None or not source.is_file():
                self._send_json(404, {"error": "image not found"})
                return
            try:
                if parsed.path == "/thumb":
                    data = thumbnail_bytes(source, 360, 82)
                else:
                    data = thumbnail_bytes(source, 1600, 88)
                self._send(200, data, "image/jpeg")
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/labels":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send_json(400, {"error": "invalid json"})
            return
        path = payload.get("path", "")
        label = payload.get("label", "")
        notes = str(payload.get("notes", ""))[:2000]
        if path not in self.paths:
            self._send_json(400, {"error": "unknown path"})
            return
        if label not in ALLOWED_LABELS and label != "":
            self._send_json(400, {"error": "invalid label"})
            return
        with _LOCK:
            labels = load_labels(self.labels_file)
            if label or notes:
                labels[path] = {
                    "label": label,
                    "notes": notes,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            else:
                labels.pop(path, None)
            save_labels(self.labels_file, labels)
        self._send_json(200, {"ok": True, "labeled": len(labels)})

    def _export_csv(self) -> None:
        labels = load_labels(self.labels_file)
        fields = [
            "list",
            "relative_path",
            "auto_label",
            "taken_at",
            "p_screen_photo",
            "predicted",
            "human_label",
            "notes",
            "updated_at",
        ]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for name, rows in self.lists.items():
            for row in rows:
                label = labels.get(row["path"], {})
                writer.writerow(
                    {
                        "list": name,
                        "relative_path": row["path"],
                        "auto_label": row["auto_label"],
                        "taken_at": row["taken_at"],
                        "p_screen_photo": row["score"],
                        "predicted": row["predicted"],
                        "human_label": label.get("label", ""),
                        "notes": label.get("notes", ""),
                        "updated_at": label.get("updated_at", ""),
                    }
                )
        data = buffer.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header(
            "Content-Disposition", f'attachment; filename="{self.export_name}"'
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--suite", default="iphone", choices=sorted(LIST_SETS))
    parser.add_argument("--labels", default="")
    parser.add_argument("--export-name", default="")
    args = parser.parse_args()

    root = Path(args.root)
    lists = load_lists(LIST_SETS[args.suite])
    paths: dict[str, Path] = {}
    for rows in lists.values():
        for row in rows:
            source = root / row["path"]
            if source.is_file():
                paths[row["path"]] = source
    ReviewHandler.lists = lists
    ReviewHandler.paths = paths
    ReviewHandler.photo_root = root
    labels_file = Path(args.labels) if args.labels else HERE / (
        "review_labels.json" if args.suite == "iphone" else "android_review_labels.json"
    )
    ReviewHandler.labels_file = labels_file
    ReviewHandler.export_name = args.export_name or (
        "shotwipe_review_labels.csv"
        if args.suite == "iphone"
        else "android_review_labels.csv"
    )

    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    total = sum(len(rows) for rows in lists.values())
    print(f"ShotWipe review: http://{args.host}:{args.port}")
    print(f"items: {total}  candidates={len(lists['candidates'])} "
          f"low={len(lists['low'])} screenshots={len(lists['screenshots'])}")
    print(f"labels: {ReviewHandler.labels_file}")
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
