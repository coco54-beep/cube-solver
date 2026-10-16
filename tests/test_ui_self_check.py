"""UI 冒烟自检：构建并进入每个屏幕，确保不抛异常。

需要 Kivy 图形上下文；无窗口环境（CI）自动跳过。
"""

import pytest

pytest.importorskip("kivy")


def test_all_screens_enter_without_error(tmp_path):
    try:
        from app.application import CubeApp
        app = CubeApp()
        app.root = app.build()
    except Exception as exc:  # 无显示/GL 时跳过
        pytest.skip("no Kivy window: %s" % exc)

    from app.ui_self_check import run_blocking
    data = run_blocking(app, str(tmp_path))

    failures = [r for r in data["results"] if r["status"] != "ok"]
    assert not failures, "\n".join("%s: %s" % (r["screen"], r.get("traceback"))
                                   for r in failures)
    assert data["errors"] == 0
