"""导出各界面截图到 assets/screenshots/（供 README 使用）。

用法：
    python tools/screenshots_export.py

流程：启动 Kivy 应用，依次切换到各页面并导出 PNG。
运行会创建真实窗口（OpenGL），结束后自动 stop。
"""

import os
import sys
import traceback
import random

os.environ.setdefault("KIVY_NO_ARGS", "1")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from kivy.clock import Clock
from kivy.core.window import Window

from app.application import CubeApp
from solver.result import SolveResult

OUT = os.path.join(BASE, "assets", "screenshots")

# 手机竖屏尺寸（README 中按 width=190 一行展示）
W, H = 420, 740


def _export(app, name):
    path = os.path.join(OUT, name)
    try:
        # 用屏幕 widget 的 export_to_png 导出完整界面（GL 场景也正确渲染）。
        app.root.current_screen.export_to_png(path)
        print("saved:", path)
    except Exception:
        traceback.print_exc()
        print("FAILED:", name)


def scramble(cube, n, length=20):
    if n == 4:
        faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l"]
    elif n == 5:
        faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l",
                 "2U", "2D", "2F", "2B", "2R", "2L"]
    else:
        faces = ["U", "D", "F", "B", "R", "L"]
    suff = ["", "'", "2"]
    moves = [random.choice(faces) + random.choice(suff) for _ in range(length)]
    cube.apply_moves(moves)
    return moves


def inverse_moves(moves):
    out = []
    for m in reversed(moves):
        if m.endswith("'"):
            out.append(m[:-1])
        elif m.endswith("2"):
            out.append(m)
        else:
            out.append(m + "'")
    return out


def build_jobs(app):
    """返回一个可顺序执行的 job 列表：每个 job 为 (setup_fn, 截图名)。"""
    jobs = []

    # ---- 首页（竖屏 2×2 卡片）----
    def _job_home():
        app.root.current = "HomeScreen"

    jobs.append((_job_home, "home.png"))

    # ---- 各阶录入页（随机打乱后截图）----
    for n in (2, 3, 4, 5):
        def _make(n):
            def _job():
                app.new_cube(n)
                app.root.current = "InputScreen"
                scr = app.root.get_screen("InputScreen")
                scr.set_facelets({})
                scr.random_load()
            return _job
        jobs.append((_make(n), f"input_{n}x{n}.png"))

    # ---- 回放页（设置一个打乱 + 逆打乱作为求解 moves）----
    def _job_playback_setup():
        app.new_cube(4)
        mv = scramble(app.cube, 4, 18)
        app.solve_result = SolveResult(True, inverse_moves(mv), "ok", 0, len(mv),
                                       [])
        app.root.current = "PlaybackScreen"

    jobs.append((_job_playback_setup, "playback.png"))

    # ---- 回放进行中（应用若干步）----
    def _job_playback_step():
        scr = app.root.get_screen("PlaybackScreen")
        if not hasattr(scr, "view"):
            scr.build_ui()
        # 手动推进到部分步骤
        target = min(6, len(scr._moves) - 1)
        scr._stop_all()
        scr._work = app.cube.clone()
        scr.view.set_cube(scr._work)
        scr._idx = -1
        while scr._idx < target:
            scr._idx += 1
            scr._work.apply_moves([scr._moves[scr._idx]])
        scr.view.set_cube(scr._work)
        scr._update_buttons()

    jobs.append((_job_playback_step, "playback_stepping.png"))

    # ---- 演示目录（三阶）----
    def _job_demo_menu():
        app.root.get_screen("DemoMenuScreen").set_mode(3)
        app.root.current = "DemoMenuScreen"

    jobs.append((_job_demo_menu, "demo_menu.png"))

    # ---- 演示屏（三阶第一个案例）----
    def _job_demo_screen():
        app.root.get_screen("DemoMenuScreen").set_mode(3)
        scr = app.root.get_screen("DemoScreen")
        scr.enter_case(3, 0, 0)
        app.root.current = "DemoScreen"

    jobs.append((_job_demo_screen, "demo_screen.png"))

    return jobs


def run(app):
    jobs = build_jobs(app)
    Window.size = (W, H)

    # 禁用屏幕切换动画，让目标屏幕立即成为 current 并被正确尺寸布局。
    try:
        app.root.transition.duration = 0
    except Exception:
        pass

    state = {"i": 0, "waiting": False, "pump": 0}

    def tick(_dt):
        while state["i"] < len(jobs):
            setup, name = jobs[state["i"]]
            if not state["waiting"]:
                # 切屏幕 + 设置状态，然后等若干帧让 GL 场景完成渲染。
                setup()
                state["waiting"] = True
                state["pump"] = 0
                Clock.schedule_once(tick, 0.15)
                return
            state["pump"] += 1
            if state["pump"] < 8:
                # 多跑几帧，确保 CubeView 的 GL 内容已绘制进屏幕。
                Clock.schedule_once(tick, 0.2)
                return
            _export(app, name)
            state["i"] += 1
            state["waiting"] = False
            if state["i"] >= len(jobs):
                print("ALL DONE")
                app.stop()
                return
            Clock.schedule_once(tick, 0.2)

    Clock.schedule_once(tick, 0.1)


def main():
    app = CubeApp()
    app.on_start = lambda: run(app) or None
    try:
        app.run()
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
