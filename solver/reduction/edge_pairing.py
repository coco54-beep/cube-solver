"""4x4 棱块配对求解器（约减法第 2 步）。

在六面中心已还原的基础上，把 24 个棱翼块配对成 12 组（每组两个同色翼块
落在同一个棱槽内）。只使用不破坏中心的状态操作：

- 外层转动 (R/L/U/D/F/B) 保持中心不变，且保持"已配对"状态不变（成组移动）。
- 原始子 P = u R U R' F R' F' R u' 保中心，交换 FR-bottom 与 BR-top 两个
  翼位，并把 4 个 U 层棱组整体轮换（已配对的组仍保持配对）。
- 通过外层 setup 把任意两个翼位 a、b 移到 (FR-bottom, BR-top)，再执行 P，
  再逆 setup，得到"交换 a、b 两个翼块"的原始子，中心不变且其它已配对组
  只被整体移动、不被打散。

配对算法（贪心）：
    逐槽检查，若某槽两个翼块不是同一颜色组，把"正确颜色组"的另一翼从
    别处换入该槽。每一步交换都会让"配对完成槽数"严格增加，最多 12 步。
"""

from collections import defaultdict, deque
from typing import List, Optional, Tuple

from cube.cube4 import Cube4
from cube.coordinates import TURNS, FACE_AXIS_SIGN, is_in_layer
from cube.notation import parse_move_str, suffix_for_count

Coord = Tuple[int, int, int]

# 12 个棱槽（每个槽 = 该棱对应的两个翼位坐标）
SLOTS = {
    "FU": [(-1, 3, 3), (1, 3, 3)],
    "RU": [(3, 3, -1), (3, 3, 1)],
    "BU": [(-1, 3, -3), (1, 3, -3)],
    "LU": [(-3, 3, -1), (-3, 3, 1)],
    "FD": [(-1, -3, 3), (1, -3, 3)],
    "RD": [(3, -3, -1), (3, -3, 1)],
    "BD": [(-1, -3, -3), (1, -3, -3)],
    "LD": [(-3, -3, -1), (-3, -3, 1)],
    "FR": [(3, -1, 3), (3, 1, 3)],
    "BR": [(3, -1, -3), (3, 1, -3)],
    "FL": [(-3, -1, 3), (-3, 1, 3)],
    "BL": [(-3, -1, -3), (-3, 1, -3)],
}
SLOT_OF = {p: n for n, poss in SLOTS.items() for p in poss}

# 面轴约定: 轴 0=X, 1=Y, 2=Z; 每轴正负各对应一个面
_FACE_BY_AXIS = {0: ("R", "L"), 1: ("U", "D"), 2: ("F", "B")}

OUTER = ["R", "R'", "R2", "L", "L'", "L2", "U", "U'", "U2",
         "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2"]

# 原始子 P = u R U R' F R' F' R u'
P = ["u", "R", "U", "R'", "F", "R'", "F'", "R", "u'"]

# P 交换的两个翼位（setup 目标）
_FR_BOTTOM = (3, -1, 3)
_BR_TOP = (3, 1, -3)


def _wings_of_solved() -> List[Coord]:
    return sorted(p for p, c in Cube4.solved().cubies.items() if len(c.stickers) == 2)


WINGS = _wings_of_solved()


def _build_pos_table() -> dict:
    """预计算每个外层转动对 24 个翼位的置换表。"""
    table = {}
    for mv in OUTER:
        label, is_wide, count = parse_move_str(mv)
        rot = TURNS[label]
        tbl = {}
        for p in WINGS:
            if is_in_layer(4, label, False, p):
                q = p
                for _ in range(count):
                    q = rot(*q)
                tbl[p] = q
            else:
                tbl[p] = p
        table[mv] = tbl
    return table


_POS_TBL = _build_pos_table()


def _move_pos(mv: str, p: Coord) -> Coord:
    return _POS_TBL[mv][p]


def _inv_of(mv: str) -> str:
    label, is_wide, count = parse_move_str(mv)
    return label + suffix_for_count((4 - count) % 4)


def _slot_of(pos: Coord) -> Tuple[str, ...]:
    fs = []
    for ax, v in enumerate(pos):
        if abs(v) == 3:
            fs.append(_FACE_BY_AXIS[ax][0] if v > 0 else _FACE_BY_AXIS[ax][1])
    return tuple(sorted(fs))


