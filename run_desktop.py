"""桌面启动（抓崩溃日志）。
双击运行或: python run_desktop.py
崩溃日志写到: desktop_err.log 同目录
"""
import os
import sys
import traceback
import io

os.environ.setdefault("KIVY_NO_ARGS", "1")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
LOG = os.path.join(BASE, "desktop_err.log")


def main():
    from app.application import CubeApp
    CubeApp().run()


if __name__ == "__main__":
    # 捕获主线程异常 + Kivy 未处理异常
    def _hook(t, v, tb):
        try:
            with open(LOG, "w", encoding="utf-8") as f:
                f.write("=== cubesolver crash ===\n")
                traceback.print_exception(t, v, tb, file=f)
        except Exception:
            pass
        sys.__excepthook__(t, v, tb)

    sys.excepthook = _hook

    # Kivy 的异常也会走 logging；额外把 traceback 落到日志
    try:
        main()
    except Exception:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== cubesolver crash (main) ===\n")
            traceback.print_exc(file=f)
        raise
