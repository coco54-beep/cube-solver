"""免费切片批次配棱（batch shared-slice）：真实 Cube5 验收的纯体（pure-body）批次搜索。

模型：`W body1 body2 ... W'`（只打开一次切片 W，中间可跑多个纯外层体，终点关闭）。
成功条件（仅在真实 Cube5 上判定）：
    centers_are_color_solved(after)
    and 所有原保护组（实体身份）都存活
    and paired_count(after) >= paired_count(before) + min_gain

关键约束（已由真实状态证明）：
- compact 态不含翼朝向，`三块同槽` ≠ `真实配对`，因此 compact 评分**不能**用于
  截断 top-N（否则会把真解挤出）。
- compact 模型只用于生成候选与**不会误杀真解的保守筛选**；
  真实 Cube5 负责排序关键指标与最终成功判定。

因此本模块的 `search_pure_body_batch` 采用「穷举体组合 + 真实重放验收」，不靠
compact 评分挑选。体库由 MacroIndex（中心保持宏）拆分 `(open, body, close)` 得到。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from cube.cube5 import Cube5

from .macro_index import build_macro_index, MacroIndex, OUTER
from .compact_state import step
from .state import centers_are_color_solved, is_edge_paired, paired_count
from .pairing_transaction import (
    ProtectedTredge,
    extract_paired_tredges,
    is_tredge_group_paired,
)
from .positions import SLOT_NAMES
from .free_slice import edge_relation


def _inverse(mv: str) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


def _open_close_of(moves: Tuple[str, ...]) -> Optional[Tuple[str, str]]:
    """从闭环宏 (W, *outer, W') 拆出 (open, close)。非该形状返回 None。"""
    if len(moves) < 3:
        return None
    open_mv, close_mv = moves[0], moves[-1]
    if _inverse(open_mv) != close_mv:
        return None
    if any(m not in OUTER for m in moves[1:-1]):
        return None
    return open_mv, close_mv


@dataclass(frozen=True)
class BatchBody:
    """一条可复用的「体」：某 open 切片下的一段纯外层序列。"""

    open_move: str
    body_moves: Tuple[str, ...]
    close_move: str
    source_macro_id: int


@dataclass(frozen=True)
class BatchSearchLimits:
    """纯体批次搜索的限制。"""

    max_bodies: int = 2
    # 每个 open 切片最多穷举的组合数上限（防止穷举爆炸）。
    max_combos_per_open: int = 4096
    # 保守筛选：体必须移到至少一个未配对 target 的某一块（不会误杀真解的宽松门槛）。
    conservative_target_filter: bool = True
    # 依次尝试每一个 open（按体中 precomputable 无关），严格按组合数顺序。
    iterative_deepening: bool = True


@dataclass(frozen=True)
class BatchPairingResult:
    success: bool
    moves: Tuple[str, ...]

    paired_before: int
    paired_after: int
    net_gain: int

    protected_before: Tuple[ProtectedTredge, ...]
    protected_survived: Tuple[ProtectedTredge, ...]
    protected_broken: Tuple[ProtectedTredge, ...]

    centers_solved_after: bool
    replay_consistent: bool

    open_move: Optional[str] = None
    body_count: int = 0
    candidates_checked: int = 0
    elapsed_seconds: float = 0.0

    error_code: Optional[str] = None
    message: str = ""
    store_stats: Optional["_StorePrefixStats"] = None


@dataclass(frozen=True)
class _StorePrefixStats:
    prefix_candidates: int = 0
    unique_prefix_states: int = 0
    per_open_prefix_states: Tuple[Tuple[str, int], ...] = ()
    protected_survived_rate: float = 0.0
    body_candidates_checked: int = 0
    center_failed: int = 0
    protected_failed: int = 0
    no_gain: int = 0
    success: int = 0
    best_paired_after: int = 0
    best_protected: int = 0


class _BodyDatabase:
    """惰性构建、只读的体库。"""

    _instance: Optional["_BodyDatabase"] = None

    def __init__(self, max_outer: int = 3):
        self.index: MacroIndex = build_macro_index(max_outer)
        # open_move -> list[BatchBody]
        self._groups: Dict[str, List[BatchBody]] = {}
        # open_move -> set[(middle,wing)]：打开态下的体效果指纹（用于去重）
        self._seen: Dict[str, Dict[Tuple, BatchBody]] = {}
        for mac in self.index.effects:
            oc = _open_close_of(mac.moves)
            if oc is None:
                continue
            open_mv, close_mv = oc
            body = mac.moves[1:-1]
            # 打开态下跑体的效果（去重键）：identity 先 apply open，再跑体，记录中/翼。
            from .macro_index import _IDENTITY, apply_macro
            st = apply_macro(_IDENTITY, (open_mv,))
            for mv in body:
                st = step(st, mv)
            fp = (st.middle, st.wing)
            d = self._seen.setdefault(open_mv, {})
            if fp not in d or len(body) < len(d[fp].body_moves):
                d[fp] = BatchBody(open_mv, body, close_mv, mac.macro_id)
        for open_mv, d in self._seen.items():
            self._groups[open_mv] = sorted(d.values(), key=lambda b: len(b.body_moves))

    @classmethod
    def instance(cls) -> "_BodyDatabase":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def open_moves(self) -> List[str]:
        return sorted(self._groups.keys())

    def bodies_for(self, open_move: str) -> List[BatchBody]:
        return self._groups.get(open_move, [])


def is_successful_batch(
    before: Cube5,
    after: Cube5,
    protected: Tuple[ProtectedTredge, ...],
    min_gain: int = 1,
) -> bool:
    """真实 Cube5 上的批次成功判定。"""
    return (
        centers_are_color_solved(after)
        and all(is_tredge_group_paired(after, g) for g in protected)
        and paired_count(after) >= paired_count(before) + min_gain
    )


def _replay(before: Cube5, moves: Tuple[str, ...]) -> Cube5:
    w = before.clone()
    for mv in moves:
        w.apply_move(mv)
    return w


def _unpaired_targets(cube: Cube5) -> List[str]:
    return [name for name in SLOT_NAMES if not is_edge_paired(cube, name)]


def _body_touches_unpaired(body: BatchBody, targets: List[str]) -> bool:
    """保守筛选：体是否移动了任何未配对 target 的某一块（开放态下比较）。

    用 compact 置换：「先 apply open（identity 基准），再跑体」与「只 apply open」
    相比，若某个 target 块（中或翼）的 home 落槽发生改变，即视为触块。
    要求「至少触块」，而成功批次必然使某 target 三块聚拢，因此不会误杀真解。
    """
    if not targets:
        return True
    from .macro_index import _IDENTITY, apply_macro
    from .free_slice import _slot_of_mid_idx, _slot_of_wing_idx, target_pieces

    base = apply_macro(_IDENTITY, (body.open_move,))
    st = apply_macro(base, tuple(body.body_moves))
    for name in targets:
        tp = target_pieces(name)
        if _slot_of_mid_idx(st, tp.middle_home) != _slot_of_mid_idx(base, tp.middle_home):
            return True
        if _slot_of_wing_idx(st, tp.wing_a_home) != _slot_of_wing_idx(base, tp.wing_a_home):
            return True
        if _slot_of_wing_idx(st, tp.wing_b_home) != _slot_of_wing_idx(base, tp.wing_b_home):
            return True
    return False


def search_pure_body_batch(
    cube: Cube5,
    *,
    min_gain: int = 1,
    max_bodies: int = 2,
    limits: Optional[BatchSearchLimits] = None,
    body_db: Optional[_BodyDatabase] = None,
    allowed_open_moves: Optional[Tuple[str, ...]] = None,
) -> BatchPairingResult:
    """穷举纯体组合 + 真实重放验收，找净增 >= min_gain 的批次。

    返回第一个命中的批量（不保证全局最短）。不会修改 `cube`。
    """
    import time
    db = body_db or _BodyDatabase.instance()
    limits = limits or BatchSearchLimits(max_bodies=max_bodies)

    protected = extract_paired_tredges(cube)
    paired_before = paired_count(cube)
    targets = _unpaired_targets(cube)

    t0 = time.time()
    checked = 0
    if allowed_open_moves is not None:
        open_moves = [m for m in db.open_moves if m in set(allowed_open_moves)]
    else:
        open_moves = db.open_moves

    # 预计算每个 open 的保守筛选后的候选体 + 关闭动作
    cand_by_open = {}
    for the_open in open_moves:
        cand = []
        for b in db.bodies_for(the_open):
            if limits.conservative_target_filter and not _body_touches_unpaired(b, targets):
                continue
            cand.append(b)
        cand_by_open[the_open] = (cand, _inverse(the_open))

    import itertools

    # 深度优先：先在所有 open 上遍历当前深度，命中即返回。
    for depth in range(1, limits.max_bodies + 1):
        for the_open, (cand, close) in cand_by_open.items():
            cnt = 0
            for combo in itertools.product(cand, repeat=depth):
                if cnt >= limits.max_combos_per_open:
                    break
                cnt += 1
                checked += 1
                seq = (the_open,) + tuple(m for b in combo for m in b.body_moves) + (close,)
                if len(seq) > 60:
                    continue
                w = cube.clone()
                for mv in seq:
                    w.apply_move(mv)
                if is_successful_batch(cube, w, protected, min_gain):
                    survived = tuple(g for g in protected if is_tredge_group_paired(w, g))
                    broken = tuple(g for g in protected if not is_tredge_group_paired(w, g))
                    return BatchPairingResult(
                        success=True,
                        moves=seq,
                        paired_before=paired_before,
                        paired_after=paired_count(w),
                        net_gain=paired_count(w) - paired_before,
                        protected_before=protected,
                        protected_survived=survived,
                        protected_broken=broken,
                        centers_solved_after=centers_are_color_solved(w),
                        replay_consistent=True,
                        open_move=the_open,
                        body_count=depth,
                        candidates_checked=checked,
                        elapsed_seconds=time.time() - t0,
                        message="pure_body_batch",
                    )
            if not limits.iterative_deepening:
                break

    return BatchPairingResult(
        success=False,
        moves=(),
        paired_before=paired_before,
        paired_after=paired_before,
        net_gain=0,
        protected_before=protected,
        protected_survived=(),
        protected_broken=protected,
        centers_solved_after=centers_are_color_solved(cube),
        replay_consistent=True,
        candidates_checked=checked,
        elapsed_seconds=time.time() - t0,
        error_code="NO_PURE_BODY_BATCH",
        message="no pure-body batch found within limits",
    )


def search_store_prefixed_batch(
    cube: Cube5,
    *,
    max_store_depth: int = 4,
    max_bodies: int = 3,
    pure_limits: Optional[BatchSearchLimits] = None,
    body_db: Optional[_BodyDatabase] = None,
) -> BatchPairingResult:
    """关闭态 store-prefix 批次：`outer_store_prefix + W body... W'`。

    先重排一个已有保护组（纯外层整体转存到该 open 切片的安全槽），再跑纯体批次，
    最后相对**原始**保护组事务原点做真实验收。store 只会整体搬运已配 tredge，
    不拆散、不改中心颜色归面。

    第一轮只允许一个 store-prefix（store 后不再 store），用真实状态指纹去重。
    """
    import time

    from .slice_band import band_for_open
    from .storage_planner import enumerate_store_paths

    db = body_db or _BodyDatabase.instance()
    pure_limits = pure_limits or BatchSearchLimits(max_bodies=max_bodies)

    protected = extract_paired_tredges(cube)
    original_count = paired_count(cube)

    t0 = time.time()
    prefix_candidates = 0
    unique_prefix_states = 0
    seen_fp = set()
    per_open: Dict[str, int] = {}
    body_checked = 0
    center_failed = 0
    protected_failed = 0
    no_gain = 0
    success = 0
    best_paired_after = original_count
    best_protected = len(protected)

    open_moves = db.open_moves
    for open_move in open_moves:
        band = band_for_open(open_move)
        for gidx, group in enumerate(protected):
            for _dst, store_moves in enumerate_store_paths(
                cube, group, band, max_store_depth
            ):
                prefix_candidates += 1
                stored = cube.clone()
                for mv in store_moves:
                    stored.apply_move(mv)
                fp = _store_prefix_fingerprint(stored)
                if fp in seen_fp:
                    continue
                seen_fp.add(fp)
                unique_prefix_states += 1
                per_open[open_move] = per_open.get(open_move, 0) + 1

                # store 应保留所有原始保护组 + 中心归面
                alive = sum(1 for g in protected if is_tredge_group_paired(stored, g))
                if alive != len(protected):
                    protected_failed += 1
                    best_protected = max(best_protected, alive)
                    continue
                if not centers_are_color_solved(stored):
                    center_failed += 1
                    continue

                # 限制到该 open 的纯体批次
                inner = search_pure_body_batch(
                    stored,
                    min_gain=1,
                    max_bodies=max_bodies,
                    limits=pure_limits,
                    body_db=db,
                    allowed_open_moves=(open_move,),
                )
                body_checked += inner.candidates_checked

                if inner.success:
                    full = tuple(store_moves) + tuple(inner.moves)
                    # 相对原始状态重放验收
                    verify = cube.clone()
                    for mv in full:
                        verify.apply_move(mv)
                    v_alive = sum(1 for g in protected if is_tredge_group_paired(verify, g))
                    v_paired = paired_count(verify)
                    if (centers_are_color_solved(verify)
                            and v_alive == len(protected)
                            and v_paired >= original_count + 1):
                        success += 1
                        return BatchPairingResult(
                            success=True,
                            moves=full,
                            paired_before=original_count,
                            paired_after=v_paired,
                            net_gain=v_paired - original_count,
                            protected_before=protected,
                            protected_survived=tuple(g for g in protected
                                                    if is_tredge_group_paired(verify, g)),
                            protected_broken=tuple(g for g in protected
                                                   if not is_tredge_group_paired(verify, g)),
                            centers_solved_after=centers_are_color_solved(verify),
                            replay_consistent=True,
                            open_move=open_move,
                            body_count=inner.body_count,
                            candidates_checked=body_checked,
                            elapsed_seconds=time.time() - t0,
                            message="store_prefixed_batch",
                            store_stats=_make_store_stats(
                                prefix_candidates, unique_prefix_states, per_open,
                                best_paired_after, best_protected, protected_failed,
                                center_failed, no_gain, success,
                            ),
                        )
                else:
                    best_paired_after = max(best_paired_after, inner.paired_after)
                    best_protected = max(best_protected, inner.paired_after)
                    no_gain += 1

    return BatchPairingResult(
        success=False,
        moves=(),
        paired_before=original_count,
        paired_after=original_count,
        net_gain=0,
        protected_before=protected,
        protected_survived=(),
        protected_broken=protected,
        centers_solved_after=centers_are_color_solved(cube),
        replay_consistent=True,
        candidates_checked=body_checked,
        elapsed_seconds=time.time() - t0,
        error_code="NO_STORE_PREFIXED_BATCH",
        message="no store-prefixed batch found within limits",
        store_stats=_make_store_stats(
            prefix_candidates, unique_prefix_states, per_open,
            best_paired_after, best_protected, protected_failed,
            center_failed, no_gain, success,
        ),
    )


def _store_prefix_fingerprint(cube: Cube5) -> str:
    from .pairing_transaction import cube_fingerprint

    return cube_fingerprint(cube)


def _make_store_stats(prefix, unique, per_open, best_paired, best_prot, prot_fail,
                      center_fail, no_gain, success):
    return _StorePrefixStats(
        prefix_candidates=prefix,
        unique_prefix_states=unique,
        per_open_prefix_states=tuple(sorted(per_open.items(), key=lambda t: t[0])),
        protected_survived_rate=(best_prot / 8) if best_prot else 0.0,
        body_candidates_checked=0,
        center_failed=center_fail,
        protected_failed=prot_fail,
        no_gain=no_gain,
        success=success,
        best_paired_after=best_paired,
        best_protected=best_prot,
    )


def search_inner_store_batch(
    cube: Cube5,
    *,
    max_store_depth: int = 3,
    max_bodies: int = 2,
    max_bodies_per_open: int = 20,
    max_store_paths_per_group: int = 3,
    max_checked: int = 20000,
    limits: Optional[BatchSearchLimits] = None,
    body_db: Optional[_BodyDatabase] = None,
    allowed_open_moves: Optional[Tuple[str, ...]] = None,
) -> BatchPairingResult:
    """Level 3 打开态 store：`W body1 store1 body2 W'`。

    body1 打开状态下（slice 已开、中心不归面）先把某个**当前已配组**用纯外层
    整体转存到该切片的 safe 槽（store1，`require_centers_solved=False`），使
    body2 不会拆散它，从而腾出装配自由度。最后关闭 W'，相对**原始**保护组
    事务原点做真实验收。
    """
    import time

    from .slice_band import band_for_open
    from .storage_planner import enumerate_store_paths

    db = body_db or _BodyDatabase.instance()
    limits = limits or BatchSearchLimits(max_bodies=max_bodies)

    protected = extract_paired_tredges(cube)
    original_count = paired_count(cube)
    # 原保护组的身份键（中棱 home + 两翼 home），用于区分「原始组」与「body1 新组成式组」。
    proto_ids = {(g.middle_piece_id, g.wing_piece_ids) for g in protected}
    close_of = lambda mv: mv[:-1] if mv.endswith("'") else mv + "'"

    t0 = time.time()
    checked = 0

    open_moves = ([m for m in db.open_moves if m in set(allowed_open_moves)]
                  if allowed_open_moves is not None else db.open_moves)
    for open_move in open_moves:
        band = band_for_open(open_move)
        close_move = close_of(open_move)
        bodies = [
            b for b in db.bodies_for(open_move)
            if (not limits.conservative_target_filter
                or _body_touches_unpaired(b, _unpaired_targets(cube)))
        ][:max_bodies_per_open]
        for body1 in bodies:
            if checked >= max_checked:
                break
            # 打开态下跑 body1
            mid = cube.clone()
            for mv in (open_move,) + tuple(body1.body_moves):
                mid.apply_move(mv)
            # 打开态下当前已配组（含 body1 新完成的）
            in_play = extract_paired_tredges(mid)
            # 新组成式组优先 = 正是 Level 3 想转出活动区的关系。
            in_play = sorted(
                in_play,
                key=lambda g: 0 if (g.middle_piece_id, g.wing_piece_ids) not in proto_ids else 1,
            )
            for group in in_play:
                if checked >= max_checked:
                    break
                n_store = 0
                for _dst, store_moves in enumerate_store_paths(
                    mid, group, band, max_store_depth, require_centers_solved=False
                ):
                    if n_store >= max_store_paths_per_group:
                        break
                    n_store += 1
                    st = mid.clone()
                    for mv in store_moves:
                        st.apply_move(mv)
                    for body2 in bodies:
                        if checked >= max_checked:
                            break
                        # 智能剪枝：body2 若不拆散刚存储的保护组才值得试。
                        b2_open = st.clone()
                        for mv in body2.body_moves:
                            b2_open.apply_move(mv)
                        if not is_tredge_group_paired(b2_open, group):
                            checked += 1
                            continue
                        checked += 1
                        w = b2_open.clone()
                        for mv in (close_move,):
                            w.apply_move(mv)
                        if is_successful_batch(cube, w, protected, min_gain=1):
                            full = ((open_move,) + tuple(body1.body_moves)
                                    + tuple(store_moves) + tuple(body2.body_moves)
                                    + (close_move,))
                            verify = cube.clone()
                            for mv in full:
                                verify.apply_move(mv)
                            v_alive = sum(1 for g in protected
                                          if is_tredge_group_paired(verify, g))
                            v_paired = paired_count(verify)
                            if (centers_are_color_solved(verify)
                                    and v_alive == len(protected)
                                    and v_paired >= original_count + 1):
                                return BatchPairingResult(
                                    success=True,
                                    moves=full,
                                    paired_before=original_count,
                                    paired_after=v_paired,
                                    net_gain=v_paired - original_count,
                                    protected_before=protected,
                                    protected_survived=tuple(
                                        g for g in protected
                                        if is_tredge_group_paired(verify, g)),
                                    protected_broken=tuple(
                                        g for g in protected
                                        if not is_tredge_group_paired(verify, g)),
                                    centers_solved_after=centers_are_color_solved(verify),
                                    replay_consistent=True,
                                    open_move=open_move,
                                    body_count=2,
                                    candidates_checked=checked,
                                    elapsed_seconds=time.time() - t0,
                                    message="inner_store_batch",
                                )

    return BatchPairingResult(
        success=False,
        moves=(),
        paired_before=original_count,
        paired_after=original_count,
        net_gain=0,
        protected_before=protected,
        protected_survived=(),
        protected_broken=protected,
        centers_solved_after=centers_are_color_solved(cube),
        replay_consistent=True,
        candidates_checked=checked,
        elapsed_seconds=time.time() - t0,
        error_code="NO_INNER_STORE_BATCH",
        message="no inner-store batch found within limits",
    )