def _find_setup_pair(
    a: Coord,
    b: Coord,
    goal: Optional[Tuple[Coord, Coord]] = None,
    cap: int = 8,
) -> Optional[List[str]]:
    """寻找仅由外层转动组成的 setup，把翼位 a 送到 goal[0]、b 送到 goal[1]。

    goal 默认为 (FR-bottom, BR-top)。返回动作列表；若超出深度则返回 None。
    """
    if goal is None:
        goal = (_FR_BOTTOM, _BR_TOP)
    start = (a, b)
    if start == goal:
        return []
    parent = {start: (None, None)}
    levels = [start]
    for depth in range(cap):
        nxt = []
        for st in levels:
            pa, pb = st
            for mv in OUTER:
                ns = (_move_pos(mv, pa), _move_pos(mv, pb))
                if ns in parent:
                    continue
                parent[ns] = (st, mv)
                nxt.append(ns)
                if ns == goal:
                    seq = []
                    cur = ns
                    while parent[cur][0] is not None:
                        prev, m = parent[cur]
                        seq.append(m)
                        cur = prev
                    seq.reverse()
                    return seq
        levels = nxt
    return None


def _find_best_setup(
    a: Coord,
    b: Coord,
    cap: int = 8,
) -> Optional[List[str]]:
    """在两种目标摆放次序中取较短的一个 setup。

    P 交换的是 FR-bottom 与 BR-top，因此 setup 把 a、b 放到这两个位置时，
    前后次序无关紧要，两种目标各搜索一次，取较短者。
    """
    best = None
    for goal in ((_FR_BOTTOM, _BR_TOP), (_BR_TOP, _FR_BOTTOM)):
        seq = _find_setup_pair(a, b, goal=goal, cap=cap)
        if seq is None:
            continue
        if best is None or len(seq) < len(best):
            best = seq
    return best


def _apply(cube, moves: List[str]) -> None:
    for m in moves:
        for tok in m.split():
            cube.apply_move(tok)


def _wing_id(cube) -> dict:
    """pos -> 该翼块的两个颜色 (frozenset)。"""
    return {p: frozenset(c.stickers.values())
            for p, c in cube.cubies.items() if len(c.stickers) == 2}


def matched_slots(cube) -> int:
    """统计配对完成的槽数（槽内两个翼块同色组）。"""
    wa = _wing_id(cube)
    by = defaultdict(list)
    for p, i in wa.items():
        by[_slot_of(p)].append(i)
    return sum(1 for ids in by.values() if len(ids) == 2 and ids[0] == ids[1])


def edges_paired(cube) -> bool:
    """12 个棱槽全部配对完成。"""
    return matched_slots(cube) == 12


def _compress_log(moves: List[str]) -> List[str]:
    """合并相邻同面同宽层动作（R R -> R2，R R' -> 空），安全等价变换。"""
    stacked = []  # ((label, is_wide), count)
    for m in moves:
        for tok in m.split():
            label, is_wide, count = parse_move_str(tok)
            key = (label, is_wide)
            while stacked and stacked[-1][0] == key:
                prev_count = stacked[-1][1]
                count = (prev_count + count) % 4
                stacked.pop()
            if count != 0:
                stacked.append((key, count))
    out = []
    for (label, is_wide), count in stacked:
        base = label.lower() if is_wide else label
        out.append(base + suffix_for_count(count))
    return out


def _swap_positions(
    cube,
    a: Coord,
    b: Coord,
    log: List[str],
    setup: Optional[List[str]] = None,
) -> bool:
    """交换翼位 a 与 b 的两个翼块（setup + P + 逆 setup）。

    结果：a、b 两个翼块互换；中心不变；其它已配对组保持配对（可能整体移位）。
    setup 可预先由 _find_best_setup 计算好并传入，避免重复 BFS。
    """
    if setup is None:
        setup = _find_best_setup(a, b)
    if setup is None:
        return False
    log.extend(setup)
    log.extend(P)
    log.extend([_inv_of(m) for m in reversed(setup)])
    _apply(cube, setup)
    _apply(cube, P)
    _apply(cube, [_inv_of(m) for m in reversed(setup)])
    return True


