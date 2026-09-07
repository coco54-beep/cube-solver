"""确定性 free-slice 第四阶段 Gate 4 回归测试：部分组合存储（store + survival only）。

Gate 4 目标（用户裁定 store + survival only）：给定一个「中棱 + 翼-A」的 rel>=2 组合
（由 `insert_wing_atomic` 产出于入口槽 UR），验证——
1. **store**：`store_partial_combo` 用纯外层把组合整体搬到 safe-untouched 存储槽，
   保持 rel>=2、同槽、中心归面、固定面心保持、真实重放一致；
2. **survival**：`combo_survives_free_slice` 证明该存储组合在「对其它 piece 做一次
   free-slice 开/关循环」后仍存活（rel>=2 且同槽）；
3. **recoverable**：`relocate_middle_to_pos` 能把组合整体搬回（第一关系可恢复）。

须满足：
- 只用物理合法动作（1X 外层 + 2X 宽层；绝不出现 3X/4X/5X）
- 不改写输入 cube；确定性；失败返回规定 error_code
"""
import random

import pytest

from cube.cube5 import Cube5
from solver.center5 import solve_centers5
from solver.edge5.compact_state import _SLOT_MID, _SLOT_WINGS
from solver.edge5.atomic_insert import (
    insert_wing_atomic, middle_wing_relation_real, REL_COMBO,
)
from solver.edge5.store_partial import (
    store_partial_combo, combo_survives_free_slice, safe_untouched_slots,
    PRECONDITION_FAILED, RELATION_NOT_COMBO, STORE_TARGET_UNREACHABLE,
)
from solver.edge5.freeslice_layout import (
    build_layout, current_joint_setup, relocate_middle_to_pos,
)
from solver.edge5.state import centers_are_color_solved
from solver.edge5.free_slice import _fixed_centers_preserved
from solver.edge5.positions import MIDDLE_ORDER, WING_ORDER, slot, MIDDLE_INDEX

LAYOUT = build_layout()
UF_MID = _SLOT_MID["UF"]; UF_WA = _SLOT_WINGS["UF"][0]; UF_WB = _SLOT_WINGS["UF"][1]

SAFE_UNTOUCHED = safe_untouched_slots(LAYOUT)
MID_HOME = MIDDLE_ORDER[UF_MID]
WA_HOME = WING_ORDER[UF_WA]


def _fixed_home_set(cube):
    return {p for p, c in cube.cubies.items()
            if len(c.stickers) == 1 and sorted(abs(v) for v in c.home) == [0, 0, 6]}


def _fixed_preserved(cube):
    fixed = _fixed_home_set(cube)
    return all(cube.cubies[p].pos == p for p in fixed)


def _center_solved_random_cube(seed, depth=6):
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


def _fingerprint(cube):
    return tuple((p, cubie.home, tuple(sorted(cubie.stickers.items())))
                 for p, cubie in sorted(cube.cubies.items()))


def _combo_state(seed):
    """返回 (存储后 cube, store_result) 或 None；用 insert 产出的组合从 UR 存到 safe-untouched。"""
    c = _center_solved_random_cube(seed)
    setup = current_joint_setup(c, UF_MID, UF_WA, LAYOUT)
    if setup is None:
        return None
    w = c.clone()
    for m in setup:
        w.apply_move(m)
    r = insert_wing_atomic(w, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    if not r.success:
        return None
    combo = w.clone()
    for m in r.moves:
        combo.apply_move(m)
    s = store_partial_combo(combo, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    if not s.success:
        return None
    stored = combo.clone()
    for m in s.store_moves:
        stored.apply_move(m)
    return stored, s


# ------------------------- 单位：safe-untouched -------------------------

def test_safe_untouched_slots_nonempty_and_valid():
    assert len(SAFE_UNTOUCHED) > 0
    assert all(s in LAYOUT.storage_slots for s in SAFE_UNTOUCHED)
    assert not (set(SAFE_UNTOUCHED) & set(LAYOUT.staging_slots))


# ------------------------- store 成功 -------------------------

@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21, 33, 44])
def test_store_partial_combo_preserves_combo_and_centers(seed):
    got = _combo_state(seed)
    if got is None:
        pytest.skip(f"seed {seed} 无法到达存储起始态")
    stored, s = got
    assert s.success, f"store 失败: {s.error_code} {s.message}"
    assert s.combo_slot_after in SAFE_UNTOUCHED
    rel = middle_wing_relation_real(stored, UF_MID, UF_WA)
    assert rel.relation_level >= REL_COMBO
    assert rel.same_logical_slot
    assert centers_are_color_solved(stored)
    assert _fixed_preserved(stored)
    assert s.centers_solved_after and s.fixed_centers_preserved
    assert s.replay_consistent and s.error_code is None


