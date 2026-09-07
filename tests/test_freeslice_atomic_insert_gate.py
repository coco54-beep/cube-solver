"""确定性 free-slice 第三阶段 Gate 3 回归测试：原子插翼（rel=2，朝向推迟到 rel=3）。

Gate 3 目标：在固定工作布局（work=UF, open=2F, 入口=UR 右翼）下，采用「纯外层联合
定位 setup + 2F outer 2F'」做一次原子插翼，把目标中棱与目标翼组合为 rel>=2（同槽且色对
一致）的位置组合。由用户裁定：朝向一致性推迟到 rel=3（完整 tredge）才强制，故 rel=2
阶段 orientation_consistent 允许为 False。

须满足：
- 只用物理合法动作（1X 外层 + 2X 宽层；绝不出现 3X/4X/5X）
- relation_after >= 2 且 > relation_before
- 中心归面、6 固定面心保持、真实重放一致
- 不改写输入 cube；确定性；失败返回规定 error_code
"""

import pytest

from cube.cube5 import Cube5
from solver.edge5.compact_state import _SLOT_MID, _SLOT_WINGS
from solver.edge5.atomic_insert import (
    insert_wing_atomic,
    middle_wing_relation_real,
    REL_SCATTERED,
    REL_SAME_SLOT,
    REL_COMBO,
    REL_ORIENTED,
    JOINT_SETUP_UNREACHABLE,
    PRECONDITION_FAILED,
    AtomicWingInsertResult,
)
from solver.edge5.freeslice_layout import build_layout, current_joint_setup
from solver.edge5.state import centers_are_color_solved
from solver.edge5.free_slice import _fixed_centers_preserved

LAYOUT = build_layout()
UF_MID = _SLOT_MID["UF"]
UF_WA = _SLOT_WINGS["UF"][0]
UF_WB = _SLOT_WINGS["UF"][1]
UR_WA = _SLOT_WINGS["UR"][0]


def _fixed_home_set(cube):
    return {p for p, c in cube.cubies.items()
            if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]}


def _fixed_preserved(cube):
    fixed = _fixed_home_set(cube)
    return all(cube.cubies[p].pos == p for p in fixed)


def _center_solved_random_cube(seed, depth=6):
    import random
    from solver.center5 import solve_centers5
    rnd = random.Random(seed)
    pool = ["R", "L", "U", "D", "F", "B", "R'", "L'", "U'", "D'", "F'", "B'",
            "R2", "L2", "U2", "D2", "F2", "B2", "2R", "2L", "2U", "2D", "2F", "2B",
            "2R'", "2L'", "2U'", "2D'", "2F'", "2B'"]
    c = Cube5.solved()
    c.apply_moves([rnd.choice(pool) for _ in range(depth)])
    if not centers_are_color_solved(c):
        cr = solve_centers5(c)
        c.apply_moves(cr.moves)
    return c


def _raw_cube(seed):
    return _center_solved_random_cube(seed)


def _reachable_work_entry_cube(seed):
    """若 (UF 中棱, UF 翼-a) 的组合可达，返回已把它们放到 (UF, UR) 的 cube，否则 None。"""
    c = _raw_cube(seed)
    setup = current_joint_setup(c, UF_MID, UF_WA, LAYOUT)
    if setup is None:
        return None
    w = c.clone()
    for m in setup:
        w.apply_move(m)
    return w


def _fingerprint(cube):
    return tuple((p, cubie.home, tuple(sorted(cubie.stickers.items())))
                 for p, cubie in sorted(cube.cubies.items()))


# ------------------------- 关系等级单元 -------------------------

def test_wing_relation_on_solved_uf_pair_is_oriented():
    c = Cube5.solved()
    r = middle_wing_relation_real(c, UF_MID, UF_WA)
    assert r.same_logical_slot and r.color_pair_matches and r.orientation_consistent
    assert r.relation_level == REL_ORIENTED
    assert r.is_combo


def test_wing_relation_different_slot_is_scattered():
    c = Cube5.solved()
    r = middle_wing_relation_real(c, UF_MID, UR_WA)
    assert not r.same_logical_slot
    assert r.relation_level == REL_SCATTERED
    assert not r.is_combo


# ------------------------- 原子插翼成功 -------------------------

@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21, 33, 44])
def test_atomic_insert_from_reachable_work_entry_succeeds(seed):
    c = _reachable_work_entry_cube(seed)
    if c is None:
        pytest.skip(f"seed {seed} 状态不可达")
    before = middle_wing_relation_real(c, UF_MID, UF_WA)
    r = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert r.success, f"未成功: {r.error_code} {r.message}"
    after = middle_wing_relation_real(c, UF_MID, UF_WA)
    # 前置：中棱在工作槽、翼在入口（不同槽）→ 关系应 < combo
    assert before.relation_level < REL_COMBO
    assert r.relation_before.relation_level == before.relation_level
    assert r.relation_after.relation_level >= REL_COMBO
    assert r.relation_after.relation_level > r.relation_before.relation_level


