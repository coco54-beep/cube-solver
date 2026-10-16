"""UI 截图基线回归：逐屏截图并压缩成小灰度签名，和基线对比。

用法（需要本机有 Kivy 窗口 + Pillow）：
    python tools/ui_baselines.py --make  tests/ui_baselines      # 生成/更新基线
    python tools/ui_baselines.py --check tests/ui_baselines      # 对比，差异过大则退出码 1
    python tools/ui_baselines.py --check tests/ui_baselines --size 540x1170

只捕获"进入每个屏幕"的静态首屏；不触发求解/回放。基线按窗口尺寸区分，
改了布局后用 --make 重新生成即可。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

THRESHOLD = 8.0  # 0-255 灰度平均绝对差；超过视为布局回归


def _compare(base_dir, signatures):
    from PIL import Image
    import numpy as np
    rows = []
    worst = 0.0
    for name, sig in signatures.items():
        path = os.path.join(base_dir, "%s.png" % name)
        if not os.path.exists(path):
            rows.append((name, None, "missing-baseline"))
            worst = 999
            continue
        with Image.open(path) as im:
            base = np.asarray(im.convert("L"), dtype=np.int16)
        h = min(base.shape[0], sig.shape[0])
        w = min(base.shape[1], sig.shape[1])
        diff = float(np.abs(base[:h, :w] - sig[:h, :w]).mean())
        worst = max(worst, diff)
        rows.append((name, diff, "ok" if diff <= THRESHOLD else "diff"))
    return rows, worst


def run(mode, base_dir, width, height):
    os.environ["KIVY_NO_ARGS"] = "1"
    from kivy.core.window import Window
    Window.size = (width, height)
    from kivy.clock import Clock
    from app.application import CubeApp
    from app.ui_self_check import UISelfCheck

    out_dir = os.path.join("tmp", "ui_baselines_run_%dx%d" % (width, height))
    state = {"code": 0}

    class Runner(CubeApp):
        def on_start(self):
            self._checker = UISelfCheck(
                self, out_dir, screenshot=True, capture_signature=True,
                signature_dir=base_dir if mode == "make" else None,
                on_done=self._done)
            self._checker.start()

        def _done(self, data):
            if mode == "check":
                rows, worst = _compare(base_dir, self._checker.signatures)
                bad = [r for r in rows if r[2] != "ok"]
                print("checked %d screens, worst mean-abs-diff=%.2f (threshold %.1f)"
                      % (len(rows), worst, THRESHOLD))
                for name, diff, status in rows:
                    if status != "ok":
                        print("  %-24s %s (%s)" % (name, status,
                              "%.2f" % diff if diff is not None else "-"))
                state["code"] = 1 if bad else 0
            else:
                print("wrote %d baselines to %s" % (len(self._checker.signatures), base_dir))
            Clock.schedule_once(lambda *_: self.stop(), 0.2)

    Runner().run()
    return state["code"]


def main(argv):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--make", metavar="DIR")
    g.add_argument("--check", metavar="DIR")
    ap.add_argument("--size", default="540x1170")
    args = ap.parse_args(argv[1:])
    width, height = (int(v) for v in args.size.lower().split("x"))
    mode, base = ("make", args.make) if args.make else ("check", args.check)
    os.makedirs(base, exist_ok=True)
    return run(mode, base, width, height)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
