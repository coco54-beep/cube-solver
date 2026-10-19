"""Solve the oriented Skewb mechanism, then close the Ghost Pyramid shell."""
from cube.mastermorphix import IDENTITY
from cube.mirror_tower import frame_key
from cube.polyhedral import Move


def solve_ghost_pyramid(cube,cancel=None,progress=None):
    if cancel and cancel(): raise InterruptedError()
    cube.labeled_state()
    if cube.is_solved(): return ()
    work=cube.clone()
    solution=[]
    if abs(work.phase)>1e-8:
        move=work.alignment_move()
        work.apply_move(move)
        solution.append(move)
    from solver.polyhedral import solve_polyhedral
    from solver.fisher_skewb import prepared
    from solver.lattice_data import geometry_key
    word=solve_polyhedral(work.ordinary_state(),cancel,progress)
    for move in word:
        if cancel and cancel(): raise InterruptedError()
        work.apply_move(move)
    solution.extend(word)
    record=prepared()
    if record['geometry']!=geometry_key(work.geometry):
        raise ValueError('Ghost Pyramid formulas do not match its mechanism')
    mask=0
    for bit,home in enumerate(record['homes']):
        piece=work.pieces[home]
        if piece.home!=home: raise ValueError('Ghost Pyramid centre is misplaced')
        if frame_key(piece.frame)!=frame_key(IDENTITY): mask|=1<<bit
    atoms=record['finishers'].get(str(mask))
    if atoms is None: raise ValueError('Ghost Pyramid centre directions are not reachable')
    finish=tuple(Move(*atom) for atom in atoms)
    for move in finish:
        if cancel and cancel(): raise InterruptedError()
        work.apply_move(move)
    solution.extend(finish)
    move=work.alignment_move(close=True)
    work.apply_move(move)
    solution.append(move)
    if not work.is_solved(): raise ValueError('Ghost Pyramid solution replay failed')
    return tuple(solution)
