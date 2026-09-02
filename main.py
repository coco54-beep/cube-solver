"""应用入口：启动 Kivy 魔方还原 App。

运行: python main.py

Android 上由 SDL2 bootstrap 以 __main__ 方式执行本文件（PyRun_SimpleFile）。
为便于定位移动端启动崩溃，这里把启动错误写入应用数据目录下的 crash.log。
"""

import os
import sys
import traceback

os.environ.setdefault("KIVY_NO_ARGS", "1")


def _crash_log_path():
    """写入应用可访问的崩溃日志目录。"""
    candidates = []
    if "ANDROID_PRIVATE" in os.environ:
        candidates.append(os.environ["ANDROID_PRIVATE"])
    if "ANDROID_APP_PATH" in os.environ:
        candidates.append(os.environ["ANDROID_APP_PATH"])
    candidates.append(os.path.expanduser("~"))
    for base in candidates:
        try:
            if base and os.path.isdir(base):
                return os.path.join(base, "crash.log")
        except Exception:
            continue
    return "crash.log"


def main():
    # 保证能导入项目包
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    from app.application import CubeApp

    # Kivy 的正常错误也应写入日志
    try:
        from kivy.logger import Logger
        Logger.info("cubesolver: starting app")
    except Exception:
        pass

    try:
        CubeApp().run()
    except Exception:
        try:
            path = _crash_log_path()
            with open(path, "w", encoding="utf-8") as f:
                f.write("=== cubesolver crash ===\n")
                traceback.print_exc(file=f)
            sys.stderr.write("crashed; log at %s\n" % path)
        except Exception:
            traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
