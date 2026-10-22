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
from cube.cube3 import Cube3  # noqa: E402
from cube.cube2 import Cube2
from cube.cube4 import Cube4
from cube.appearance import with_appearance
from cube.bandaged_cube import BandagedCube  # noqa: E402
from cube.circle_cube import Circle2Cube
from cube.cuboid import CuboidCube
from renderer.cuboid_view import CuboidView
from cube.mastermorphix import MastermorphixCube  # noqa: E402
from cube.mirror import MirrorCube  # noqa: E402
from cube.shape_cube import AxisCube, PandoraCube, WindmillCube, FisherCube  # noqa: E402
from cube.mirror_shape import MirrorAxisCube, MirrorFisherCube, MirrorWindmillCube  # noqa: E402
from cube.mirror_shape import (MirrorUnequalWindmillCube, MirrorUnequalFisherCube,
                               MirrorOffsetWindmillCube, MirrorOffsetFisherCube)  # noqa: E402
from cube.square1 import Square1Cube  # noqa: E402
from cube.square_family import SquareFamilyCube  # noqa: E402
from cube.mirror_tower import MirrorTowerCube  # noqa: E402
from cube.mirror_pyraminx import MirrorPyraminxCube  # noqa: E402
from cube.mirror_skewb import MirrorSkewbCube  # noqa: E402
from cube.fisher_skewb import FisherSkewbCube
from renderer.fisher_skewb_view import FisherSkewbView
from cube.ghost_pyramid import GhostPyramidCube
from renderer.ghost_pyramid_view import GhostPyramidView
from cube.ghost import GhostCube  # noqa: E402
from renderer.polyhedral_view import PolyhedralView, default_palette  # noqa: E402
from renderer.cube_view import CubeView  # noqa: E402
from renderer.mastermorphix_view import MastermorphixView  # noqa: E402
from renderer.mirror_view import MirrorView  # noqa: E402
from renderer.shape_cube_view import AxisView, PandoraView, WindmillView, FisherView  # noqa: E402
from renderer.mirror_shape_view import (MirrorAxisView, MirrorFisherView,  # noqa: E402
                                        MirrorWindmillView, MirrorUnequalWindmillView,
                                        MirrorUnequalFisherView, MirrorOffsetWindmillView, MirrorOffsetFisherView)
from renderer.square1_view import Square1View  # noqa: E402
from renderer.square_family_view import SquareFamilyView  # noqa: E402
from renderer.mirror_tower_view import MirrorTowerView  # noqa: E402
from renderer.mirror_pyraminx_view import MirrorPyraminxView  # noqa: E402
from renderer.mirror_skewb_view import MirrorSkewbView  # noqa: E402
from renderer.ghost_view import GhostView  # noqa: E402

