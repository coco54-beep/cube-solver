"""4x4 中心还原求解器（两阶段分解：联合 U+D -> 侧面）。

Phase A (joint U+D):
    状态 = U-home 中心 + D-home 中心在 24 个槽位的占位掩码。
    共 C(24,4)*C(20,4) = 51,482,970 个状态。
    有效转动只有 8 个宽层 (f/f'/b/b'/r/r'/l/l')。
    用 colex 组合排名把状态压成 [0, JOINT_STATE_COUNT) 的整数,
    BFS 距离表 (dist) 贪心下降。

Phase B (sides):
    U/D 还原后, 16 个侧面中心 (F/B/R/L) 各有一个 home 面 (2 bit)。
    共 63,063,000 个状态, 12 个 UD 保持转动。
    查预生成的 p4_table.bin (mmap + 二分查找) 下降。
"""

import itertools
import mmap
import os
import struct
import time
from math import comb
from typing import Callable, Dict, List, Optional, Tuple

from primitives import ALL_CENTERS, MOVES, SLOT_FACE, SLOT_INDEX


# ---------- Phase A: colex 组合排名 ----------

COMB = {}
for _n in range(25):
    for _k in range(5):
        COMB[(_n, _k)] = comb(_n, _k)

JOINT_STATE_COUNT = COMB[(24, 4)] * COMB[(20, 4)]  # 51,482,970
GOAL = (0xF0 << 24) | 0x0F


def rank_comb(positions: List[int], n: int, k: int) -> int:
    r = 0
    for j, p in enumerate(positions):
        r += COMB[(p, j + 1)]
    return r


def unrank_comb(r: int, n: int, k: int) -> List[int]:
    out = [0] * k
    rem = r
    for j in range(k - 1, -1, -1):
        c = 0
        while COMB[(c, j + 1)] <= rem:
            c += 1
        c -= 1
        out[j] = c
        rem -= COMB[(c, j + 1)]
    return out


def extract_bits(mask: int) -> List[int]:
    out = []
    m = mask
    while m:
        lsb = m & (-m)
        out.append(lsb.bit_length() - 1)
        m ^= lsb
    return out


def apply_mask_perm(mask: int, perm) -> int:
    out = 0
    m = mask
    while m:
        lsb = m & (-m)
        i = lsb.bit_length() - 1
        out |= 1 << perm[i]
        m ^= lsb
    return out


def reduce_d(d_pos: List[int], u_set) -> List[int]:
    u_sorted = sorted(u_set)
    ui = 0
    out = []
    for d in d_pos:
        while ui < 4 and u_sorted[ui] < d:
            ui += 1
        out.append(d - ui)
    return out


def unmap_d(d_reduced: List[int], u_set) -> List[int]:
    non_u = [s for s in range(24) if s not in u_set]
    return [non_u[x] for x in d_reduced]


def combined_to_rank(combined: int) -> int:
    u_mask = combined & 0xFFFFFF
    d_mask = (combined >> 24) & 0xFFFFFF
    u_pos = extract_bits(u_mask)
    d_pos = extract_bits(d_mask)
    u_set = set(u_pos)
    d_red = reduce_d(d_pos, u_set)
    return rank_comb(u_pos, 24, 4) * COMB[(20, 4)] + rank_comb(d_red, 20, 4)


def rank_to_combined(r: int) -> int:
    r_u = r // COMB[(20, 4)]
    r_d = r % COMB[(20, 4)]
    u_pos = unrank_comb(r_u, 24, 4)
    d_red = unrank_comb(r_d, 20, 4)
    u_set = set(u_pos)
    d_pos = unmap_d(d_red, u_set)
    u_mask = 0
    for v in u_pos:
        u_mask |= 1 << v
    d_mask = 0
    for v in d_pos:
        d_mask |= 1 << v
    return (d_mask << 24) | u_mask


