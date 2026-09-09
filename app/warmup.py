"""应用启动后台预热：预加载求解器惰性资源，消除「第一遍解特别慢」。

首解慢是因为首次调用才 import / 反序列化 / 构建预计算资源。桌面端实测：

- ``import solver3``（kociemba 两阶段表，~63MB）≈ 6.9s；
- 中心 setup 表（每个 BFS 约 12144 状态）≈ 1.75s × 常用 4 个 ≈ 7s；
- ref5 宏缓存 / 朝向掩码库 / 全空间 Dijkstra 均可忽略（< 0.05s）。

这里在守护线程里按依赖顺序预热上述资源，任何异常都吞掉，绝不影响应用。
"""

import threading
import time

_started = False
_started_lock = threading.Lock()


def warmup_solvers():
    """启动后台预热线程（幂等）。返回线程对象，便于测试等待。"""
    global _started
    with _started_lock:
        if _started:
            return None
        _started = True
    thread = threading.Thread(target=_run, name="solver-warmup", daemon=True)
    thread.start()
    return thread


def _safe(fn):
    try:
        fn()
    except Exception:
        pass
    # 主动让出 GIL，尽量不阻塞 Kivy 主循环。
    time.sleep(0)


def _run():
    _safe(_warm_twophase)
    _safe(_warm_ref5)
    _safe(_warm_center)


def _warm_twophase():
    """导入即加载 kociemba 两阶段表（3x3/4x4/5x5 降阶 3x3 共用）。"""
    import solver.solver3  # noqa: F401


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
