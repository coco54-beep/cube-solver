"""5x5 活动中心 3-cycle 的 setup 缓存。

每个基元（其支撑三元组）只需做一次 BFS，即可覆盖该轨道全部有序三重
（24×23×22 = 12144 个状态，三重传递性保证全部可达）。后续每次共轭仅需查表
并回溯父指针得到最短 setup，再拼出 S' P S。

缓存键必须包含会影响结果的全部要素：
    CACHE_VERSION
    基元支撑三元组（expected_cycle）
    生成元列表（合法动作）
    置换复合方向约定（正向 3-cycle）
任一项改变即应失效（见 cache_key_of）。第一版为内存缓存；若启动明显变慢，
再引入版本化磁盘缓存（solver/center5/data/）。
"""

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import os
import pickle
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .legal_moves import (
    LEGAL_5X5_CENTER_MOVES,
    invert_move_string,
    is_legal_5x5_solver_move,
)
from .orbits import CenterOrbitKind, apply_to_pos
from .primitives import CENTER_INDEX, CENTER_ORDER, CenterPrimitive

# 影响 setup 结果的全部要素组合，用于缓存键。
CACHE_VERSION = 1
_PERMUTATION_CONVENTION = "pos_to_home_forward_3cycle"

# generator 集合：全部合法动作（外层 + 两层宽转 × "", "'", "2"）。
_LEGAL: Tuple[str, ...] = tuple(
    m for m in LEGAL_5X5_CENTER_MOVES if is_legal_5x5_solver_move(m)
)

# 版本化磁盘缓存：首次 BFS 后落盘，之后启动直接反序列化（每个 ~0.4MB）。
_CACHE_SUBDIR = "center5_setup"

Coord = Tuple[int, int, int]
TripState = Tuple[Coord, Coord, Coord]  # 三个 marker 的当前坐标


@dataclass(frozen=True)
class SetupTable:
    """对某基元做一次 BFS 得到的完整 setup 查表结构。"""

    primitive: CenterPrimitive
    start: TripState
    parent: Mapping[TripState, Optional[Tuple[TripState, str]]]

    def size(self) -> int:
        return len(self.parent)


# ---------------------------------------------------------------------------
# 缓存统计
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SetupCacheStats:
    builds: int
    hits: int
    disk_hits: int = 0


_STATS: Dict[str, int] = {"builds": 0, "hits": 0, "disk_hits": 0}


def setup_cache_stats() -> SetupCacheStats:
    return SetupCacheStats(builds=_STATS["builds"], hits=_STATS["hits"],
                           disk_hits=_STATS["disk_hits"])


def clear_setup_cache() -> None:
    get_setup_table.cache_clear()
    _STATS["builds"] = 0
    _STATS["hits"] = 0
    _STATS["disk_hits"] = 0
    directory = _disk_cache_dir()
    if directory is not None:
        for name in os.listdir(directory):
            if name.endswith(".pkl"):
                try:
                    os.remove(os.path.join(directory, name))
                except OSError:
                    pass


def cache_key_of(primitive: CenterPrimitive) -> str:
    """计算缓存键哈希；任一影响要素改变即自动失效。"""
    payload = repr((
        CACHE_VERSION,
        tuple(primitive.expected_cycle),
        _LEGAL,
        _PERMUTATION_CONVENTION,
    ))
    return sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 版本化磁盘缓存（安卓写入应用私有目录，桌面写入 ~）
# ---------------------------------------------------------------------------

def _disk_cache_dir() -> Optional[str]:
    """返回可写的缓存目录（不存在则创建）；无可用目录返回 None。"""
    bases: List[str] = []
    for var in ("ANDROID_PRIVATE", "ANDROID_APP_PATH"):
        value = os.environ.get(var)
        if value:
            bases.append(value)
    bases.append(os.path.expanduser("~"))
    for base in bases:
        try:
            if not base or not os.path.isdir(base):
                continue
            directory = os.path.join(base, ".cubesolver_cache", _CACHE_SUBDIR)
            os.makedirs(directory, exist_ok=True)
            return directory
        except OSError:
            continue
    return None


def _disk_path(primitive: CenterPrimitive) -> Optional[str]:
    directory = _disk_cache_dir()
    if directory is None:
        return None
    return os.path.join(directory, cache_key_of(primitive) + ".pkl")


# ---------------------------------------------------------------------------
# BFS 构建
# ---------------------------------------------------------------------------

def _support_state(primitive: CenterPrimitive) -> TripState:
    return tuple(CENTER_ORDER[i] for i in primitive.expected_cycle)  # type: ignore


def build_setup_table(
    primitive: CenterPrimitive,
    max_states: int = 200000,
) -> SetupTable:
    """以基元支撑三元组为起点 BFS，得到覆盖该轨道全部可达三重的查表。"""
    start = _support_state(primitive)
    parent: Dict[TripState, Optional[Tuple[TripState, str]]] = {start: None}
    dq = deque([start])
    while dq:
        st = dq.popleft()
        if len(parent) >= max_states:
            break
        for m in _LEGAL:
            ns = tuple(apply_to_pos(p, m, 5) for p in st)
            if ns not in parent:
                parent[ns] = (st, m)
                dq.append(ns)
    return SetupTable(primitive=primitive, start=start, parent=parent)


@lru_cache(maxsize=None)
def get_setup_table(primitive: CenterPrimitive) -> SetupTable:
    """按基元取 setup 表：内存 → 磁盘 → BFS 构建（构建后落盘）。"""
    key = cache_key_of(primitive)
    path = _disk_path(primitive)
    if path is not None:
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            if data.get("version") == CACHE_VERSION and data.get("key") == key:
                _STATS["disk_hits"] += 1
                return data["table"]
        except Exception:
            pass
    _STATS["builds"] += 1
    table = build_setup_table(primitive)
    if path is not None:
        try:
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump({"version": CACHE_VERSION, "key": key, "table": table},
                            f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, path)
        except Exception:
            pass
    return table


# ---------------------------------------------------------------------------
# 查表回溯与共轭实例化
# ---------------------------------------------------------------------------

def reconstruct_setup(
    table: SetupTable,
    target_state: TripState,
) -> Tuple[str, ...]:
    """从 target_state 向上回溯父指针得到 start -> target 的最短 setup。"""
    if target_state not in table.parent:
        raise ValueError(
            "%s 的目标三重 %s 不可达" % (table.primitive.name, target_state)
        )
    path: List[str] = []
    cur = target_state
    while table.parent[cur] is not None:
        pstate, m = table.parent[cur]  # type: ignore
        path.append(m)
        cur = pstate
    return tuple(reversed(path))


def _target_state(primitive: CenterPrimitive, target_ids: Sequence[int]) -> TripState:
    return tuple(CENTER_ORDER[i] for i in target_ids)  # type: ignore


def instantiate_center_3cycle(
    primitive: CenterPrimitive,
    target_ids: Sequence[int],
    table: Optional[SetupTable] = None,
) -> List[str]:
    """用缓存表作用出目标三重 (x,y,z) 的合法动作序列 S' P S。

    target_ids 是目标中心在 CENTER_ORDER 中的全局下标（与 conjugate_cycle 一致）。
    传入 table 可复用查表；否则自动按基元取缓存表。
    """
    if table is None:
        _STATS["hits"] += 1
        table = get_setup_table(primitive)
    else:
        _STATS["hits"] += 1
    setup = reconstruct_setup(table, _target_state(primitive, target_ids))
    moves: List[str] = []
    for m in reversed(setup):
        moves.append(invert_move_string(m))
    moves.extend(primitive.moves)
    moves.extend(setup)
    return moves
