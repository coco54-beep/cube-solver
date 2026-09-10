"""应用启动后台预热：预加载求解器惰性资源，消除「第一遍解特别慢」。

首解慢是因为首次调用才 import / 反序列化 / 构建预计算资源。桌面端实测：

- ``import solver3``（kociemba 两阶段表，~63MB）≈ 0.06s；
- ref5 宏库构建（``macro_lib``，约 10 万次 compute_effect）≈ 6.8s——**仅首次**，
  之后走 ``~/.cubesolver_cache/ref5`` 磁盘缓存（<0.1s）；
- 中心 setup 表（每个 BFS 约 12144 状态）≈ 1.75s × 常用 4 个 ≈ 7s；
- ref5 宏缓存 / 朝向掩码库 / 全空间 Dijkstra 均可忽略（< 0.05s）。

策略（启动开销按需分摊）：
- 通用资源（kociemba 两阶段表 + 2/3/4 阶求解器导入）在启动后台线程预热；
- 仅 5 阶用到的重资源（ref5 宏库 / 宏表 / 朝向掩码 / 中心 setup 表）改为**懒加载**：
  用户进入 5 阶录入页时才在后台线程构建，既能在他填色时完成，又不让只玩
  2/3/4 阶的用户白白承担冷启动开销与内存峰值。

任何异常都吞掉，绝不影响应用。
"""

import threading
import time

_common_started = False
_5x5_started = False
_lock = threading.Lock()


def warmup_solvers():
    """启动通用求解资源后台预热（幂等）。返回线程对象，便于测试等待。"""
    global _common_started
    with _lock:
        if _common_started:
            return None
        _common_started = True
    thread = threading.Thread(target=_run_common, name="solver-warmup", daemon=True)
    thread.start()
    return thread


def warmup_5x5():
    """按需预热 5 阶专属资源（幂等）。进入 5 阶录入页时调用。"""
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
