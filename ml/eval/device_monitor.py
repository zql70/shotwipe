"""真机扫描监控：触发 ShotWipe 全库扫描并采样进度/内存/CPU/温度。

用法（本地，不涉及任何数据上传）：
    python ml/eval/device_monitor.py [--no-tap]
输出每 15s 一行进度；扫描完成后打印汇总统计并退出。
"""
from __future__ import annotations

import argparse
import datetime
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ADB = r"C:\Users\killian\AppData\Local\Android\Sdk\platform-tools\adb.exe"
PKG = "com.shotwipe.app"


def sh(*args: str, binary: bool = False, timeout: int = 60) -> bytes | str:
    r = subprocess.run([ADB, *args], capture_output=True, timeout=timeout)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def pull_db(tmpdir: Path) -> tuple[sqlite3.Connection | None, str]:
    """run-as 拷出 drift 数据库（app_flutter/shotwipe.sqlite），失败返回 (None, 原因)。"""
    files = {}
    for suffix in ("", "-wal"):
        name = "shotwipe.sqlite" + suffix
        try:
            data = sh(
                "exec-out", "run-as", PKG, "cat", f"app_flutter/{name}", binary=True
            )
            # run-as 失败时 adb 会把错误文本当 stdout 返回，长度极短且非 sqlite 格式
            if isinstance(data, bytes) and len(data) > 4096:
                p = tmpdir / name
                p.write_bytes(data)
                files[suffix or "db"] = str(p)
        except Exception as e:  # noqa: BLE001
            return None, f"pull {name}: {e}"
    db = files.get("db")
    if not db:
        return None, "db missing"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.execute("select count(*) from scanned_assets").fetchone()
        return con, ""
    except sqlite3.Error as e:
        return None, f"sqlite: {e}"


def snapshot(con: sqlite3.Connection) -> dict:
    s: dict = {}
    s["rows"] = con.execute("select count(*) from scanned_assets").fetchone()[0]
    s["by_cat"] = dict(
        con.execute(
            "select category || '/' || source, count(*) from scanned_assets"
            " group by 1"
        ).fetchall()
    )
    s["model_ge_065"] = con.execute(
        "select count(*) from scanned_assets where source='model'"
        " and category='screen_photo' and confidence>=0.65"
    ).fetchone()[0]
    s["model_035_065"] = con.execute(
        "select count(*) from scanned_assets where source='model'"
        " and category='screen_photo' and confidence>=0.35 and confidence<0.65"
    ).fetchone()[0]
    kv = dict(con.execute("select key, value from scan_state").fetchall())
    s["state"] = kv
    return s


def device_stats() -> str:
    out = []
    try:
        mem = sh("shell", "dumpsys", "meminfo", PKG)
        for line in mem.splitlines():
            if line.strip().startswith("TOTAL PSS:"):
                out.append("pss " + line.split(":")[1].strip().split()[0] + "KB")
                break
    except Exception as e:  # noqa: BLE001
        out.append(f"mem:{e}")
    try:
        top = sh("shell", "top", "-b", "-n", "1")
        for line in top.splitlines():
            if PKG in line and "%" in line:
                cols = line.split()
                if len(cols) > 9:
                    out.append("cpu " + cols[9] + "%")
                break
    except Exception as e:  # noqa: BLE001
        out.append(f"top:{e}")
    try:
        bat = sh("shell", "dumpsys", "battery")
        for line in bat.splitlines():
            if "temperature" in line:
                out.append("bat " + str(int(line.split(":")[1].strip()) / 10) + "C")
                break
    except Exception as e:  # noqa: BLE001
        out.append(f"bat:{e}")
    return " ".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tap", action="store_true", help="不点击开始，只监控")
    args = ap.parse_args()

    if not args.no_tap:
        print(f"[{datetime.datetime.now():%H:%M:%S}] tap 开始扫描 (720,1824)", flush=True)
        sh("shell", "input", "tap", "720", "1824")
    t0 = time.time()

    prev_rows = -1
    stable = 0
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        for i in range(120):  # 最长 30 分钟
            time.sleep(15)
            elapsed = int(time.time() - t0)
            con, err = pull_db(tmpdir)
            if con is None:
                print(f"[{elapsed:4d}s] db not ready: {err}", flush=True)
                continue
            try:
                s = snapshot(con)
            except sqlite3.Error as e:
                print(f"[{elapsed:4d}s] sqlite busy: {e}", flush=True)
                continue
            finally:
                con.close()
            done = bool(s["state"].get("last_scan_ms"))
            print(
                f"[{elapsed:4d}s] rows={s['rows']} "
                f"screen_shot/meta={s['by_cat'].get('screenshot/metadata', 0)} "
                f"model_pos={s['by_cat'].get('screen_photo/model', 0)} "
                f"ge065={s['model_ge_065']} mid={s['model_035_065']} "
                f"done={done} {device_stats()}",
                flush=True,
            )
            if done and s["rows"] == prev_rows:
                stable += 1
                if stable >= 2:
                    print(
                        f"SCAN COMPLETE in ~{elapsed}s total={s['state'].get('last_scan_total')}",
                        flush=True,
                    )
                    return
            else:
                stable = 0
            prev_rows = s["rows"]
    print("TIMEOUT after 30min", flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
