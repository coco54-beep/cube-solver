"""Resolve invisible labels, solve the eight corners, replay the white shell."""
def solve_blanker(cube,cancel_event=None,progress_callback=None):
    from cube.blanker import normalize_entry,core3
    from cube.mastermorphix import MorphixInputError
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import verify_3x3,solve_3x3
    from solver.result import SolveResult
    if cancel_event and cancel_event.is_set():raise InterruptedError()
    try:work=normalize_entry(cube)
    except MorphixInputError as exc:return SolveResult(False,[],f'morphix.error.{exc}',0,0,[])
    if cube.is_solved():return SolveResult(True,[],'',0,0,[])
    full=core3(work);facelets=cubies_to_facelets(full.cubies,3)
    if not verify_3x3(facelets)[0]:
        # A 2x2 has no edge parity restriction. Two virtual edges compensate
        # for odd corner permutation without altering any entered corner.
        a,b=full.cubies[(1,1,0)],full.cubies[(0,1,1)]
        a.stickers[(1,0,0)],b.stickers[(0,0,1)]=b.stickers[(0,0,1)],a.stickers[(1,0,0)]
        facelets=cubies_to_facelets(full.cubies,3)
    result=solve_3x3(facelets)
    if cancel_event and cancel_event.is_set():raise InterruptedError()
    if result.success:
        replay=cube.clone();replay.apply_moves(result.moves)
        if not replay.is_solved():return SolveResult(False,[],'Blanker shape replay failed',result.elapsed_ms,0,[])
    return result