def apply_combined(combined: int, perm) -> int:
    u_mask = combined & 0xFFFFFF
    d_mask = (combined >> 24) & 0xFFFFFF
    new_u = apply_mask_perm(u_mask, perm)
    new_d = apply_mask_perm(d_mask, perm)
    return (new_d << 24) | new_u


def inv_perm(p) -> List[int]:
    n = len(p)
    inv = [0] * n
    for i, v in enumerate(p):
        inv[v] = i
    return inv


# ---------- Phase A: 联合转动 (每对逆转动取一个) ----------

# 联合态 BFS 需要 20 个转动 (10 个基本转动 + 各自逆)，才能保证任意
# 含逆的打乱词到达的联合态都在 BFS 深度内；只取 10 个代表会使需逆
# 转动到达的态被高估 (距离膨胀) -> 下降失败。
# U/U'/D/D' 对联合态是恒等 (no-op)，但为与打乱词一致仍纳入。
# JOINT_MOVE_LABELS 保持 10 个基本转动 (test_joint_move_labels 约束)。
JOINT_MOVE_LABELS = ["F", "B", "R", "L", "f", "b", "r", "l", "u", "d"]
JOINT_BFS_LABELS = []
for _lab in JOINT_MOVE_LABELS:
    JOINT_BFS_LABELS.append(_lab)
    JOINT_BFS_LABELS.append(_lab + "'")
JOINT_MOVES = [MOVES[lab] for lab in JOINT_BFS_LABELS]
JOINT_INV_PERMS = [tuple(inv_perm(p)) for p in JOINT_MOVES]

_JOINT_LOOKUPS: Optional[dict] = None


def _build_joint_lookups() -> dict:
    """预计算联合态查找表 (惰性一次性构建)。

    bits24: 24-bit mask -> 排序的 4 位置元组 (C(24,4) 项)。
    u_rank: U mask -> C(24,4) 的 colex rank。
    rank20: 归一化 D mask -> C(20,4) 的 colex rank。
    apply:  每个转动的 24-bit mask -> 转动后 24-bit mask (10 x C(24,4))。
    """
    bits24 = {}
    for pos in itertools.combinations(range(24), 4):
        mask = 0
        for p in pos:
            mask |= 1 << p
        bits24[mask] = pos
    u_rank = {mask: rank_comb(pos, 24, 4) for mask, pos in bits24.items()}
    rank20 = {}
    for pos in itertools.combinations(range(20), 4):
        mask = 0
        for p in pos:
            mask |= 1 << p
        rank20[mask] = rank_comb(pos, 20, 4)
    apply_tbl = [
        {mask: apply_mask_perm(mask, JOINT_MOVES[mi]) for mask in bits24}
        for mi in range(len(JOINT_MOVES))
    ]
    return {"bits24": bits24, "u_rank": u_rank, "rank20": rank20,
            "apply": apply_tbl}


def _ensure_joint_lookups() -> dict:
    global _JOINT_LOOKUPS
    if _JOINT_LOOKUPS is None:
        _JOINT_LOOKUPS = _build_joint_lookups()
    return _JOINT_LOOKUPS


def combined_to_rank_fast(combined: int) -> int:
    """经预计算表给联合态排名 (快速路径)。"""
    lk = _JOINT_LOOKUPS
    if lk is None:
        return combined_to_rank(combined)
    u_mask = combined & 0xFFFFFF
    d_mask = (combined >> 24) & 0xFFFFFF
    u_pos = lk["bits24"][u_mask]
    d_pos = lk["bits24"][d_mask]
    d_red = 0
    ui = 0
    for j in range(4):
        dd = d_pos[j]
        while ui < 4 and u_pos[ui] < dd:
            ui += 1
        d_red |= 1 << (dd - ui)
    return lk["u_rank"][u_mask] * COMB[(20, 4)] + lk["rank20"][d_red]


# ---------- Phase B: UD 保持侧面转动 ----------

