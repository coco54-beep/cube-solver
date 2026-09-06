"""5x5 配棱「保护事务」（Slice-band / free-slice 保护原型的核心数据结构与 Gate 1 搜索）。

背景：`pair_all_edges` 的原子级贪婪只能到约 7/12，因为每次 inner-slice 装配都会
拆散此前已配好的棱组。这里改为**事务（transaction）**视角：允许事务中间配对退化、
中心被扰动，但事务结束时要求：

    centers_are_color_solved(after)
    and 原保护组全部存活
    and 配对槽数相比 before 至少 +1

关键概念：
- 块身份（piece identity）：用 `Cubie.home` 坐标（不随移动变化）唯一标识每个棱块。
- ProtectedTredge：一条已配好棱的身份组（中棱 home + 两翼 home，两翼规范排序）。
- is_tredge_group_paired：这 3 个特定身份块当前是否仍聚集在**某个**逻辑槽且该槽配对
  （不要求原槽 / home）。
- PairingTransaction：一笔事务的完整诊断记录（动作、前后配对、保护组存活/破裂、
  新生成组、中心状态、指纹）。

本模块只读、无副作用；只做统计与判定，不修改任何传入 cube。
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Dict, FrozenSet, Iterator, List, Optional, Sequence, Tuple

from cube.cube5 import Cube5
from cube.cubie_model import Cubie

from .free_slice import _fixed_centers_preserved
from .positions import SLOT_NAMES, slot, edge_type_of_cubie, slot_of
from .state import centers_are_color_solved, is_edge_paired, paired_count, face_colors

Coord = Tuple[int, int, int]

# 宽层四分之一转（作为自由切片打开/关闭动作）。
WIDE_QUARTER_MOVES: Tuple[str, ...] = (
    "2U", "2U'", "2D", "2D'",
    "2L", "2L'", "2R", "2R'",
    "2F", "2F'", "2B", "2B'",
)

# 外层动作。
OUTER_MOVES: Tuple[str, ...] = (
    "U", "U'", "U2", "D", "D'", "D2",
    "L", "L'", "L2", "R", "R'", "R2",
    "F", "F'", "F2", "B", "B'", "B2",
)


def base_face(mv: str) -> str:
    """去掉层数/计数前缀，返回基本面字母。"""
    return mv if mv.isalpha() else mv[1:]


def inverse_move(mv: str) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def same_face(a: str, b: str) -> bool:
    return base_face(a) == base_face(b)


# --- 块身份 ---------------------------------------------------------------


@dataclass(frozen=True)
class ProtectedTredge:
    """一条已配棱的身份组（用 home 坐标唯一标识）。"""

    edge_type: FrozenSet[str]          # 色对（frozenset，无色序）
    middle_piece_id: Coord             # 中棱 home
    wing_piece_ids: Tuple[Coord, Coord]  # 两翼 home，规范排序


def _cubie_with_home(cube: Cube5, home: Coord) -> Optional[Cubie]:
    for c in cube.cubies.values():
        if c.home == home:
            return c
    return None


def extract_paired_tredges(cube: Cube5) -> Tuple[ProtectedTredge, ...]:
    """提取当前所有逻辑槽中「已配对」的棱组，按块身份表示。"""
    out = []
    for name in SLOT_NAMES:
        if not is_edge_paired(cube, name):
            continue
        s = slot(name)
        mid = cube.cubies[s.middle]
        w1 = cube.cubies[s.left_wing]
        w2 = cube.cubies[s.right_wing]
        out.append(ProtectedTredge(
            edge_type=edge_type_of_cubie(mid),
            middle_piece_id=mid.home,
            wing_piece_ids=tuple(sorted((w1.home, w2.home))),
        ))
    # 规范排序（按中棱 home、再两翼），保证确定性。
    return tuple(sorted(
        out,
        key=lambda g: (g.middle_piece_id, g.wing_piece_ids[0], g.wing_piece_ids[1]),
    ))


def is_tredge_group_paired(cube: Cube5, group: ProtectedTredge) -> bool:
    """这 3 个身份块当前是否聚集在**某个**逻辑槽且该槽配对。

    不要求它们回到原槽或 home；只要求三者当前位于同一逻辑槽，且该槽
    `is_edge_paired` 为真（槽内色对一致且朝向一致）。
    """
    comb = [group.middle_piece_id, group.wing_piece_ids[0], group.wing_piece_ids[1]]
    cubs = []
    for hm in comb:
        c = _cubie_with_home(cube, hm)
        if c is None:
            return False
        cubs.append(c)
    names = {slot_of(c.pos) for c in cubs}
    if len(names) != 1:
        return False
    (name,) = names
    return is_edge_paired(cube, name)


# --- 事务结果 -------------------------------------------------------------


@dataclass(frozen=True)
class PairingTransaction:
    """一笔配棱保护事务的完整诊断记录。"""

    moves: Tuple[str, ...]
    open_slice: str
    close_slice: str

    paired_before: int
    paired_after: int
    net_gain: int

    protected_before: Tuple[ProtectedTredge, ...]
    protected_survived: Tuple[ProtectedTredge, ...]
    protected_broken: Tuple[ProtectedTredge, ...]
    created_groups: Tuple[ProtectedTredge, ...]

    centers_solved_after: bool
    fixed_centers_preserved: bool

    outer_length: int
    state_fingerprint_before: str
    state_fingerprint_after: str

    @property
    def gate1_success(self) -> bool:
        """Gate 1 严格成功条件：
        中心按颜色归面 ∧ 固定面心保持 ∧ 原保护组全部存活 ∧ 配对数至少 +1。
        """
        return (
            self.centers_solved_after
            and self.fixed_centers_preserved
            and not self.protected_broken
            and self.paired_after >= self.paired_before + 1
        )


# --- 状态指纹 -------------------------------------------------------------

_FACE_SIG = ("U", "R", "F", "D", "L", "B")


def cube_fingerprint(cube: Cube5) -> str:
    """对每个 cubie，按 (home, pos, 规范化的 sticker 颜色) 序列化；确定性。

    用于 fixture 重放校验与事务前后指纹。
    """
    from cube.coordinates import FACE_AXIS_SIGN

    def _sig(c: Cubie) -> str:
        dirs = sorted(c.stickers.keys())
        col_str = ",".join("%s%s" % (c.stickers[d], d) for d in dirs)
        return "%s>%s>%s" % (c.home, c.pos, col_str)

    items = [k for k in cube.cubies.keys()]
    return "|".join(_sig(cube.cubies[k]) for k in sorted(items))


# --- 候选枚举 -------------------------------------------------------------


def enumerate_outer_sequences(max_depth: int) -> Iterator[Tuple[str, ...]]:
    yield ()
    for n in range(1, max_depth + 1):
        for seq in product(OUTER_MOVES, repeat=n):
            # 跳过同面连续动作（可化简，避免冗余）。
            bad = False
            for i in range(1, len(seq)):
                if same_face(seq[i - 1], seq[i]):
                    bad = True
                    break
            if bad:
                continue
            yield seq


def enumerate_wide_outer_wide(max_outer: int) -> Iterator[Tuple[str, ...]]:
    """枚举 W + outer(1..max_outer) + W⁻¹ 宏序列。"""
    for wide in WIDE_QUARTER_MOVES:
        close = inverse_move(wide)
        for outer in enumerate_outer_sequences(max_outer):
            if not outer:
                continue
            yield (wide,) + outer + (close,)


# --- 候选评估与 Gate 1 搜索 ----------------------------------------------


def evaluate_candidate(before: Cube5, moves: Sequence[str]) -> PairingTransaction:
    """在真实 Cube5 上重放一段宏，生成完整事务诊断。不改动 before。"""
    protected = extract_paired_tredges(before)
    paired_before = paired_count(before)
    fpb = cube_fingerprint(before)

    after = before.clone()
    for mv in moves:
        after.apply_move(mv)

    paired_after = paired_count(after)

    survived = tuple(g for g in protected if is_tredge_group_paired(after, g))
    broken = tuple(g for g in protected if not is_tredge_group_paired(after, g))

    after_groups = set(extract_paired_tredges(after))
    before_groups = set(protected)
    created = tuple(sorted(after_groups - before_groups, key=lambda g: g.middle_piece_id))

    open_slice = moves[0] if moves else ""
    close_slice = moves[-1] if moves else ""
    outer_length = max(0, len(moves) - 2)

    return PairingTransaction(
        moves=tuple(moves),
        open_slice=open_slice,
        close_slice=close_slice,
        paired_before=paired_before,
        paired_after=paired_after,
        net_gain=paired_after - paired_before,
        protected_before=protected,
        protected_survived=survived,
        protected_broken=broken,
        created_groups=created,
        centers_solved_after=centers_are_color_solved(after),
        fixed_centers_preserved=_fixed_centers_preserved(after),
        outer_length=outer_length,
        state_fingerprint_before=fpb,
        state_fingerprint_after=cube_fingerprint(after),
    )


def search_gate1(stuck: Cube5, max_outer: int = 2) -> List[PairingTransaction]:
    """在 stuck（配对数固定，中心可能被 inner-slice 配棱扰动）上搜索 Gate 1 事务。

    事务语义：*结束后* 中心按颜色归面、原保护组全部存活、配对槽数至少 +1。
    stuck 开始时的中心状态不作要求（inner-slice 配棱必然扰动中心，这是耦合的体现）；
    `gate1_success` 基于 after 态判定。

    返回按 (是否 Gate 1 命中, 存活保护组数, 配对后数, 新生成组数, -动作长度) 排序的
    候选列表（含命中的前排与最接近的若干候选）。
    """
    hits = []
    for moves in enumerate_wide_outer_wide(max_outer):
        tx = evaluate_candidate(stuck, moves)
        hits.append(tx)

    def rank(tx: PairingTransaction):
        return (
            tx.gate1_success,
            len(tx.protected_survived),
            tx.paired_after,
            len(tx.created_groups),
            -len(tx.moves),
        )

    hits.sort(key=rank, reverse=True)
    return hits


def gate1_stats(hits: List[PairingTransaction]) -> Dict[str, int]:
    """对候选做分级统计，帮助判断失败原因。"""
    stats = {
        "gate1": 0,
        "center_ok_protected_all": 0,
        "center_ok_net_gain": 0,
        "protected_all_net_gain": 0,
        "center_ok": 0,
        "any_created": 0,
        "total": len(hits),
    }
    for tx in hits:
        if tx.gate1_success:
            stats["gate1"] += 1
        if tx.centers_solved_after and not tx.protected_broken:
            stats["center_ok_protected_all"] += 1
        if tx.centers_solved_after and tx.net_gain >= 1:
            stats["center_ok_net_gain"] += 1
        if not tx.protected_broken and tx.net_gain >= 1:
            stats["protected_all_net_gain"] += 1
        if tx.centers_solved_after:
            stats["center_ok"] += 1
        if tx.created_groups:
            stats["any_created"] += 1
    return stats
