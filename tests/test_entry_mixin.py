"""EntryActionsMixin：各族输入页的 assign_initial / open_twist 钩子。

需要 Kivy 图形上下文；无窗口环境（CI）自动跳过。
"""

import pytest

pytest.importorskip("kivy")

CASES = [
    ("InputScreen", "cube3", "TwistScreen"),
    ("MastermorphixScreen", "mastermorphix", "MorphixTwistScreen"),
    ("MirrorScreen", "mirror", "MorphixTwistScreen"),
    ("ShapeCubeScreen", "shape_axis", "MorphixTwistScreen"),
    ("PolyhedralScreen", "polyhedral_fto", "PolyhedralTwistScreen"),
    ("MirrorTowerScreen", "mirror_tower", "PolyhedralTwistScreen"),
    ("Square1Screen", "square1", None),
]


def _setup(app, kind):
    if kind == "cube3":
        app.new_cube(3)
    elif kind == "mastermorphix":
        app.new_mastermorphix(3)
    elif kind == "mirror":
        app.new_mirror(3)
    elif kind == "shape_axis":
        app.new_shape_cube("axis")
    elif kind == "polyhedral_fto":
        app.new_polyhedral("fto", 3)
    elif kind == "mirror_tower":
        app.new_mirror_tower()
    elif kind == "square1":
        app.new_square1()


def test_entry_actions_mixin():
    try:
        from app.application import CubeApp
        app = CubeApp()
        app.root = app.build()
    except Exception as exc:  # 无显示/GL 时跳过
        pytest.skip("no Kivy window: %s" % exc)

    sm = app.root
    for name, kind, twist in CASES:
        _setup(app, kind)
        screen = sm.get_screen(name)
        screen.on_pre_enter()
        assert screen.entry_twist_screen == twist, name

        screen.assign_initial()                       # 不抛异常
        assert app.cube is not None, name
        if hasattr(app.cube, "is_solved"):
            assert app.cube.is_solved(), name

        if twist is not None:
            screen.open_twist()                       # 不抛异常
