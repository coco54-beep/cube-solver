"""Prepared finite groups must not abort because a wall clock advanced."""
from itertools import count
import pytest


@pytest.mark.parametrize('kind',('circle_2','crazy_earth','ai_cube','burr_cube','cuboid_442','pentacle'))
def test_default_state_matching_has_no_automatic_time_cutoff(monkeypatch,kind):
    if kind.startswith(('circle_2','crazy_')):
        import solver.circle2_group as module
        from cube.circle_cube import Circle2Cube
        from cube.polyhedral import PolyhedralPuzzle
        from cube.polyhedral_scramble import scramble
        source=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
        scramble(source,24,37)
        cube=Circle2Cube(colors=list(source.colors)).entered() if kind=='circle_2' else PolyhedralPuzzle(kind,3,list(source.colors))
        function=module.solve_circle_group
    elif kind in ('ai_cube','burr_cube'):
        import solver.bandaged_reduction as module
        from cube.bandaged_cube import BandagedCube
        from cube.bandaged_entry import reconstruct,plates
        from cube.conversion import cubies_to_facelets
        source=BandagedCube.random_scramble(kind,40,37)
        cube=reconstruct(kind,cubies_to_facelets(source.cubies,4),{(p.face,p.cells) for p in plates(source)})
        function=module.solve_bandage_reduction
    elif kind=='cuboid_442':
        import solver.cuboid442 as module
        from cube.cuboid import CuboidCube
        from cube.polyhedral_scramble import scramble
        cube=CuboidCube.solved(kind);scramble(cube,24,37);cube.history=None
        function=module.solve_cuboid442
    else:
        import solver.pentacle_state as module
        from cube.pentacle import PentacleCube
        from cube.polyhedral import Move
        cube=PentacleCube();cube.apply_moves(cube.alignment_moves(0));cube.apply_move(Move(0,1,90));cube.history=[]
        function=module.solve_pentacle_state
    clock=count(1000.,1000.)
    monkeypatch.setattr(module,'monotonic',lambda:next(clock))
    word=function(cube)
    replay=cube.clone()
    for move in word:replay.apply_move(move)
    assert replay.is_solved()


def test_tangram_colour_coset_has_no_default_clock_limit(monkeypatch):
    import solver.tangram_table as module
    from tests.test_tangram_solver import scrambled
    table=module.load_table('tangram');cube=scrambled('tangram',37,30)
    clock=count(1000.,1000.);monkeypatch.setattr(module,'monotonic',lambda:next(clock))
    assert table.coloured_factors(table.element(cube.frames)) is not None