@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21, 33, 44])
def test_atomic_insert_meets_all_postconditions(seed):
    c = _reachable_work_entry_cube(seed)
    if c is None:
        pytest.skip(f"seed {seed} 状态不可达")
    r = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert r.success
    # 位置组合
    assert r.relation_after.same_logical_slot
    assert r.relation_after.color_pair_matches
    assert r.relation_after.relation_level >= REL_COMBO
    assert r.middle_preserved
    # 中心 / 固定面心
    assert r.centers_solved_after and centers_are_color_solved(c)
    assert r.fixed_centers_preserved and _fixed_preserved(c)
    # 真实重放
    assert r.replay_consistent
    assert r.error_code is None


def test_atomic_insert_moves_are_only_legal():
    c = Cube5.solved()  # 用已定位态确保可达
    setup = current_joint_setup(c, UF_MID, UF_WA, LAYOUT)
    assert setup is None or setup == ()  # solved 态中棱/翼同槽，可能不可达；只验证动作合法性
    # 构造一个确定可达态：手动把 UF 翼-a 移出（用外层）
    c2 = _raw_cube(9)
    setup = current_joint_setup(c2, UF_MID, UF_WA, LAYOUT)
    if setup is None:
        pytest.skip("seed 9 不可达")
    w = c2.clone()
    for m in setup:
        w.apply_move(m)
    r = insert_wing_atomic(w, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert r.success
    for m in r.moves:
        assert m[:1] in ("R", "L", "U", "D", "F", "B", "2"), f"非物理动作 {m}"
        assert m not in ("3R", "3L", "3U", "3D", "3F", "3B"), f"非法动作 {m}"
    assert r.insert_moves == ("2F", "U", "F'", "U'", "2F'")


def test_atomic_insert_no_input_mutation():
    c = _reachable_work_entry_cube(12)
    if c is None:
        pytest.skip("seed 12 不可达")
    fp_before = _fingerprint(c)
    _ = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert _fingerprint(c) == fp_before


def test_atomic_insert_deterministic():
    c = _reachable_work_entry_cube(13)
    if c is None:
        pytest.skip("seed 13 不可达")
    r1 = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    r2 = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert r1.success and r2.success
    assert r1.moves == r2.moves
    assert r1.relation_after == r2.relation_after


# ------------------------- 失败路径 -------------------------

def test_atomic_insert_joint_setup_unreachable_returns_error():
    # 遍历 seed，找到返回 JOINT_SETUP_UNREACHABLE 的（结构不变量组合）
    found = None
    for seed in range(1, 60):
        c = _raw_cube(seed)
        r = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
        if r.error_code == JOINT_SETUP_UNREACHABLE:
            found = r
            break
    assert found is not None, "未遇到 JOINT_SETUP_UNREACHABLE（说明 24 个结构性不可达组合未触发）"
    assert not found.success
    assert found.moves == ()


def test_atomic_insert_precondition_centers_unsolved_rejected():
    import random
    rnd = random.Random(2)
    c = Cube5.solved()
    c.apply_moves([rnd.choice(["R", "U", "F", "R'", "U'", "F'"]) for _ in range(4)])
    # 用宽转一层确保中心颜色不再归面（free-slice 打开切片即破坏中心归面）
    if centers_are_color_solved(c):
        c.apply_move("2R")
    assert not centers_are_color_solved(c)
    r = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert not r.success
    assert r.error_code == PRECONDITION_FAILED


# ------------------------- 返回类型 / 联合定位 -------------------------

def test_result_type_fields_are_present_on_success():
    c = _reachable_work_entry_cube(14)
    if c is None:
        pytest.skip("seed 14 不可达")
    r = insert_wing_atomic(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert isinstance(r, AtomicWingInsertResult)
    assert r.middle_piece_id == UF_MID
    assert r.wing_piece_id == UF_WA
    assert isinstance(r.setup_moves, tuple)
    assert isinstance(r.insert_moves, tuple)
    assert len(r.moves) == len(r.setup_moves) + len(r.insert_moves)


def test_relation_before_is_strictly_below_target_for_reachable():
    c = _reachable_work_entry_cube(15)
    if c is None:
        pytest.skip("seed 15 不可达")
    r = middle_wing_relation_real(c, UF_MID, UF_WA)
    assert r.relation_level < REL_COMBO  # 前置：中棱在工作槽、翼在入口 → 不同槽
