"""Render a small 3D thumbnail for every irregular puzzle card.

Runs a hidden Kivy window and exports each puzzle view to
``assets/puzzles/<key>.png`` so the directory can show a picture instead of a
two-letter abbreviation.

Usage:  python tools/export_puzzle_thumbs.py
"""
import os
import sys

os.environ.setdefault("KIVY_NO_ARGS", "1")
from kivy.config import Config  # noqa: E402
Config.set("graphics", "window", "hidden")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402

from cube.polyhedral import PolyhedralPuzzle  # noqa: E402
from cube.mastermorphix import MastermorphixCube  # noqa: E402
from cube.mirror import MirrorCube  # noqa: E402
from cube.shape_cube import AxisCube, PandoraCube, WindmillCube, FisherCube  # noqa: E402
from cube.square1 import Square1Cube  # noqa: E402
from cube.mirror_tower import MirrorTowerCube  # noqa: E402
from renderer.polyhedral_view import PolyhedralView, default_palette  # noqa: E402
from renderer.mastermorphix_view import MastermorphixView  # noqa: E402
from renderer.mirror_view import MirrorView  # noqa: E402
from renderer.shape_cube_view import AxisView, PandoraView, WindmillView, FisherView  # noqa: E402
from renderer.square1_view import Square1View  # noqa: E402
from renderer.mirror_tower_view import MirrorTowerView  # noqa: E402

P = PolyhedralPuzzle
JOBS = [
    ("pyraminx", PolyhedralView, lambda: P("pyraminx", 3)),
    ("mastermorphix", MastermorphixView, lambda: MastermorphixCube.solved(n=3)),
    ("skewb", PolyhedralView, lambda: P("skewb", 3)),
    ("dino", PolyhedralView, lambda: P("dino", 2)),
    ("megaminx", PolyhedralView, lambda: P("megaminx", 3)),
    ("moyu", PolyhedralView, lambda: P("moyu", 3)),
    ("mirror", MirrorView, lambda: MirrorCube.solved(n=3)),
    ("fto", PolyhedralView, lambda: P("fto", 2)),
    ("football", PolyhedralView, lambda: P("football", 3)),
    ("icosahedron", PolyhedralView, lambda: P("icosahedron", 3)),
    ("war_drum", PolyhedralView, lambda: P("war_drum", 3)),
    ("pentahedron", PolyhedralView, lambda: P("pentahedron", 3)),
    ("eight_petals", PolyhedralView, lambda: P("eight_petals", 3)),
    ("clover", PolyhedralView, lambda: P("clover", 3)),
    ("blossom", PolyhedralView, lambda: P("blossom", 3)),
    ("square1", Square1View, lambda: Square1Cube.solved()),
    ("void_cube", PolyhedralView, lambda: P("void_cube", 3)),
    ("void_tower", PolyhedralView, lambda: P("void_tower", 3)),
    ("mirror_tower", MirrorTowerView, lambda: MirrorTowerCube.solved()),
    ("axis", AxisView, lambda: AxisCube.solved(n=3)),
    ("pandora", PandoraView, lambda: PandoraCube.solved(n=3)),
    ("windmill", WindmillView, lambda: WindmillCube.solved(n=3)),
    ("fisher", FisherView, lambda: FisherCube.solved(n=3)),
    ("ivy", PolyhedralView, lambda: P("ivy", 3)),
]

OUT = os.path.join(BASE, "assets", "puzzles")
os.makedirs(OUT, exist_ok=True)
SIZE = 260
#: Every thumbnail is normalised so its visible content spans this many pixels,
#: which puts all puzzles (cube-shaped and not) on one common scale.
FILL = 224


def _normalize(path):
    """Crop to the visible content and re-centre it at a common scale."""
    try:
        from PIL import Image
        import numpy as np
    except Exception:
        return
    im = Image.open(path).convert("RGBA")
    alpha = np.array(im)[..., 3]
    ys, xs = np.where(alpha > 8)
    if len(xs) == 0:
        return
    crop = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    w, h = crop.size
    scale = FILL / max(w, h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    crop = crop.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(crop, ((SIZE - nw) // 2, (SIZE - nh) // 2), crop)
    out.save(path)


class ThumbApp(App):
    def build(self):
        self.root = FloatLayout()
        self._q = list(JOBS)
        Clock.schedule_once(self._next, 0.6)
        return self.root

    def _next(self, _dt):
        if not self._q:
            self.stop()
            return
        name, viewcls, factory = self._q.pop(0)
        try:
            cube = factory()
            view = viewcls(size_hint=(None, None), size=(SIZE, SIZE), pos=(0, 0))
            if hasattr(view, "palette"):
                try:
                    view.palette = default_palette(cube)
                except Exception:
                    pass
            view.set_cube(cube)
            # CubeView-based views (mastermorphix/mirror/shape): use the
            # standard 3/4 camera and a little zoom-out so nothing is clipped.
            if hasattr(view, "reset_camera"):
                view.reset_camera()
            if hasattr(view, "_display_zoom"):
                view._display_zoom = 0.75
                if hasattr(view, "_redraw"):
                    view._redraw()
            # Strip the input-screen face-number labels; thumbnails want the
            # bare puzzle only.
            for lab in list(getattr(view, "_face_labels", [])):
                try:
                    view.remove_widget(lab)
                except Exception:
                    pass
            if hasattr(view, "_face_labels"):
                view._face_labels = []
                if hasattr(view, "refresh"):
                    view.refresh()
            if hasattr(view, "fit_margin"):
                kind = getattr(cube, "puzzle_kind", "")
                view.fit_margin = 1.3 if kind in (
                    "war_drum", "pentahedron", "moyu", "blossom",
                    "eight_petals", "clover", "ivy") else 1.0
                if hasattr(view, "refresh"):
                    view.refresh()
            self.root.add_widget(view)
            Clock.schedule_once(lambda d, v=view, n=name: self._export(v, n), 0.5)
        except Exception as exc:
            print("setup failed", name, repr(exc), flush=True)
            Clock.schedule_once(self._next, 0.05)

    def _export(self, view, name):
        try:
            path = os.path.join(OUT, name + ".png")
            view.export_to_png(path)
            _normalize(path)
            print("saved", name, flush=True)
        except Exception as exc:
            print("export failed", name, repr(exc), flush=True)
        self.root.remove_widget(view)
        Clock.schedule_once(self._next, 0.15)


if __name__ == "__main__":
    ThumbApp().run()
