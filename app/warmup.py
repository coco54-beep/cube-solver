"""Solver tables are loaded on demand, never during ordinary app startup.

An explicit desktop 5x5 entry may prewarm its own resources. Android keeps
that work deferred until solving. Startup does not load two-phase/4x4 tables.
"""

import os
import threading
import time

_common_started = False
_5x5_started = False
_lock = threading.Lock()


def warmup_solvers():
    """Startup is table-free on every platform; actual solve imports on demand."""
    return None


def warmup_5x5():
    """按需预热 5 阶专属资源（幂等）。进入 5 阶录入页时调用。"""
    if os.environ.get("ANDROID_PRIVATE"):
        return None
    global _5x5_started
    with _lock:
        if _5x5_started:
            return None
        _5x5_started = True
    thread = threading.Thread(target=_run_5x5, name="solver-warmup-5x5", daemon=True)
    thread.start()
    return thread


def _safe(fn):
    try:
        fn()
    except Exception:
        pass
    # 主动让出 GIL，尽量不阻塞 Kivy 主循环。
    time.sleep(0)


def _run_common():
    _safe(_warm_twophase)


def _run_5x5():
    _safe(_warm_solver5)
    _safe(_warm_ref5)
    _safe(_warm_center)


def _warm_solver5():
    """导入 5 阶求解入口（会加载 ref5 宏库，首次构建约 6.8s，之后走磁盘缓存）。"""
    import solver.solver5  # noqa: F401


def _warm_twophase():
    """导入即加载 kociemba 两阶段表，并预加载低阶求解器（供后续惰性导入复用）。"""
    import solver.solver3  # noqa: F401
    import solver.solver2  # noqa: F401
    import solver.solver4  # noqa: F401


def _warm_ref5():
    """加载 ref5 宏表、朝向掩码库并预建全空间 Dijkstra、生成元。"""
    from solver.reduction.ref5 import middle_orient_fix as mof
    from solver.reduction.ref5 import reduce5
    from solver.reduction.ref5 import terminal_solver as ts

    ts.build_all_macros()
    patterns = mof._load_patterns()
    if mof._SOLVE_PREV_SRC is not patterns:
        mof._SOLVE_PREV = mof._build_solve_prev(patterns)
        mof._SOLVE_PREV_SRC = patterns
    reduce5.generators()


def _warm_center():
    """构建中心 3-cycle setup 表（同色等价主路径 + 精确回退用到的基元）。"""
    from solver.center5 import primitives as P
    from solver.center5.setup_cache import get_setup_table

    for prim in (P.EDGE_COMM4, P.CORNER_MAIN, P.CORNER_BACKUP, P.EDGE_MAIN):
        get_setup_table(prim)
