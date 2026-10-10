"""Solve geometry-entered mirror states with their ordinary NxN mechanism."""
def solve_mirror(cube,cancel_event=None,progress_callback=None):
    from cube.conversion import cubies_to_facelets
    if cube.n==2:
        from solver.solver2 import solve_2x2_facelets
        result=solve_2x2_facelets(cubies_to_facelets(cube.cubies,2),cancel_event=cancel_event)
    elif cube.n==3:
        from solver.solver3 import solve_3x3
        result=solve_3x3(cubies_to_facelets(cube.cubies,3))
    else:
        from solver.solver_n import solve_nxn
        result=solve_nxn(cube,cancel_event=cancel_event,progress_callback=progress_callback)
    if result.success:
        replay=cube.clone()
        replay.apply_moves(result.moves)
        if not replay.is_solved():
            from solver.result import SolveResult
            return SolveResult(False,[],'Mirror geometry replay failed',result.elapsed_ms,0,[])
    return result
