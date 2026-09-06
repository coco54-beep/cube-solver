"""物理语义回归测试：只有外层(1X)与两层宽转(2X)及由它们合成的合法切片
(如 2R R' / 2L L' / 2U U') 才不会移动 6 个固定面心。

3X/4X/5X 会移动固定面心，属非物理状态，禁止用于正式求解。
本测试为「前缘风险」硬测试：在通过前，任何依赖 3X 提升配对的结果都只能算实验线索。
"""

from cube.cube5 import Cube5


def fixed_center_positions(cube):
    return {
        c.home: tuple(c.pos)
        for c in cube.cubies.values()
        if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]
    }


def moved_fixed_centers(before_cube, after_cube):
    before = fixed_center_positions(before_cube)
    after = fixed_center_positions(after_cube)
    return [h for h in before if before[h] != after.get(h)]


# 合法：不得移动任何固定面心
LEGAL_CENTER_SAFE = [
    "R", "L", "U", "D", "F", "B",
    "R'", "L'", "U'", "D'", "F'", "B'",
    "2R", "2L", "2U", "2D", "2F", "2B",
    "2R'", "2L'", "2U'", "2D'", "2F'", "2B'",
]

# 由合法动作合成的「内侧切片原语」，同样不得移动固定面心
LEGAL_SLICE_PRIMITIVES = [
    ["2R", "R'"], ["2R'", "R"], ["R", "2R'"],
    ["2L", "L'"], ["2L'", "L"], ["2U", "U'"],
    ["2D", "D'"], ["2F", "F'"], ["2B", "B'"],
]

# 非法：会移动固定面心，禁止用于求解
ILLEGAL_CENTER_SHIFTING = [
    "3R", "3L", "3U", "3D", "3F", "3B",
    "3R'", "3L'", "3U'", "3D'", "3F'", "3B'",
    "4R", "4L", "4U", "4D", "4F", "4B",
    "5R", "5L", "5U", "5D", "5F", "5B",
]


class TestLegacyMoves:
    def test_outer_and_wide_keep_fixed_centers(self):
        for mv in LEGAL_CENTER_SAFE:
            c = Cube5.solved()
            before = c.clone()
            c.apply_move(mv)
            assert moved_fixed_centers(before, c) == [], f"{mv} 移动了固定面心"

    def test_legal_slice_primitives_keep_fixed_centers(self):
        for seq in LEGAL_SLICE_PRIMITIVES:
            c = Cube5.solved()
            before = c.clone()
            c.apply_moves(seq)
            assert moved_fixed_centers(before, c) == [], f"{seq} 移动了固定面心"


class TestNonPhysicalMoves:
    def test_deep_moves_shift_fixed_centers(self):
        # 这只是记录现状：深层动作确实会移动固定面心，因此禁止用于求解
        for mv in ILLEGAL_CENTER_SHIFTING:
            c = Cube5.solved()
            before = c.clone()
            c.apply_move(mv)
            assert moved_fixed_centers(before, c) != [], f"{mv} 应移动固定面心(非物理)"

    def test_3R_cannot_be_used_alone(self):
        # 明确断言：3R 单独使用是非物理的
        c = Cube5.solved()
        before = c.clone()
        c.apply_move("3R")
        assert moved_fixed_centers(before, c) != []
