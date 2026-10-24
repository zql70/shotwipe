"""真机扫描结果提取：拉取 App drift 数据库，输出统计并与离线挖掘对比。

用法：python ml/eval/device_pull_and_report.py
"""
from __future__ import annotations

import csv
import subprocess
from collections import Counter
from pathlib import Path

ADB = r"C:\Users\killian\AppData\Local\Android\Sdk\platform-tools\adb.exe"
PKG = "com.shotwipe.app"
OUT = Path(__file__).resolve().parent / "device_shotwipe.sqlite"
DATA = Path(__file__).resolve().parents[1] / "data"


def sh(*args: str, binary: bool = False) -> bytes | str:
    r = subprocess.run([ADB, *args], capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def main() -> None:
    data = sh(
        "exec-out", "run-as", PKG, "cat", "app_flutter/shotwipe.sqlite", binary=True
    )
    assert isinstance(data, bytes) and len(data) > 4096, "pull db failed"
    OUT.write_bytes(data)
    print(f"db saved: {OUT} ({len(data)//1024} KB)")

    import sqlite3

    con = sqlite3.connect(f"file:{OUT}?mode=ro", uri=True)
    rows = con.execute(
        "select platform_id, category, source, confidence, state, model_version"
        " from scanned_assets"
    ).fetchall()
    kv = dict(con.execute("select key, value from scan_state").fetchall())
    con.close()

    print(f"\n== scan_state ==\n{kv}")
    print(f"\n== rows: {len(rows)} ==")
    print("category/source:", Counter(f"{c}/{s}" for _, c, s, *_ in rows).most_common())
    print("state:", Counter(st for *_, st, _ in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]).most_common())

    model_sp = [conf for _, c, s, conf, _, _ in rows if s == "model" and c == "screen_photo"]
    model_shot = sum(1 for _, c, s, *_ in rows if s == "model" and c == "screenshot")
    meta_shot = sum(1 for _, c, s, *_ in rows if s == "metadata" and c == "screenshot")
    print(f"\nmetadata_screenshots={meta_shot}  model_screenshot_class={model_shot}")
    print(f"model screen_photo n={len(model_sp)}")
    for lo, hi in ((0.9, 1.01), (0.8, 0.9), (0.65, 0.8), (0.35, 0.65), (0.2, 0.35), (0.0, 0.2)):
        n = sum(1 for c in model_sp if lo <= c < hi)
        print(f"  [{lo:.2f},{hi:.22}): {n}")

    # 与离线 v2 挖掘对比（同样本库、同一模型、不同预处理/缩略图）
    scores = Path(DATA / "android_scores.csv")
    if scores.exists():
        with scores.open(encoding="utf-8") as f:
            off = [float(r["p_screen_photo"]) for r in csv.DictReader(f)]
        print(f"\noffline android_scores n={len(off)}")
        for t in (0.65, 0.35, 0.2):
            print(f"  >={t}: {sum(1 for p in off if p >= t)}")
        app_ge = sum(1 for c in model_sp if c >= 0.65)
        app_mid = sum(1 for c in model_sp if 0.35 <= c < 0.65)
        print(f"app on-device      >=0.65: {app_ge}  mid: {app_mid}")


if __name__ == "__main__":
    main()
