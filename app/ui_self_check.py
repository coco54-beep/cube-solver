"""UI 冒烟自检：逐个进入每个屏幕，捕获异常并截图，输出 JSON 报告。

用于"改动 -> 验证"闭环：不需要人工点，一次跑完所有输入页/目录页，
把每个屏幕的进入结果（ok / error + traceback）和截图写到输出目录。
既能在桌面运行（python run_desktop.py --ui-self-check <dir>），
也能在真机上由 adb 额外参数触发（见 tools/device_selfcheck.py）。

只做"构建 + 进入 + 截图"，不触发耗时求解 / 回放。
"""

import json
import os
import traceback

from kivy.clock import Clock
from kivy.core.window import Window

# 每个屏幕进入前的状态准备；只覆盖"构建 + 进入"安全的屏幕。
# 求解页 / 回放页需要真实 solve_result，且会启动线程，故不在此列。
SKIP = {"SolvingScreen", "PlaybackScreen", "PolyhedralPlaybackScreen",
        "DemoScreen", "DemoMenuScreen"}


def _steps(app):
    def cube3():
        app.new_cube(3)

    return [
        ("HomeScreen", cube3),
        ("IrregularDirectoryScreen", cube3),
        ("SpecialIrregularScreen", cube3),
        ("InputScreen", cube3),
        ("CameraScreen", cube3),
        ("MastermorphixScreen", lambda: app.new_mastermorphix(3)),
        ("MirrorScreen", lambda: app.new_mirror(3)),
        ("MorphixTwistScreen", lambda: app.new_mastermorphix(3)),
        ("PolyhedralScreen", lambda: app.new_polyhedral("fto", 3)),
        ("PolyhedralTwistScreen", lambda: app.new_polyhedral("fto", 3)),
        ("FormulaLibraryScreen", cube3),
        ("PracticeScreen", cube3),
        ("TwistScreen", cube3),
        ("SettingsScreen", cube3),
        ("Square1Screen", lambda: app.new_square1()),
        ("ShapeCubeScreen", lambda: app.new_shape_cube("axis")),
        ("MirrorTowerScreen", lambda: app.new_mirror_tower()),
    ]


SIGNATURE_SIZE = (60, 130)  # (宽, 高) 缩略灰度图，用于截图基线对比


def signature_array(path):
    """把一张截图压成小灰度数组，供基线回归对比。无 Pillow 时返回 None。"""
    try:
        from PIL import Image
        import numpy as np
        with Image.open(path) as im:
            im = im.convert("L").resize(SIGNATURE_SIZE)
            return np.asarray(im, dtype=np.int16)
    except Exception:
        return None


class UISelfCheck:
    """按帧推进的自检流程（截图需要窗口已渲染一帧）。"""

    def __init__(self, app, out_dir, screenshot=True, on_done=None, step_delay=0.35,
                 signature_dir=None, capture_signature=None):
        self.app = app
        self.out = out_dir
        self.screenshot = screenshot
        self.on_done = on_done
        self.step_delay = step_delay
        self.signature_dir = signature_dir
        self.capture_signature = (signature_dir is not None
                                  if capture_signature is None else bool(capture_signature))
        self.signatures = {}
        self.report = []
        self._steps = [s for s in _steps(app) if s[0] not in SKIP]
        self._index = 0
        self._pending = None
        self._t0 = None

    def start(self):
        os.makedirs(self.out, exist_ok=True)
        try:
            import time
            self._t0 = time.time()
        except Exception:
            pass
        Clock.schedule_once(self._next, self.step_delay)

    def _next(self, _dt):
        if self._index >= len(self._steps):
            self._finish()
            return
        name, setup = self._steps[self._index]
        self._index += 1
        try:
            setup()
            screen = self.app.root.get_screen(name)
            screen.on_pre_enter()
            on_enter = getattr(screen, "on_enter", None)
            if on_enter is not None:
                on_enter()
            self._pending = (name, None)
        except Exception:
            self.report.append({"screen": name, "status": "error",
                                "traceback": traceback.format_exc()})
            self._pending = None
        Clock.schedule_once(self._shot, self.step_delay)

    def _shot(self, _dt):
        name = self._pending[0] if self._pending else None
        if name is not None:
            entry = {"screen": name, "status": "ok", "shot": None}
            if self.screenshot:
                entry["shot"] = self._capture(name)
            self.report.append(entry)
        Clock.schedule_once(self._next, 0.05)

    def _capture(self, name):
        try:
            fn = Window.screenshot(name=name)
            if fn and os.path.exists(fn):
                dest = os.path.join(self.out, "%s.png" % name)
                os.replace(fn, dest)
                if self.capture_signature:
                    self._save_signature(name, dest)
                return os.path.basename(dest)
        except Exception:
            return "shot-failed: " + traceback.format_exc().splitlines()[-1]
        return None

    def _save_signature(self, name, path):
        sig = signature_array(path)
        if sig is None:
            return
        self.signatures[name] = sig
        if self.signature_dir:
            try:
                from PIL import Image
                Image.fromarray(sig.astype("uint8")).save(
                    os.path.join(self.signature_dir, "%s.png" % name))
            except Exception:
                pass

    def _finish(self):
        errors = [r for r in self.report if r["status"] == "error"]
        data = {
            "status": "pass" if not errors else "fail",
            "checked": len(self.report),
            "errors": len(errors),
            "results": self.report,
        }
        try:
            with open(os.path.join(self.out, "ui_selfcheck.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass
        if self.on_done is not None:
            try:
                self.on_done(data)
            except Exception:
                pass


def run_blocking(app, out_dir):
    """同步版本（不截图、不需事件循环），供测试 / 命令行使用。"""
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for name, setup in _steps(app):
        if name in SKIP:
            continue
        try:
            setup()
            screen = app.root.get_screen(name)
            screen.on_pre_enter()
            on_enter = getattr(screen, "on_enter", None)
            if on_enter is not None:
                on_enter()
            report.append({"screen": name, "status": "ok"})
        except Exception:
            report.append({"screen": name, "status": "error",
                           "traceback": traceback.format_exc()})
    errors = [r for r in report if r["status"] == "error"]
    data = {"status": "pass" if not errors else "fail", "checked": len(report),
            "errors": len(errors), "results": report}
    try:
        with open(os.path.join(out_dir, "ui_selfcheck.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


def requested():
    """是否请求运行 UI 自检（Android intent extra 或环境变量）。"""
    if os.environ.get("CUBESOLVER_UI_SELFCHECK"):
        return True
    try:
        from android import activity  # noqa: F401
        intent = activity.getIntent()
        extras = intent.getExtras() if intent is not None else None
        return bool(extras and extras.getBoolean("ui_selfcheck"))
    except Exception:
        return False


def default_output_dir():
    """选一个可写、且 adb 可拉取的目录。"""
    candidates = []
    env_dir = os.environ.get("CUBESOLVER_UI_SELFCHECK_DIR")
    if env_dir:
        candidates.append(env_dir)
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        ext = activity.getExternalFilesDir(None)
        if ext is not None:
            candidates.append(os.path.join(ext.getAbsolutePath(), "selfcheck"))
    except Exception:
        pass
    for var in ("ANDROID_PRIVATE", "ANDROID_APP_PATH"):
        base = os.environ.get(var)
        if base:
            candidates.append(os.path.join(base, "selfcheck"))
    candidates.append(os.path.join(os.getcwd(), "selfcheck"))
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            continue
    return os.getcwd()