SIDE_FACES = ["F", "B", "R", "L"]
SIDE_FACE_INDEX = {f: i for i, f in enumerate(SIDE_FACES)}
SIDE_ORDER = [s for s in range(24) if SLOT_FACE[s] in SIDE_FACES]
_side_index = {s: i for i, s in enumerate(SIDE_ORDER)}


def _preserves_face(p, face: str) -> bool:
    slots = [i for i in range(24) if SLOT_FACE[i] == face]
    return all(p[s] in slots for s in slots)


def _side_perm_2bit(p):
    sp = []
    for s in SIDE_ORDER:
        d = p[s]
        if SLOT_FACE[d] not in SIDE_FACES:
            return None
        sp.append(_side_index[d])
    return tuple(sp)


SIDE_MOVES = []
SIDE_MOVE_LABELS = []
_SIDE_IDENT_PERM = tuple(range(16))
for _lab, _p in MOVES.items():
    if not (_preserves_face(_p, "U") and _preserves_face(_p, "D")):
        continue
    _sp = _side_perm_2bit(_p)
    if _sp is None or _sp == _SIDE_IDENT_PERM:
        continue
    SIDE_MOVES.append(_sp)
    SIDE_MOVE_LABELS.append(_lab)

SIDE_INV_PERMS = [tuple(inv_perm(sp)) for sp in SIDE_MOVES]


def _inv_label(lab: str) -> str:
    return lab[:-1] if lab.endswith("'") else lab + "'"


SIDE_INV_LABELS = [_inv_label(l) for l in SIDE_MOVE_LABELS]

IDENT_STATE = tuple(
    0 if SLOT_FACE[s] == "F" else
    1 if SLOT_FACE[s] == "B" else
    2 if SLOT_FACE[s] == "R" else
    3 for s in SIDE_ORDER)


def _enc(state) -> int:
    out = 0
    for i in range(16):
        out |= state[i] << (2 * i)
    return out


IDENT_CODE = _enc(IDENT_STATE)


def _apply_side_inv(code: int, inv_sp) -> int:
    out = 0
    for j in range(16):
        val = (code >> (2 * j)) & 3
        out |= val << (2 * inv_sp[j])
    return out


def _apply_side(code: int, sp) -> int:
    """Phase B 正向应用一个 UD 保持转动到 16 侧面中心 code。"""
    out = 0
    for j in range(16):
        val = (code >> (2 * j)) & 3
        out |= val << (2 * sp[j])
    return out


# ---------- 从 Cube 抽取状态 ----------

def extract_joint(cube) -> int:
    u_mask = 0
    d_mask = 0
    for slot in range(24):
        cub = cube.cubies[ALL_CENTERS[slot]]
        home_face = SLOT_FACE[SLOT_INDEX[cub.home]]
        if home_face == "U":
            u_mask |= 1 << slot
        elif home_face == "D":
            d_mask |= 1 << slot
    return (d_mask << 24) | u_mask


def extract_side_code(cube) -> int:
    code = 0
    for i, slot in enumerate(SIDE_ORDER):
        cub = cube.cubies[ALL_CENTERS[slot]]
        home_face = SLOT_FACE[SLOT_INDEX[cub.home]]
        code |= SIDE_FACE_INDEX[home_face] << (2 * i)
    return code


def centers_solved(cube) -> bool:
    for slot in range(24):
        cub = cube.cubies[ALL_CENTERS[slot]]
        if SLOT_FACE[SLOT_INDEX[cub.home]] != SLOT_FACE[slot]:
            return False
    return True


# ---------- Phase A: BFS 距离表 ----------

