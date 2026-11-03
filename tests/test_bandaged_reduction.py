"""Complete layout assets, manual reconstruction, global holding and replay."""
import pytest
from types import SimpleNamespace
from cube.bandaged_cube import BandagedCube
from cube.bandaged_entry import reconstruct,plates
from cube.conversion import cubies_to_facelets
from cube.appearance import ROTATIONS
from solver.bandaged_cube import solve_bandaged_cube
from solver.bandaged_reduction import geometry,assets,locate


@pytest.mark.parametrize('kind',('ai_cube','burr_cube'))
@pytest.mark.parametrize('seed',range(12))
@pytest.mark.parametrize('length',(40,100))
def test_reentered_deep_state_uses_no_witness(kind,seed,length):
    source=BandagedCube.random_scramble(kind,length,seed)
    source.apply_moves(('x','y','z')[:seed%4])
    data=cubies_to_facelets(source.cubies,4);seams={(p.face,p.cells) for p in plates(source)}
    cube=reconstruct(kind,data,seams)
    assert not cube.history
    word=solve_bandaged_cube(cube)
    assert not cube.history and cubies_to_facelets(cube.cubies,4)==data
    replay=cube.clone();replay.apply_moves(word);assert replay.is_solved()


@pytest.mark.parametrize('kind,count,edges',(('ai_cube',70,1278),('burr_cube',182070,1294884)))
def test_exhaustive_layout_counts_and_all_global_root_orientations(kind,count,edges):
    g=geometry(kind);header,blob,group=assets(kind)
    assert header['count']==group['exhaustive_layouts']==count
    assert header['edges']==group['verified_edges']==edges
    assert len(blob)==count*(header.get('key_bytes',14)+5)
    for frame in range(len(ROTATIONS)):
        state=bytes((u%8)*24+g.grid.aliases[u][frame] for u in range(len(g.grid.units)))
        assert locate(g.key(state),header,blob) is not None


@pytest.mark.parametrize('kind',('ai_cube','burr_cube'))
def test_asset_guard_and_mid_solve_cancel_preserve_input(monkeypatch,kind):
    import solver.bandaged_reduction as module
    source=BandagedCube.random_scramble(kind,40,7)
    data=cubies_to_facelets(source.cubies,4)
    cube=reconstruct(kind,data,{(p.face,p.cells) for p in plates(source)})
    calls=0
    def cancel():
        nonlocal calls
        calls+=1;return calls>40
    with pytest.raises(InterruptedError):solve_bandaged_cube(cube,cancel)
    assert not cube.history and cubies_to_facelets(cube.cubies,4)==data
    assets.cache_clear()
    with monkeypatch.context() as patch:
        patch.setattr(module,'geometry',lambda kind:SimpleNamespace(grid=SimpleNamespace(fingerprint='changed')))
        with pytest.raises(ValueError,match='bandage.search_table'):assets(kind)
    assets.cache_clear()
