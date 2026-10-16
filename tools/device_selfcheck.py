"""在已连接的 Android 真机上跑 UI 冒烟自检，并拉回报告 + 截图。

用法：
    python tools/device_selfcheck.py                 # 自动找 adb
    python tools/device_selfcheck.py --out reports/device-selfcheck
    adb 不在 PATH 时： python tools/device_selfcheck.py --adb "C:/.../platform-tools/adb.exe"

流程：force-stop -> am start（带 --ez ui_selfcheck true）-> 轮询设备上的
ui_selfcheck.json -> adb pull 整个 selfcheck 目录 -> 打印结论。
in-app 侧见 app/ui_self_check.py。
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

PKG = "com.example.cubesolver"
ACTIVITY = "org.kivy.android.PythonActivity"
REMOTE_DIR = "/sdcard/Android/data/%s/files/selfcheck" % PKG
REMOTE_JSON = REMOTE_DIR + "/ui_selfcheck.json"


def _find_adb(explicit):
    if explicit:
        return explicit
    found = shutil.which("adb")
    if found:
        return found
    for root in (os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")):
        if root:
            cand = os.path.join(root, "platform-tools", "adb")
            if os.path.exists(cand):
                return cand
    return "adb"


def _run(adb, *args, timeout=60):
    return subprocess.run([adb, *args], capture_output=True, text=True, timeout=timeout)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=None)
    ap.add_argument("--out", default="reports/device-selfcheck")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)
    adb = _find_adb(args.adb)

    devices = _run(adb, "devices")
    if "device\n" not in devices.stdout + "\n":
        print("no device/emulator attached:\n" + devices.stdout)
        return 2

    os.makedirs(args.out, exist_ok=True)
    print("launching self-check on device ...")
    _run(adb, "shell", "am", "force-stop", PKG)
    _run(adb, "shell", "am", "start", "-n", "%s/%s" % (PKG, ACTIVITY),
         "--ez", "ui_selfcheck", "true")

    deadline = time.time() + args.timeout
    report = ""
    while time.time() < deadline:
        time.sleep(3)
        cat = _run(adb, "shell", "cat", REMOTE_JSON)
        if cat.returncode == 0 and cat.stdout.strip().startswith("{"):
            report = cat.stdout
            break

    if not report:
        print("timed out waiting for the report. Recent app log:")
        log = _run(adb, "logcat", "-d", "-t", "200")
        for line in (log.stdout or "").splitlines():
            if any(k in line for k in ("python", "Traceback", "Error", PKG)):
                print(line)
        return 1

    # 拉回整个目录（报告 + 截图）
    _run(adb, "pull", REMOTE_DIR, args.out)
    try:
        import json
        data = json.loads(report)
        print("status=%s checked=%s errors=%s"
              % (data.get("status"), data.get("checked"), data.get("errors")))
        for item in data.get("results", []):
            if item.get("status") != "ok":
                print("  FAIL %s\n%s" % (item.get("screen"), item.get("traceback", "")))
    except Exception:
        print(report)

    print("pulled to %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