P = PolyhedralPuzzle
JOBS = [
    ('cuboid_family', CuboidView, lambda: CuboidCube.solved('cuboid_224')),
    ('circle_family', PolyhedralView, lambda: P('crazy_earth',3)),
    ('cube', CubeView, lambda: Cube3.solved()),
    ('fused_cube', CubeView, lambda: BandagedCube.solved('fused_cube')),
    ('two_bar_cube', CubeView, lambda: BandagedCube.solved('two_bar_cube')),
    ('bandaged_c', CubeView, lambda: BandagedCube.solved('bandaged_c')),
    ('bicube', CubeView, lambda: BandagedCube.solved('bicube')),
    ('ai_cube', CubeView, lambda: BandagedCube.solved('ai_cube')),
    ('burr_cube', CubeView, lambda: BandagedCube.solved('burr_cube')),
    ('camouflage_3', CuboidView, lambda: CuboidCube.solved('camouflage_3')),
    ('penrose_2', CubeView, lambda: with_appearance(Cube2.solved(), 'penrose_2')),
    ('penrose_3', CubeView, lambda: with_appearance(Cube3.solved(), 'penrose_3')),
    ('penrose_4', CubeView, lambda: with_appearance(Cube4.solved(), 'penrose_4')),
    ('circle_2', PolyhedralView, lambda: Circle2Cube()),
    ('axis_4',AxisView,lambda:AxisCube.solved(n=4)),
    ('windmill_4',WindmillView,lambda:WindmillCube.solved(n=4)),
    ('fisher_4',FisherView,lambda:FisherCube.solved(n=4)),
    ('sq_family',SquareFamilyView,lambda:SquareFamilyCube('super_square1')),
    ('square0',SquareFamilyView,lambda:SquareFamilyCube('square0')),
    ('square2',SquareFamilyView,lambda:SquareFamilyCube('square2')),
    ('super_square1',SquareFamilyView,lambda:SquareFamilyCube('super_square1')),
    ("ghost", GhostView, lambda: GhostCube.solved(n=3)),
    ("ghost_1", GhostView, lambda: GhostCube.solved(n=1)),
    ("ghost_2", GhostView, lambda: GhostCube.solved(n=2)),
    ("ghost_4", GhostView, lambda: GhostCube.solved(n=4)),
    ("mirror_skewb", MirrorSkewbView, lambda: MirrorSkewbCube.solved()),
    ("mirror_pyraminx", MirrorPyraminxView, lambda: MirrorPyraminxCube.solved(n=3)),
    ("mirror_pyraminx_4", MirrorPyraminxView, lambda: MirrorPyraminxCube.solved(n=4)),
    ("pyraminx", PolyhedralView, lambda: P("pyraminx", 3)),
    ("mastermorphix", MastermorphixView, lambda: MastermorphixCube.solved(n=3)),
    ("skewb", PolyhedralView, lambda: P("skewb", 3)),
    ("dino", PolyhedralView, lambda: P("dino", 2)),
    ("dino4", PolyhedralView, lambda: P("dino4", 2)),
    ("megaminx", PolyhedralView, lambda: P("megaminx", 3)),
    ("moyu", PolyhedralView, lambda: P("moyu", 3)),
    ("mirror", MirrorView, lambda: MirrorCube.solved(n=3)),
    ("fto", PolyhedralView, lambda: P("fto", 2)),
    ("fto_5", PolyhedralView, lambda: P("fto", 5)),
    ("football", PolyhedralView, lambda: P("football", 3)),
    ("icosahedron", PolyhedralView, lambda: P("icosahedron", 3)),
    ("war_drum", PolyhedralView, lambda: P("war_drum", 3)),
    ("pentahedron", PolyhedralView, lambda: P("pentahedron", 3)),
    ("eight_petals", PolyhedralView, lambda: P("eight_petals", 3)),
    ("clover", PolyhedralView, lambda: P("clover", 3)),
    ("blossom", PolyhedralView, lambda: P("blossom", 3)),
    ("edge_family", PolyhedralView, lambda: P("blossom", 3)),
    ("petal_tetrahedron", PolyhedralView, lambda: P("petal_tetrahedron", 3)),
    ("petal_tetrahedron_nocentre", PolyhedralView, lambda: P("petal_tetrahedron_nocentre", 3)),
    ("petal_icosahedron", PolyhedralView, lambda: P("petal_icosahedron", 3)),
    ("petal_icosahedron_nocentre", PolyhedralView, lambda: P("petal_icosahedron_nocentre", 3)),
    ("square1", Square1View, lambda: Square1Cube.solved()),
    ("void_cube", PolyhedralView, lambda: P("void_cube", 3)),
    ("void_tower", PolyhedralView, lambda: P("void_tower", 3)),
    ("void_minx", PolyhedralView, lambda: P("void_minx", 3)),
    ("mirror_tower", MirrorTowerView, lambda: MirrorTowerCube.solved()),
    ("axis", AxisView, lambda: AxisCube.solved(n=3)),
    ("pandora", PandoraView, lambda: PandoraCube.solved(n=3)),
    ("windmill", WindmillView, lambda: WindmillCube.solved(n=3)),
    ("fisher", FisherView, lambda: FisherCube.solved(n=3)),
    ("mirror_windmill", MirrorWindmillView, lambda: MirrorWindmillCube.solved()),
    ("mirror_axis", MirrorAxisView, lambda: MirrorAxisCube.solved()),
    ("mirror_fisher", MirrorFisherView, lambda: MirrorFisherCube.solved()),
    ("mirror_windmill_unequal", MirrorUnequalWindmillView, lambda: MirrorUnequalWindmillCube.solved()),
    ("mirror_fisher_unequal", MirrorUnequalFisherView, lambda: MirrorUnequalFisherCube.solved()),
    ("mirror_windmill_offset", MirrorOffsetWindmillView, lambda: MirrorOffsetWindmillCube.solved()),
    ("mirror_fisher_offset", MirrorOffsetFisherView, lambda: MirrorOffsetFisherCube.solved()),
    ("ivy", PolyhedralView, lambda: P("ivy", 3)),
    ("pyraminx_duo", PolyhedralView, lambda: P("pyraminx_duo", 3)),
    ("coin_tetrahedron", PolyhedralView, lambda: P("coin_tetrahedron", 3)),
    ("skewb_ultimate", PolyhedralView, lambda: P("skewb_ultimate", 3)),
    ("super_ivy", PolyhedralView, lambda: P("super_ivy", 3)),
    ("helicopter", PolyhedralView, lambda: P("helicopter", 3)),
    ("mosaic", PolyhedralView, lambda: P("mosaic", 4)),
    ("tins", PolyhedralView, lambda: P("tins", 5)),
    ("dino_skewb", PolyhedralView, lambda: P("dino_skewb", 4)),
    ("dayan_dino_skewb", PolyhedralView, lambda: P("dayan_dino_skewb", 4)),
    ("fisher_skewb", FisherSkewbView, lambda: FisherSkewbCube.solved()),
    ("ghost_pyramid", GhostPyramidView, lambda: GhostPyramidCube.solved()),
]
from cube.cuboid import MODELS as CUBOID_MODELS
JOBS.extend((kind,CuboidView,lambda k=kind:CuboidCube.solved(k))
            for kind in CUBOID_MODELS if kind.startswith('cuboid_'))
ONLY=set(sys.argv[1:])
from cube.articulated import ArticulatedCube,KINDS as ARTICULATED_KINDS
from renderer.articulated_view import ArticulatedView
from cube.pentacle import PentacleCube
from renderer.pentacle_view import PentacleView
JOBS.append(('pentacle',PentacleView,PentacleCube))
JOBS.extend((kind,ArticulatedView,lambda k=kind:ArticulatedCube(k)) for kind in ARTICULATED_KINDS)
JOBS.extend((("o2",PolyhedralView,lambda:P('o2',1)),
             ("ancient_coin",PolyhedralView,lambda:P('ancient_coin',3))))

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
        self._q = [job for job in JOBS if not ONLY or job[0] in ONLY]
        Clock.schedule_once(self._next, 0.6)
        return self.root

    def _next(self, _dt):
        if not self._q:
            self.stop()
            return
        name, viewcls, factory = self._q.pop(0)
        try:
            cube = factory()
            view = viewcls(size_hint=(None, None), size=(SIZE*2, SIZE*2), pos=(0, 0))
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
            if name in ('mirror_fisher_unequal','mirror_fisher_offset'):
                view.camera.azimuth = 22.5
            if name in ('penrose_2','penrose_3','penrose_4'):
                view.camera.azimuth = -145
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
                    "eight_petals", "clover", "ivy", "super_ivy") else 1.0
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