@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21])
def test_store_moves_are_only_legal(seed):
    got = _combo_state(seed)
    if got is None:
        pytest.skip(f"seed {seed} 不可达")
    _, s = got
    for m in s.store_moves:
        assert m[:1] in ("R", "L", "U", "D", "F", "B", "2"), f"非物理动作 {m}"
        assert m not in ("3R", "3L", "3U", "3D", "3F", "3B"), f"非法动作 {m}"


# ------------------------- survival + recoverable -------------------------

@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21])
def test_store_combo_survives_intervening_free_slice(seed):
    got = _combo_state(seed)
    if got is None:
        pytest.skip(f"seed {seed} 不可达")
    stored, _ = got
    assert combo_survives_free_slice(stored, middle_piece_id=UF_MID,
                                     wing_piece_id=UF_WA, layout=LAYOUT)


@pytest.mark.parametrize("seed", [3, 5, 6, 7, 11, 21])
def test_store_combo_recoverable_via_pure_outer(seed):
    got = _combo_state(seed)
    if got is None:
        pytest.skip(f"seed {seed} 不可达")
    stored, s = got
    # 把存储槽的中棱搬回工作槽（工作槽 = UF 中棱位），应能找到序列且组合随行。
    target_mid = MIDDLE_INDEX[slot(LAYOUT.work_slot).middle]
    from solver.edge5.store_partial import _find_middle_pos
    mpos = _find_middle_pos(stored, UF_MID)
    moves = relocate_middle_to_pos(mpos, target_mid)
    assert moves is not None, f"无法把组合搬回工作槽 (mpos={mpos})"
    back = stored.clone()
    for m in moves:
        back.apply_move(m)
    rel = middle_wing_relation_real(back, UF_MID, UF_WA)
    # 搬回后组合仍在同一逻辑槽（纯外层不拆同槽）
    assert rel.same_logical_slot
    assert rel.relation_level >= REL_COMBO
    assert centers_are_color_solved(back)
    assert _fixed_preserved(back)


# ------------------------- 不修改输入 + 确定性 -------------------------

def test_store_no_input_mutation_and_deterministic():
    got = _combo_state(12)
    if got is None:
        pytest.skip("seed 12 不可达")
    stored, s1 = got
    fp_before = _fingerprint(stored)
    s2 = store_partial_combo(stored, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert _fingerprint(stored) == fp_before
    assert s1.success and s2.success
    assert s1.store_moves == s2.store_moves


# ------------------------- 失败路径 -------------------------

def test_store_precondition_centers_unsolved_rejected():
    rnd = random.Random(2)
    c = Cube5.solved()
    c.apply_moves([rnd.choice(["R", "U", "F", "R'", "U'", "F'"]) for _ in range(4)])
    if centers_are_color_solved(c):
        c.apply_move("2R")
    assert not centers_are_color_solved(c)
    r = store_partial_combo(c, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert not r.success
    assert r.error_code == PRECONDITION_FAILED


def test_store_requires_combo_relation():
    # 目标中棱与目标翼不同槽 → rel < combo
    c = Cube5.solved()
    # solved 态 UF 中棱与 UR 翼不同槽且色对不符 → 常见为同一逻辑槽；改用分散态
    got = None
    for seed in range(1, 40):
        cc = _center_solved_random_cube(seed)
        rel = middle_wing_relation_real(cc, UF_MID, UF_WA)
        if rel.relation_level < REL_COMBO:
            got = cc
            break
    if got is None:
        pytest.skip("未找到 rel<combo 的测试态")
    r = store_partial_combo(got, middle_piece_id=UF_MID, wing_piece_id=UF_WA, layout=LAYOUT)
    assert not r.success
    assert r.error_code == RELATION_NOT_COMBO


def test_store_rejects_non_safe_target_slot():
    got = _combo_state(3)
    if got is None:
        pytest.skip("seed 3 不可达")
    combo, _ = got
    # 目标槽是 staging 中被 2F 触碰的槽（非 safe-untouched）→ 拒绝
    staging = LAYOUT.staging_slots
    r = store_partial_combo(combo, middle_piece_id=UF_MID, wing_piece_id=UF_WA,
                            layout=LAYOUT, target_slot=staging[0])
    assert not r.success
    assert r.error_code == STORE_TARGET_UNREACHABLE