def _candidate_swaps(cube, log):
    """枚举全部候选交换，按 (压缩后净长度, setup 长度) 升序。

    返回列表元素 (new_len, setup_len, setup, ypos, other)：对未配对槽换入正确
    颜色翼块，遍历每槽两个保留方向 × 所有同色换入源；对 setup 做保中心 BFS。
    """
    wa = _wing_id(cube)
    by_slot = defaultdict(list)
    for p, i in wa.items():
        by_slot[_slot_of(p)].append(i)
    out = []
    for target, ids in by_slot.items():
        if ids[0] == ids[1]:
            continue
        t_pos = [p for p in WINGS if _slot_of(p) == target]
        for swap_keep, swap_out in ((t_pos[0], t_pos[1]), (t_pos[1], t_pos[0])):
            want = wa[swap_keep]
            others = [
                p for p in WINGS
                if p != swap_keep and _slot_of(p) != target and wa[p] == want
            ]
            for other in others:
                setup = _find_best_setup(swap_out, other, cap=8)
                if setup is None:
                    continue
                swap_seq = setup + list(P) + [_inv_of(m) for m in reversed(setup)]
                new_len = len(_compress_log(log + swap_seq))
                out.append((new_len, len(setup), setup, swap_out, other))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def _pair_beam_finish(cube, log, width=8, max_nodes=600, cancel_event=None):
    """受限 beam：从当前状态把剩余配棱搜到全部配对。

    每层展开全部候选交换并按压缩长度保留 width 条（用翼排列 + 日志尾去重）。
    一旦某层出现完成节点即返回该层最短日志；超出 max_nodes 预算仍未完成则
    返回 None（调用方回退贪心）。只读输入，不修改 cube/log。
    """
    beam = [(cube.clone(), list(log))]
    expanded = 0
    while beam:
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("edge pairing cancelled")
        done = [lg for _c, lg in beam if edges_paired(_c)]
        if done:
            done.sort(key=len)
            return done[0]
        nxt = []
        for _c, lg in beam:
            if edges_paired(_c):
                continue
            for cand in _candidate_swaps(_c, lg):
                expanded += 1
                if expanded > max_nodes:
                    return None
                nc = _c.clone()
                nl = list(lg)
                _swap_positions(nc, cand[3], cand[4], nl, setup=cand[2])
                nl[:] = _compress_log(nl)
                nxt.append((nc, nl))
        nxt.sort(key=lambda t: len(t[1]))
        beam = []
        seen = set()
        for nc, nl in nxt:
            key = (tuple(sorted(_wing_id(nc).items())), tuple(nl[-2:]))
            if key in seen:
                continue
            seen.add(key)
            beam.append((nc, nl))
            if len(beam) >= width:
                break
    return None


def pair_edges(
    cube,
    max_swaps: int = 60,
    cancel_event=None,
    progress_callback=None,
    tail_width: int = 0,
    tail_max_nodes: int = 600,
    tail_matched: int = 7,
) -> List[str]:
    """配对 12 个棱组，返回所用的动作列表（不修改输入 cube）。

    要求调用前中心已还原。内部在副本上执行，完成后返回动作序列，由调用方
    自行决定是否应用到原立方体。支持 cancel_event（threading.Event）与
    progress_callback（每完成一步配对回调 dict，含当前已配对槽数）。

    当 tail_width>0 且已配对槽数 >= tail_matched 时，改用受限 beam 完成尾段
    （贪心易在最后几根局部最优），预算不足自动回退贪心。默认关闭，行为不变。
    """
    work = cube.clone()
    log: List[str] = []
    beam_tried = False
    for step in range(max_swaps):
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("edge pairing cancelled")
        if edges_paired(work):
            break
        if progress_callback is not None:
            progress_callback({"paired": matched_slots(work), "step": step})
        if tail_width and not beam_tried and matched_slots(work) >= tail_matched:
            beam_tried = True
            bl = _pair_beam_finish(
                work, log, width=tail_width, max_nodes=tail_max_nodes,
                cancel_event=cancel_event,
            )
            if bl is not None:
                log = bl
                break
        # 贪心单步：选压缩后净长度最短的候选交换
        cands = _candidate_swaps(work, log)
        if not cands:
            break
        _, _, setup, ypos, other = cands[0]
        if not _swap_positions(work, ypos, other, log, setup=setup):
            break
        # 日志保持为「已压缩」状态，供下一轮按压缩长度择优。
        log[:] = _compress_log(log)
    return log


def solve_edges(cube) -> List[str]:
    """配对棱块的高层入口（不修改输入，返回动作）。"""
    moves = pair_edges(cube)
    check = cube.clone()
    check.apply_moves(moves)
    if not edges_paired(check):
        raise ValueError("edge pairing failed")
    return moves
