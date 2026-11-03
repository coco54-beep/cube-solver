"""求解服务：在后台线程调用 3x3/4x4 求解器，支持取消与进度回调。

UI 线程通过 Clock.schedule_once 把后台进度/结果送回调；本服务自身不依赖
Kivy，便于在安卓后台线程复用。
"""

from cube.cuboid import CUBOID_PREFIXES
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
        self.cancel()
        self._cancel = CancelToken()
        self._thread = threading.Thread(
            target=self._run,
            args=(cube, on_done, on_progress, self._cancel),
            daemon=True,
        )
        self._thread.start()

    def _run(self, cube, on_done, on_progress, cancel):
        from solver.search_resume import reporting
        def report(payload):
            if on_progress is not None and not cancel.is_set():
                try:on_progress(payload)
                except Exception:pass
        with reporting(report):self._execute(cube,on_done,on_progress,cancel)

    def _execute(self, cube, on_done, on_progress, cancel):
        def cb(payload):
            if on_progress is not None and not cancel.is_set():
                try:
                    on_progress(payload)
                except Exception:
                    pass

        def physical_progress(done,total):
            cb({'label':'solver.continuing','progress':0.} if done<0 else {'done':done,'total':total})

        try:
            from services.solution_cache import lookup
            cached=lookup(cube,cancel.is_set) if not cancel.is_set() else _make_failure(InterruptedError())
        except InterruptedError:cached=_make_failure(InterruptedError())
        except Exception:cached=None  # Optional caching must not block a fresh solve.
        if cached is not None:
            if cancel.is_set():cached=_make_failure(InterruptedError())
            else:cb({'label':'entry.cached_solution','progress':1.,'cache_hit':True})
            on_done(cached);return

        try:
            if cancel.is_set():
                raise InterruptedError()
            from cube.cube2 import Cube2
            from cube.cube3 import Cube3
            from cube.cube5 import Cube5
            from cube.bandaged_cube import BandagedCube
            from cube.polyhedral import PolyhedralPuzzle
            if hasattr(cube,'frames') and cube.puzzle_kind in ('helicopter','helicopter_14','rua','clover','mf8_bauhinia_minx'):
                from solver.edge_jumbling import solve
                from solver.result import SolveResult
                moves=solve(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',0,len(moves),[])
            elif getattr(cube,'puzzle_kind',None) in ('mf8_twins','mf8_suncube_2','lanlan_pisces','lanlan_hexagram','lanlan_clover_pyraminx','lanlan_flower_copter','lanlan_butterflower','lanlan_master_clover'):
                from time import perf_counter
                if cube.puzzle_kind=='mf8_twins':
                    if getattr(cube,'geometry_profile',None)=='pcubes-skewby-twins-v1':from solver.twins_pcubes import solve
                    else:from solver.twins import solve
                elif cube.puzzle_kind=='lanlan_pisces':from solver.pisces import solve
                elif cube.puzzle_kind=='lanlan_flower_copter':from solver.flower_copter import solve
                elif cube.puzzle_kind=='lanlan_butterflower':from solver.butterflower import solve
                elif cube.puzzle_kind=='lanlan_master_clover':from solver.master_clover import solve
                elif cube.puzzle_kind=='lanlan_hexagram':from solver.hexagram import solve
                elif cube.puzzle_kind=='lanlan_clover_pyraminx':from solver.clover_pyraminx import solve
                else:from solver.suncube import solve
                from solver.result import SolveResult
                started=perf_counter();prepared=None
                if cube.puzzle_kind=='lanlan_butterflower':
                    if any(c<0 for c in cube.paints):raise ValueError('Please enter every sticker')
                    from solver.butterflower import prepare_observation
                    prepared=prepare_observation(cube,cancel.is_set)
                    moves=solve(prepared,cancel.is_set,physical_progress,max(.001,60.-(perf_counter()-started)))
                else:moves=solve(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
                result.prepared_cube=prepared
            elif getattr(cube,'puzzle_kind',None)=='lanlan_comet_physical':
                from time import perf_counter
                from solver.lanlan_comet import solve
                from solver.result import SolveResult
                started=perf_counter();moves=solve(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind',None)=='planar_rhombic_12':
                from time import perf_counter
                from solver.crazy_comet import solve
                from solver.result import SolveResult
                started=perf_counter();moves=solve(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind',None)=='lanlan_curvy_copter':
                from time import perf_counter
                from solver.curvy_copter import solve
                from solver.result import SolveResult
                started=perf_counter();moves=solve(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind','').startswith('mixup_'):
                from solver.mixup import solve_mixup
                result=solve_mixup(cube,cancel.is_set,cb)
            elif getattr(cube,'rigid_family',False):
                from time import perf_counter
                from solver.articulated import solve_articulated
                from solver.result import SolveResult
                started=perf_counter()
                moves=solve_articulated(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif isinstance(cube,PolyhedralPuzzle) or getattr(cube,'puzzle_kind','').startswith(CUBOID_PREFIXES) or getattr(cube,'puzzle_kind',None) in ('mirror_tower','mirror_pyraminx','mirror_skewb','fisher_skewb','container','mirror_kilominx','mirror_megaminx','ghost_pyramid'):
                from time import perf_counter
                from solver.polyhedral import solve_polyhedral
                from solver.result import SolveResult
                started=perf_counter()
                moves=solve_polyhedral(cube,cancel.is_set,physical_progress)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind',None) in ('square0','square2','super_square1'):
                from time import perf_counter
                from solver.square_family import solve_square_family
                from solver.result import SolveResult
                started=perf_counter()
                moves=solve_square_family(cube,cancel.is_set,
                                          lambda done,total:cb({'done':done,'total':total}))
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind',None)=='square1':
                from time import perf_counter
                from solver.square1 import solve_square1
                from solver.result import SolveResult
                started=perf_counter()
                moves=solve_square1(cube,cancel.is_set,
                                    lambda done,total:cb({'done':done,'total':total}))
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif getattr(cube,'puzzle_kind',None) == 'ghost':
                from solver.ghost import solve_ghost
                result=solve_ghost(cube,cancel_event=cancel,progress_callback=cb)
            elif getattr(cube,'puzzle_kind',None) in ('axis','pandora','windmill','fisher','trajber','trajber_4','dodecahedron_2','dodecahedron_3',
                                                   'rhombic_3','rhombic_4','rhombic_mask_4','caneball_4'):
                from solver.shape_cube import solve_shape_cube
                result=solve_shape_cube(cube,cancel_event=cancel,progress_callback=cb)
            elif getattr(cube,'puzzle_kind',None)=='blanker':
                from solver.blanker import solve_blanker
                result=solve_blanker(cube,cancel_event=cancel,progress_callback=cb)
            elif getattr(cube, 'puzzle_kind', None) in ('mirror','mirror_windmill','mirror_axis','mirror_fisher',
                                                                      'mirror_windmill_unequal','mirror_fisher_unequal',
                                                                      'mirror_windmill_offset','mirror_fisher_offset'):
                from solver.mirror import solve_mirror
                result = solve_mirror(cube, cancel_event=cancel, progress_callback=cb)
            elif getattr(cube, "puzzle_kind", None) == "mastermorphix":
                from solver.mastermorphix import solve_mastermorphix
                result = solve_mastermorphix(cube, cancel_event=cancel, progress_callback=cb)
            elif isinstance(cube, BandagedCube):
                from solver.bandaged_cube import solve_bandaged_cube
                from solver.result import SolveResult
                from time import perf_counter
                started=perf_counter()
                moves=solve_bandaged_cube(cube, cancel.is_set)
                result=SolveResult(True,list(moves),'',int((perf_counter()-started)*1000),len(moves),[])
            elif isinstance(cube, Cube2):
                from solver.solver2 import solve_2x2
                result = solve_2x2(cube, cancel_event=cancel, progress_callback=cb)
            elif isinstance(cube, Cube3):
                from solver.solver3 import solve_3x3
                # 3x3: 用 facelets 路径，复用 solver3
                from cube.conversion import cubies_to_facelets
                facelets = cubies_to_facelets(cube.cubies, 3)
                result = solve_3x3(facelets)
            elif isinstance(cube, Cube5):
                from solver.solver5 import solve_5x5
                result = solve_5x5(cube, cancel_event=cancel, progress_callback=cb)
            elif cube.n >= 6:
                from solver.solver_n import solve_nxn
                result = solve_nxn(cube, cancel_event=cancel, progress_callback=cb)
            else:
                from solver.solver4 import solve_4x4
                result = solve_4x4(
                    cube,
                    cancel_event=cancel,
                    progress_callback=cb,
                )
        except Exception as exc:  # 求解失败/取消
            result = _make_failure(exc)
        if result.success:
            try:
                from services.solution_cache import remember
                remember(cube,result,cancel.is_set)
            except InterruptedError:result=_make_failure(InterruptedError('Cancelled'))
            except Exception:pass
        if cancel.is_set():result=_make_failure(InterruptedError('Cancelled'))
        if not result.success and not result.failure_category:
            from services.failures import classify
            result.failure_category='cancelled' if result.failure_kind=='cancelled' else classify(result.message)
        on_done(result)

    def cancel(self):
        self._cancel.cancel()


def _make_failure(exc: Exception):
    from solver.result import SolveResult
    from services.failures import classify
    msg = str(exc) or exc.__class__.__name__
    return SolveResult(False, [], msg, 0, 0, [],'cancelled' if isinstance(exc,InterruptedError) else 'solver',
                       classify(msg,exception=exc),list(getattr(exc,'locations',()) or ()))
