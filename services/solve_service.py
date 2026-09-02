"""求解服务：在后台线程调用 3x3/4x4 求解器，支持取消与进度回调。

UI 线程通过 Clock.schedule_once 把后台进度/结果送回调；本服务自身不依赖
Kivy，便于在安卓后台线程复用。
"""

import threading
from typing import Callable, List, Optional


class CancelToken:
    """线程安全取消标记（行为与 threading.Event 一致）。

    .is_set() 为方法（与 threading.Event 相同），便于直接传给求解器。
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()


class SolveService:
    """在后台线程运行 solve_4x4 / solve_3x3。"""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._cancel = CancelToken()
        self._pending = None  # 存放 (cancel_token) 以便取消

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        cube,
        on_done: Callable,
        on_progress: Optional[Callable] = None,
    ):
        """启动求解。on_done(result)、on_progress(dict) 在后台线程调用。

        调用方需用 Clock 把结果切回 UI 线程。
        """
        self._cancel = CancelToken()
        self._thread = threading.Thread(
            target=self._run,
            args=(cube, on_done, on_progress, self._cancel),
            daemon=True,
        )
        self._thread.start()

    def _run(self, cube, on_done, on_progress, cancel):
        from cube.cube3 import Cube3
        from solver.solver3 import solve_3x3
        from solver.solver4 import solve_4x4

        def cb(payload):
            if on_progress is not None:
                try:
                    on_progress(payload)
                except Exception:
                    pass

        try:
            if isinstance(cube, Cube3):
                # 3x3: 用 facelets 路径，复用 solver3
                from cube.conversion import cubies_to_facelets
                facelets = cubies_to_facelets(cube.cubies, 3)
                result = solve_3x3(facelets)
            else:
                result = solve_4x4(
                    cube,
                    cancel_event=cancel,
                    progress_callback=cb,
                )
        except Exception as exc:  # 求解失败/取消
            result = _make_failure(exc)
        on_done(result)

    def cancel(self):
        self._cancel.cancel()


def _make_failure(exc: Exception):
    from solver.result import SolveResult
    msg = str(exc) or exc.__class__.__name__
    return SolveResult(False, [], msg, 0, 0, [])