def build_joint_bfs(
    max_depth: int = 255,
    progress_callback: Optional[Callable[[dict], None]] = None,
    cancel_event=None,
) -> Tuple[bytearray, dict]:
    lk = _ensure_joint_lookups()
    bits24 = lk["bits24"]
    u_rank = lk["u_rank"]
    rank20 = lk["rank20"]
    apply_tbl = lk["apply"]
    c20 = COMB[(20, 4)]
    dist = bytearray([255]) * JOINT_STATE_COUNT
    dist[0] = 0  # GOAL 的 rank 为 0
    frontier = [GOAL]
    depth = 0
    visited = 1
    total_transitions = 0
    t0 = time.time()
    n_moves = len(JOINT_MOVES)
    while frontier and depth < max_depth:
        next_frontier = []
        d_next = depth + 1
        for cur in frontier:
            u_mask = cur & 0xFFFFFF
            d_mask = (cur >> 24) & 0xFFFFFF
            for mi in range(n_moves):
                new_u = apply_tbl[mi][u_mask]
                new_d = apply_tbl[mi][d_mask]
                total_transitions += 1
                nu_pos = bits24[new_u]
                nd_pos = bits24[new_d]
                d_red = 0
                ui = 0
                for j in range(4):
                    dd = nd_pos[j]
                    while ui < 4 and nu_pos[ui] < dd:
                        ui += 1
                    d_red |= 1 << (dd - ui)
                r = u_rank[new_u] * c20 + rank20[d_red]
                if dist[r] == 255:
                    dist[r] = d_next
                    visited += 1
                    next_frontier.append((new_d << 24) | new_u)
        if cancel_event is not None and cancel_event.is_set():
            raise CenterSolveError("Center solve cancelled")
        frontier = next_frontier
        depth += 1
        if progress_callback is not None:
            elapsed = time.time() - t0
            rate = total_transitions / elapsed if elapsed > 0 else 0.0
            progress_callback({
                "depth": depth,
                "frontier": len(frontier),
                "visited": visited,
                "transitions": total_transitions,
                "elapsed": elapsed,
                "rate": rate,
            })
    stats = {
        "max_depth_reached": depth,
        "visited": visited,
        "transitions": total_transitions,
        "elapsed": time.time() - t0,
    }
    return dist, stats


class CenterSolveError(Exception):
    pass


