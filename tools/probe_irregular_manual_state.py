"""Visible-input roundtrips and bounded solve probes for the remaining list."""
import json
import sys
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def run(kind,seed=20261023,length=24,seconds=30.):
    from cube.polyhedral_scramble import scramble
    from solver.polyhedral import solve_polyhedral
    started=monotonic()
    if kind.startswith(('crazy_','circle_2')):
        from cube.polyhedral import PolyhedralPuzzle
        from cube.circle_cube import Circle2Cube
        source=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
        scramble(source,length,seed)
        # Re-enter only painted panel colours. Anchor is inferred from those
        # observations by the same entered() path as the input screen.
        cube=(Circle2Cube(colors=list(source.colors)) if kind=='circle_2' else
              PolyhedralPuzzle(kind,3,list(source.colors))).entered()
        assert cube.colors==source.colors
        assert not getattr(cube,'circle_history',None)
    else:
        from cube.cuboid import CuboidCube
        from cube.cuboid_observation import SixViewDraft,project
        source=CuboidCube.solved(kind);scramble(source,length,seed)
        if kind=='camouflage_3':
            from tests.test_camouflage_six_view_entry import enter_visible_panels
            draft=enter_visible_panels(source)
        else:draft=SixViewDraft.from_cube(source)
        state=json.loads(json.dumps(draft.state()))
        # View-local plate IDs describe seam continuity, not source identities.
        result=SixViewDraft(kind,state).match(seconds=10.)
        if result.status!='ok':raise ValueError('entry.'+result.status)
        cube=result.cube
        assert cube.history is None
        def visible(c):return tuple(tuple((colour,depth) for colour,owner,depth in v) for v in project(c,draft.model))
        assert visible(cube)==visible(source)
    matched=monotonic()
    try:
        moves=solve_polyhedral(cube,lambda:monotonic()-matched>seconds)
        work=cube.clone()
        for move in moves:work.apply_move(move)
        assert work.is_solved()
        row=dict(kind=kind,seed=seed,scramble_turns=length,entry_matches=True,history_empty=True,
                 success=True,moves=len(moves),seconds=round(monotonic()-matched,3),replay_solved=True)
    except (ValueError,InterruptedError,TimeoutError) as exc:
        row=dict(kind=kind,seed=seed,scramble_turns=length,entry_matches=True,history_empty=True,
                 success=False,seconds=round(monotonic()-matched,3),message=str(exc) or type(exc).__name__)
    print('IRREGULAR_MANUAL_RESULT '+json.dumps(row),flush=True)
    return row


if __name__=='__main__':run(sys.argv[1],seconds=float(sys.argv[2]) if len(sys.argv)>2 else 30.)
