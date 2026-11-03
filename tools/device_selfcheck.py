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
    prefix=list(adb) if isinstance(adb,(tuple,list)) else [adb]
    return subprocess.run([*prefix, *args], capture_output=True, text=True, timeout=timeout)


def verified_report(data):
    """Older checks did not navigate; their success cannot certify visible UI."""
    rows=data.get('results',[])
    return (data.get('schema')==2 and data.get('status')=='pass' and data.get('errors')==0
            and data.get('image_validation')=='visible_pixels_and_variance'
            and data.get('screenshots_requested') is True and data.get('checked',0)>0
            and len(rows)==data['checked'] and all(row.get('status')=='ok'
                and row.get('screen')==row.get('current_screen') and isinstance(row.get('shot'),str) and row.get('shot')
                and not row['shot'].startswith('shot-failed:') for row in rows))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=None)
    ap.add_argument('--serial',default=None,help='Select one connected device explicitly')
    ap.add_argument("--out", default="reports/device-selfcheck")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)
    adb = _find_adb(args.adb)

    devices = _run(adb, "devices")
    available=[parts[0] for line in devices.stdout.splitlines() if len(parts:=line.split())>=2 and parts[1]=='device']
    if not available:
        print("no device/emulator attached:\n" + devices.stdout)
        return 2
    if args.serial is not None and args.serial not in available:
        print('selected device is not ready: '+args.serial);return 2
    if args.serial is None and len(available)!=1:
        print('multiple devices attached; choose --serial: '+', '.join(available));return 2
    adb=[adb,'-s',args.serial or available[0]]

    os.makedirs(args.out, exist_ok=True)
    print("launching self-check on device ...")
    _run(adb, "shell", "am", "force-stop", PKG)
    # A stale success report must not mask a crash or a missing test trigger.
    removed = _run(adb, "shell", "rm", "-f", REMOTE_JSON)
    if removed.returncode:
        print("could not remove previous self-check report: " + removed.stderr)
        return 1
    started = _run(adb, "shell", "am", "start", "-n", "%s/%s" % (PKG, ACTIVITY),
                   "--ez", "ui_selfcheck", "true")
    if started.returncode or "Error:" in started.stdout + started.stderr:
        print("could not start self-check: " + started.stdout + started.stderr)
        return 1

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
    pulled = _run(adb, "pull", REMOTE_DIR, args.out)
    try:
        import json
        data = json.loads(report)
        print("status=%s checked=%s errors=%s"
              % (data.get("status"), data.get("checked"), data.get("errors")))
        for item in data.get("results", []):
            if item.get("status") != "ok":
                print("  FAIL %s\n%s" % (item.get("screen"), item.get("traceback", "")))
        passed=verified_report(data)
        if data.get('schema')!=2 or data.get('image_validation')!='visible_pixels_and_variance':
            print('installed app uses the older check without verified navigation/images; this run cannot certify the updated source')
    except Exception:
        print(report)
        return 1

    print("pulled to %s" % args.out)
    return 0 if passed and not pulled.returncode else 1


if __name__ == "__main__":
    sys.exit(main())
