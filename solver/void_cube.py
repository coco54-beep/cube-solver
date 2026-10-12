"""Solve colour-entered Void Cubes, including missing-centre parity.

No scramble history is consulted. Choose a legal virtual centre frame before
calling the bundled two-phase bridge, then replay on the centreless model.
"""
from cube.coordinates import pos_from_rc
from cube.polyhedral import Move, key
from solver.polyhedral import _body_frames, _transform, identify


def solve_void_cube(cube,cancel=None,progress=None):
    from solver.solver3 import solve_3x3, _tface, _tcubie, _build_cubestring
    identify(cube)
    g=cube.geometry
    names=('U','R','F','D','L','B')
    slots={(tuple(round(v*1.5) for v in g.centres[s.piece]),s.face):i
           for i,s in enumerate(g.stickers)}
    face_index={key(normal):i for i,normal in enumerate(g.spec.normals)}
    for stage,frame in enumerate(_body_frames('void_cube',3)):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage,24)
        centres=tuple(face_index[key(_transform(frame,normal))] for normal in g.spec.normals)
        grids={name:[[centres[face] if r==c==1 else
                      cube.colors[slots[(pos_from_rc(3,name,r,c),face)]]
                      for c in range(3)] for r in range(3)] for face,name in enumerate(names)}
        state=_tface.FaceCube()
        state.from_string(_build_cubestring(grids))
        if state.to_cubie_cube().verify()!=_tcubie.CUBE_OK:
            continue
        result=solve_3x3(grids)
        if cancel and cancel():
            raise InterruptedError()
        if not result.success:
            raise ValueError(result.message)
        word=tuple(Move(names.index(token[0]),0,(-(
                   2 if token.endswith('2') else 3 if token.endswith("'") else 1))%4)
                   for token in result.moves)
        replay=cube.entered()
        for move in word:
            replay.apply_move(move)
        if not replay.is_solved():
            raise ValueError('Void Cube solution replay failed')
        return word
    raise ValueError('The entered puzzle is not a legal state')
