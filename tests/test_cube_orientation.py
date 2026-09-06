"""测试整体旋转导航模块（cube_orientation）。"""

from cube.coordinates import FACE_NORMALS
from renderer.cube_orientation import CubeOrientation, SEQ


def test_seq_covers_all_faces():
    assert len(SEQ) == 6
    assert set(SEQ) == set("UDFBRL")


def test_current_face_always_faces_camera():
    for n in (2, 3, 4, 5):
        for start in range(6):
            ori = CubeOrientation(n)
            for _ in range(start):
                ori.turn_next()
            for _ in range(6):
                assert ori.face_for_world() == ori.current_face()
                assert ori.current_face() == SEQ[ori.index]
                ori.turn_next()


def test_turn_prev_round_trip():
    ori = CubeOrientation(4)
    seq = []
    for _ in range(6):
        seq.append(ori.current_face())
        ori.turn_next()
    assert len(set(seq)) == 6
    for _ in range(6):
        ori.turn_prev()
    assert ori.current_face() == SEQ[0]
    assert ori.face_for_world() == SEQ[0]


def test_world_rotation_is_90deg_coordinate():
    """每次整体旋转应为绕坐标轴的 90° 整数旋转（world 为整数矩阵）。"""
    ori = CubeOrientation(3)
    for _ in range(6):
        angle, axis = ori.next_axis_deg()
        assert abs(angle - 90.0) < 1e-6
        # 轴应确为一根坐标轴
        ones = sum(1 for v in axis if abs(v) > 1e-6)
        assert ones == 1
        ori.turn_next()


def test_screen_dir_is_cardinal():
    """屏幕方位始终为一根明确的方向（left/right/up/down）。"""
    for n in (2, 3, 4, 5):
        ori = CubeOrientation(n)
        for _ in range(6):
            d = ori.next_dir()
            assert d in ("left", "right", "up", "down")
            p = ori.prev_dir()
            assert p in ("left", "right", "up", "down")
            ori.turn_next()


def test_next_prev_arrows_perpendicular():
    """下一步与上一步朝向两个垂直的侧面（一个左右、一个上下）。"""
    for n in (2, 3, 4, 5):
        for start in range(6):
            ori = CubeOrientation(n)
            for _ in range(start):
                ori.turn_next()
            nxt = ori.next_dir()
            prv = ori.prev_dir()
            is_lr = ("left", "right")
            assert (nxt in is_lr) != (prv in is_lr), (nxt, prv)
