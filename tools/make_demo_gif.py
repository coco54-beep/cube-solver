"""生成一段 3D 回放动画演示 GIF（供 README 使用）。

用法：
    python tools/make_demo_gif.py

流程：启动 Kivy 应用 -> 随机打乱一个 4x4 -> 调用 solver4 求解 ->
进入回放页，逐步重放求解过程并逐帧截图 -> 合成为 GIF 输出到 assets/demo.gif。
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
from cube.cube4 import Cube4
from solver.solver4 import solve_4x4
from solver.result import SolveResult

OUT = os.path.join(BASE, "assets", "demo.gif")
W, H = 300, 500
FRAMES_TMP = os.path.join(BASE, "assets", "_gif_frames")
FRAME_COUNT = 14


def scramble(cube, length=18):
    faces = ["U", "D", "F", "B", "R", "L", "u", "d", "f", "b", "r", "l"]
    suff = ["", "'", "2"]
    mv = [random.choice(faces) + random.choice(suff) for _ in range(length)]
    cube.apply_moves(mv)
    return mv


def sample_indices(total_moves, count):
    """返回要截取的求解进度下标（含起点 -1 与终点）。"""
    if total_moves <= 0:
        return [-1]
    idxs = []
    for i in range(count):
        idxs.append(int(round((total_moves - 1) * i / (count - 1))))
    # 去重并保证顺序、包含末尾
    seen = []
    for i in idxs + [total_moves - 1]:
        if i not in seen:
            seen.append(i)
    return [-1] + seen


def run(app):
    Window.size = (W, H)
    try:
        app.root.transition.duration = 0
    except Exception:
        pass

    # 准备真实的 4x4 求解
    cube = Cube4.solved()
    mv = scramble(cube, 18)
    res = solve_4x4(cube)
    if not res.success:
        print("solve failed:", res.message)
        app.stop()
        return
    app.new_cube(4)
    app.n = 4
    app.cube = cube
    app.solve_result = res
    app.facelets_input = None

    app.root.current = "PlaybackScreen"

    idxs = sample_indices(len(res.moves), FRAME_COUNT)
    os.makedirs(FRAMES_TMP, exist_ok=True)

    state = {"i": 0, "pump": 0}

    def capture_frame(name):
        scr = app.root.current_screen
        p = os.path.join(FRAMES_TMP, name)
        scr.export_to_png(p)
        return p

    def tick(_dt):
        if state["i"] >= len(idxs):
            _assemble()
            app.stop()
            return
        if state["pump"] == 0:
            # 重放到该进度，然后等若干帧渲染
            idx = idxs[state["i"]]
            scr = app.root.get_screen("PlaybackScreen")
            scr._replay_to(idx)
            state["pump"] = 1
            Clock.schedule_once(tick, 0.15)
            return
        state["pump"] += 1
        if state["pump"] < 6:
            Clock.schedule_once(tick, 0.2)
            return
        capture_frame("f%02d.png" % state["i"])
        print("frame", state["i"], "idx", idxs[state["i"]])
        state["i"] += 1
        state["pump"] = 0
        Clock.schedule_once(tick, 0.15)

    Clock.schedule_once(tick, 0.1)


def _assemble():
    from PIL import Image
    files = sorted(f for f in os.listdir(FRAMES_TMP) if f.endswith(".png"))
    imgs = [Image.open(os.path.join(FRAMES_TMP, f)).convert("RGBA")
            for f in files]
    if not imgs:
        print("no frames")
        return
    # 统一尺寸（有的帧可能因渲染时序略不同，缩放到首帧尺寸）
    w, h = imgs[0].size
    imgs = [im.resize((w, h)).convert("RGB") for im in imgs]
    # 每帧停留 0.4s
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=400,
                 loop=0)
    print("GIF saved:", OUT, "frames:", len(imgs), "size:", (w, h))


def main():
    app = CubeApp()
    app.on_start = lambda: run(app) or None
    try:
        app.run()
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
