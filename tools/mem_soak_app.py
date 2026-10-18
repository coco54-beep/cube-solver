"""Continuous-use memory soak through the real desktop UI: switch puzzles and render."""
import gc
import sys
from pathlib import Path

import psutil

ROOT = Path(r"D:\coco\cube-solver")
sys.path.insert(0, str(ROOT))

from kivy.config import Config
Config.set("graphics", "width", "960")
Config.set("graphics", "height", "720")
Config.set("graphics", "resizable", "0")

from app.desktop_runtime import configure_graphics
configure_graphics()

from kivy.clock import Clock

PROC = psutil.Process()
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def rss():
    return PROC.memory_info().rss / (1024 * 1024)


def cache_entries():
    total = 0
    per = []
    for name, module in list(sys.modules.items()):
        if not module:
            continue
        for attr in list(vars(module)):
            try:
                value = getattr(module, attr)
                info = getattr(value, "cache_info", None)
            except Exception:
                continue
            if callable(info):
                try:
                    size = info().currsize
                except Exception:
                    continue
                if size:
                    total += size
                    per.append((size, f"{name}.{attr}"))
    per.sort(reverse=True)
    return total, per[:8]


def build_steps(app):
    sm = app.root

    def poly(kind, n):
        def run():
            app.new_polyhedral(kind, n)
            sm.current = "PolyhedralScreen"
            sm.get_screen("PolyhedralScreen").on_pre_enter()
        return run

    def cube(n):
        def run():
            app.new_cube(n)
            sm.current = "InputScreen"
            sm.get_screen("InputScreen").on_pre_enter()
        return run

    def mastermorphix():
        app.new_mastermorphix(3)
        sm.current = "MastermorphixScreen"
        sm.get_screen("MastermorphixScreen").on_pre_enter()

    def mirror():
        app.new_mirror(3)
        sm.current = "MirrorScreen"
        sm.get_screen("MirrorScreen").on_pre_enter()

    def square1():
        app.new_square1()
        sm.current = "Square1Screen"
        sm.get_screen("Square1Screen").on_pre_enter()

    return [
        ("megaminx13", poly("megaminx", 13)),
        ("football5", poly("football", 5)),
        ("icosahedron5", poly("icosahedron", 5)),
        ("megaminx3", poly("megaminx", 3)),
        ("megaminx5", poly("megaminx", 5)),
        ("football3", poly("football", 3)),
        ("icosahedron3", poly("icosahedron", 3)),
        ("moyu5", poly("moyu", 5)),
        ("pyraminx3", poly("pyraminx", 3)),
        ("skewb3", poly("skewb", 3)),
        ("cube3", cube(3)),
        ("cube4", cube(4)),
        ("mastermorphix", mastermorphix),
        ("mirror", mirror),
        ("square1", square1),
    ]


def main():
    from app.application import CubeApp
    app = CubeApp()
    state = {"round": 1, "index": 0, "steps": None, "baseline": None}

    def advance(_dt=0):
        if state["steps"] is None:
            state["steps"] = build_steps(app)
            gc.collect()
            state["baseline"] = rss()
            print(f"baseline {state['baseline']:.1f} MB", flush=True)
        if state["index"] >= len(state["steps"]):
            gc.collect()
            total, top = cache_entries()
            print(f"ROUND {state['round']} end: rss={rss():.1f} MB "
                  f"(+{rss()-state['baseline']:.1f}) lru={total} top={top}", flush=True)
            state["round"] += 1
            state["index"] = 0
            if state["round"] > ROUNDS:
                app.stop()
                return
        name, step = state["steps"][state["index"]]
        state["index"] += 1
        try:
            step()
        except Exception as exc:
            print(f"ERR {name}: {exc!r}", flush=True)
        Clock.schedule_once(advance, 0.5)

    def on_start():
        Clock.schedule_once(advance, 1.0)

    app.on_start = on_start
    app.run()
    print("DONE")


if __name__ == "__main__":
    main()