class CenterSolver4:
    def __init__(
        self,
        joint_dist: Optional[bytearray] = None,
        table_path: Optional[str] = None,
        joint_dist_path: Optional[str] = None,
    ):
        self.joint_dist = joint_dist
        if table_path is None:
            table_path = os.path.join(os.path.dirname(__file__), "..", "..", "p4_table.bin")
        self.table_path = os.path.abspath(table_path)
        if joint_dist_path is None:
            joint_dist_path = os.path.join(os.path.dirname(__file__), "..", "..", "joint_dist.bin")
        self.joint_dist_path = os.path.abspath(joint_dist_path)
        self._mm = None
        self._count = 0

    def close(self) -> None:
        if self._mm is not None:
            self._mm.close()
            self._mm = None

    # -- Phase B: p4_table.bin --
    def _ensure_table(self) -> None:
        if self._mm is not None:
            return
        path = self.table_path
        if not os.path.exists(path):
            raise CenterSolveError(f"Phase-4 table not found: {path}")
        with open(path, "rb") as f:
            self._mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        if self._mm[:4] != b"C4PT":
            self._mm.close()
            self._mm = None
            raise CenterSolveError("bad Phase-4 table header")
        self._count = struct.unpack_from("<I", self._mm, 4)[0]

    def _table_lookup(self, code: int) -> Optional[int]:
        lo, hi = 0, self._count - 1
        while lo <= hi:
            mid = (lo + hi) >> 1
            off = 8 + mid * 5
            mcode = struct.unpack_from("<I", self._mm, off)[0]
            if mcode == code:
                return self._mm[off + 4]
            if mcode < code:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    # -- Phase A: 距离表 --
    def _get_joint_dist(self, progress_callback=None, cancel_event=None) -> bytearray:
        if self.joint_dist is None:
            loaded = self._try_load_joint_dist()
            if loaded is None:
                self.joint_dist, _ = build_joint_bfs(
                    max_depth=255,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )
            else:
                self.joint_dist = loaded
        return self.joint_dist

    def _try_load_joint_dist(self) -> Optional[bytearray]:
        """Load a precomputed joint-distance table (1 byte per state).

        The table is a raw dump of the Phase-A distance array ordered by
        `combined_to_rank`, with dist[0] == 0 at the goal state. Falls back
        to None (build via BFS) if missing or the wrong size.
        """
        try:
            with open(self.joint_dist_path, "rb") as f:
                data = f.read()
        except OSError:
            return None
        if len(data) != JOINT_STATE_COUNT:
            return None
        return bytearray(data)

    def _descend_joint(
        self,
        combined: int,
        cancel_event=None,
        progress_callback=None,
    ) -> List[str]:
        dist = self._get_joint_dist(progress_callback=progress_callback, cancel_event=cancel_event)
        moves: List[str] = []
        cur = combined
        d = dist[combined_to_rank_fast(cur)]
        if d == 255:
            raise CenterSolveError("joint state outside BFS depth")
        steps = 0
        while d > 0:
            steps += 1
            if steps > 128:
                raise CenterSolveError("joint descent exceeded max depth")
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            found = False
            for mi in range(len(JOINT_MOVES)):
                ns = apply_combined(cur, JOINT_INV_PERMS[mi])
                if dist[combined_to_rank_fast(ns)] == d - 1:
                    moves.append(_inv_label(JOINT_BFS_LABELS[mi]))
                    cur = ns
                    d -= 1
                    found = True
                    break
            if not found:
                raise CenterSolveError(f"joint descent stuck at dist={d}")
        return moves

    def _descend_side(self, code: int, cancel_event=None) -> List[str]:
        self._ensure_table()
        moves: List[str] = []
        cur = code
        steps = 0
        while cur != IDENT_CODE:
            steps += 1
            if steps > 64:
                raise CenterSolveError("side descent exceeded max depth")
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            par = self._table_lookup(cur)
            if par is None:
                raise CenterSolveError(f"side state {cur:#x} not in Phase-4 table")
            cur = _apply_side_inv(cur, SIDE_INV_PERMS[par])
            moves.append(SIDE_INV_LABELS[par])
        return moves

    def _descend_side_seeded(
        self,
        code: int,
        seed: int,
        cancel_event=None,
    ) -> List[str]:
        """Phase B 下降的确定性变体：每步在「使距离 -1」的全部转动中按种子
        伪随机择步。与默认 _descend_side 同深度（最短），但路径不同，从而给出
        不同的内层切片奇偶 / 翼块落点，供「OLL parity 规避」择优使用。

        距离经 parent 链回溯计算并缓存；只依赖 p4_table.bin（mmap）。
        """
        self._ensure_table()
        import random as _random
        rng = _random.Random(0x9E3779B9 ^ seed)
        dist_cache = {IDENT_CODE: 0}

        def _dist(c: int) -> Optional[int]:
            if c in dist_cache:
                return dist_cache[c]
            par = self._table_lookup(c)
            if par is None:
                dist_cache[c] = None
                return None
            dd = _dist(_apply_side_inv(c, SIDE_INV_PERMS[par]))
            dist_cache[c] = None if dd is None else dd + 1
            return dist_cache[c]

        moves: List[str] = []
        cur = code
        d = _dist(cur)
        if d is None:
            raise CenterSolveError(f"side state {code:#x} not in Phase-4 table")
        steps = 0
        while cur != IDENT_CODE:
            steps += 1
            if steps > 64:
                raise CenterSolveError("side descent exceeded max depth")
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            opts = []
            for mi in range(len(SIDE_MOVES)):
                ns = _apply_side(cur, SIDE_MOVES[mi])
                if _dist(ns) == d - 1:
                    opts.append(mi)
            if not opts:
                raise CenterSolveError(f"side descent stuck at dist={d}")
            mi = rng.choice(opts)
            moves.append(SIDE_MOVE_LABELS[mi])
            cur = _apply_side(cur, SIDE_MOVES[mi])
            d -= 1
        return moves

    def _descend_joint_seeded(
        self,
        combined: int,
        seed: int,
        cancel_event=None,
    ) -> List[str]:
        """与 _descend_joint 相同的 Phase A 下降，但每步在「使距离 -1」的全部
        候选转动中做确定性伪随机择步（种子来自 seed）。

        任一步都保证距离严格减 1，因此总步数与默认贪心相同（不增加中心步数），
        而落点（翼块排列 / 侧中心排列）不同，从而给「择优」提供多条等价最优解。
        """
        import random as _random
        rng = _random.Random(0x9E3779B9 ^ seed)
        dist = self._get_joint_dist()
        moves: List[str] = []
        cur = combined
        d = dist[combined_to_rank_fast(cur)]
        if d == 255:
            raise CenterSolveError("joint state outside BFS depth")
        steps = 0
        n_moves = len(JOINT_MOVES)
        while d > 0:
            steps += 1
            if steps > 128:
                raise CenterSolveError("joint descent exceeded max depth")
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            opts: List[int] = []
            for mi in range(n_moves):
                ns = apply_combined(cur, JOINT_MOVES[mi])
                if dist[combined_to_rank_fast(ns)] == d - 1:
                    opts.append(mi)
            if not opts:
                raise CenterSolveError(f"joint descent stuck at dist={d}")
            mi = rng.choice(opts)
            moves.append(JOINT_BFS_LABELS[mi])
            cur = apply_combined(cur, JOINT_MOVES[mi])
            d -= 1
        return moves

    def solve(
        self,
        cube,
        cancel_event=None,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> List[str]:
        if cancel_event is not None and cancel_event.is_set():
            raise CenterSolveError("Center solve cancelled")
        work = cube.clone()
        moves: List[str] = []

        combined = extract_joint(work)
        if combined != GOAL:
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            a_moves = self._descend_joint(
                combined, cancel_event, progress_callback=progress_callback
            )
            work.apply_moves(a_moves)
            moves.extend(a_moves)

        code = extract_side_code(work)
        if code != IDENT_CODE:
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            b_moves = self._descend_side(code, cancel_event)
            work.apply_moves(b_moves)
            moves.extend(b_moves)

        if not centers_solved(work):
            raise CenterSolveError("centers not solved after descent")
        return moves


def solve_centers(
    cube,
    joint_dist: Optional[bytearray] = None,
    table_path: Optional[str] = None,
    cancel_event=None,
    progress_callback: Optional[Callable[[dict], None]] = None,
    joint_dist_path: Optional[str] = None,
) -> List[str]:
    solver = CenterSolver4(
        joint_dist=joint_dist,
        table_path=table_path,
        joint_dist_path=joint_dist_path,
    )
    try:
        return solver.solve(cube, cancel_event=cancel_event, progress_callback=progress_callback)
    finally:
        solver.close()


def solve_centers_variant(
    cube,
    seed: int,
    cancel_event=None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> List[str]:
    """求解中心，返回一条「确定性但不同于默认贪心」的等价最优解。

    与 solve_centers 同架构：Phase A 下降改用 seed 做确定性伪随机择步
    （每步仍严格使距离 -1，总中心步数不增加），Phase B 也走 seeded 变体。
    用于在若干条同长度的中心解中挑选对后续棱配对 / parity 最有利的一条。
    """
    solver = CenterSolver4()
    try:
        work = cube.clone()
        moves: List[str] = []

        combined = extract_joint(work)
        if combined != GOAL:
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            a_moves = solver._descend_joint_seeded(combined, seed, cancel_event)
            work.apply_moves(a_moves)
            moves.extend(a_moves)

        code = extract_side_code(work)
        if code != IDENT_CODE:
            if cancel_event is not None and cancel_event.is_set():
                raise CenterSolveError("Center solve cancelled")
            b_moves = solver._descend_side_seeded(code, seed ^ 0x5F3759DF, cancel_event)
            work.apply_moves(b_moves)
            moves.extend(b_moves)

        if not centers_solved(work):
            raise CenterSolveError("centers not solved after descent")
        return moves
    finally:
        solver.close()
