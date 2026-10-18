"""Solve virtual cubies, then visible centre orientations, and replay geometry."""
import time

from cube.conversion import cubies_to_facelets
from solver.result import SolveResult,SolveStage


def _side_centres(twists,cancelled):
    """Only the four side centres of Windmill/Fisher need orientation.

    Top/bottom square centres can absorb virtual parity and arbitrary quarter
    turns. Choose the shortest existing centre macro for any such endpoint,
    avoiding rejection of a valid input with invisible centre rotations.
    """
    from solver.mastermorphix import center_solution
    if all(twists[i]==0 for i in (1,2,4,5)):
        return []
    best=None
    for top in range(4):
        for bottom in range(4):
            if cancelled():
                raise InterruptedError()
            target=(top,twists[1],twists[2],bottom,twists[4],twists[5])
            if sum(target)%2:
                continue
            moves=center_solution(target)
            if best is None or len(moves)<len(best):
                best=moves
    return best


def solve_shape_cube(cube,cancel_event=None,progress_callback=None,optimize_budget=1.0):
    started=time.perf_counter()
    if cube.n == 4:
        from cube.high_shape import normalize_high_shape_input
        from solver.solver_n import solve_nxn
        cancelled=lambda:cancel_event is not None and cancel_event.is_set()
        try:
            work=normalize_high_shape_input(cube,cancelled)
        except ValueError as exc:
            return SolveResult(False,[],str(exc),int((time.perf_counter()-started)*1000),0,[])
        result=solve_nxn(work,cancel_event,progress_callback)
        if result.success:
            replay=cube.clone()
            for move in result.moves:
                if cancelled():
                    raise InterruptedError()
                replay.apply_move(move)
            if not replay.is_solved():
                return SolveResult(False,[],'shape.error.replay',int((time.perf_counter()-started)*1000),0,[])
        result.elapsed_ms=int((time.perf_counter()-started)*1000)
        return result
    baseline=_solve_shape_cube(cube,cancel_event,progress_callback)
    if not baseline.success or cube.n!=3 or cube.puzzle_kind=='pandora' or not baseline.moves:
        return baseline
    from solver.solver_n import _compress
    best=baseline
    deadline=time.perf_counter()+max(0,optimize_budget)
    # Distinct body solves expose distinct centre twists. Rank their complete
    # body+centre result, rather than choosing only the shortest cubie solve.
    for prefix in ((),('R',),('U',),('F',),("R'",),("U'",),("F'",)):
        if time.perf_counter()>=deadline:break
        if cancel_event is not None and cancel_event.is_set():raise InterruptedError()
        trial=cube.clone();trial.apply_moves(prefix)
        try:
            candidate=_solve_shape_cube(trial,cancel_event,None,max_length=18,timeout=.15)
        except InterruptedError:
            raise
        except Exception:
            continue
        if not candidate.success:continue
        moves=_compress(list(prefix)+candidate.moves,3)
        if len(moves)>=len(best.moves):continue
        replay=cube.clone();replay.apply_moves(moves)
        if replay.is_solved():
            best=SolveResult(True,moves,'',0,len(moves),
                             [SolveStage('shape.body_centres','shape.body_centres',moves)])
    if cancel_event is not None and cancel_event.is_set():raise InterruptedError()
    best.elapsed_ms=int((time.perf_counter()-started)*1000)
    return best


def _solve_shape_cube(cube,cancel_event=None,progress_callback=None,max_length=20,timeout=3.0):
    from solver.solver3 import solve_3x3
    from solver.mastermorphix import center_solution
    start=time.perf_counter()
    def cancelled():
        return cancel_event is not None and cancel_event.is_set()
    if cancelled():
        raise InterruptedError()
    if len({piece.home for piece in cube.cubies.values()})!=len(cube.positions):
        return SolveResult(False,[],'shape.error.duplicate',0,0,[])
    if cube.puzzle_kind in ('windmill','fisher') and cube.is_solved():
        return SolveResult(True,[],'',int((time.perf_counter()-start)*1000),0,[])
    if cube.puzzle_kind=='fisher':
        from cube.shape_cube import normalize_fisher
        cube=normalize_fisher(cube)
    if cube.n==2:
        from cube.cube3 import Cube3
        from cube.cubie_model import Cubie
        from cube.mastermorphix import placements,transform
        from solver.solver3 import verify_3x3
        work=Cube3.solved()
        for pos,piece in cube.cubies.items():
            work.cubies[pos]=Cubie(piece.home,pos,dict(piece.stickers))
        facelets=cubies_to_facelets(work.cubies,3)
        if not verify_3x3(facelets)[0]:
            # An odd corner permutation is valid on a 2x2. Virtual edges
            # can supply the matching parity without changing its corners.
            a,b=(1,1,0),(1,0,1)
            pa,pb=work.cubies[a],work.cubies[b]
            valid=False
            for fa in placements(pa.home,b):
                for fb in placements(pb.home,a):
                    work.cubies[b]=Cubie(pa.home,b,{transform(fa,n):c for n,c in pa.stickers.items()})
                    work.cubies[a]=Cubie(pb.home,a,{transform(fb,n):c for n,c in pb.stickers.items()})
                    facelets=cubies_to_facelets(work.cubies,3)
                    if verify_3x3(facelets)[0]:
                        valid=True
                        break
                if valid:
                    break
            if not valid:
                return SolveResult(False,[],'shape.error.replay',0,0,[])
        result=solve_3x3(facelets)
    else:
        result=solve_3x3(cubies_to_facelets(cube.cubies,3),max_length=max_length,timeout=timeout)
    if not result.success:
        return result
    if cancelled():
        raise InterruptedError()
    replay=cube.clone()
    replay.apply_moves(result.moves)
    try:
        # Pandora's square, single-colour centres have fourfold symmetry.
        # A quarter-turn of a centre is already visually restored.
        if cube.puzzle_kind in ('windmill','fisher'):
            turns=_side_centres(replay.center_twists(),cancelled)
        else:
            turns=center_solution(replay.center_twists()) if cube.n==3 and cube.puzzle_kind!='pandora' else ()
    except ValueError:
        return SolveResult(False,[],'shape.error.centres',0,0,[])
    replay.apply_moves(turns)
    if not replay.is_solved():
        return SolveResult(False,[],'shape.error.replay',0,0,[])
    moves=list(result.moves)+list(turns)
    stages=list(result.stages)
    if turns:
        stages.append(SolveStage('shape.centres','shape.centres',list(turns)))
    return SolveResult(True,moves,'',int((time.perf_counter()-start)*1000),len(moves),stages)
