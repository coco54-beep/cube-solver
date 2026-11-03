"""Reference exchanges must separate the old colour pairs and solve from state alone."""
import json
from collections import Counter
import pytest
from cube.twins_pcubes import TwinsPCubesState,fingerprint,data
from cube.twins_pcubes_aligned import generators,geometry,scrambled,observed_colors
from cube.polyhedral import Move
from app.session import encode,decode


def old_colour_pairs():
    """Find the old regular subgroup's singleton equivariances independently."""
    g=geometry();actions=[p for p,w in generators()[:20]];left=set(range(192));orbits=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for s in queue:
            for p in actions:
                if p[s] not in orbit:orbit.add(p[s]);queue.append(p[s])
        orbits.append(sorted(orbit));left-=orbit
    representatives=[];pairs=[]
    for orbit in orbits:
        if not all(len(g.pieces[g.stickers[s].piece])==1 for s in orbit):continue
        hit=None
        for rep in representatives:
            for target in orbit:
                mapping={rep[0]:target};queue=[rep[0]];valid=True
                for s in queue:
                    if g.stickers[s].face!=g.stickers[mapping[s]].face:valid=False;break
                    for p in actions:
                        a,b=p[s],p[mapping[s]]
                        if a in mapping and mapping[a]!=b:valid=False;break
                        if a not in mapping:mapping[a]=b;queue.append(a)
                    if not valid:break
                if valid and set(mapping.values())==set(orbit):hit=mapping;break
            if hit is not None:break
        if hit is None:representatives.append(orbit)
        else:pairs.extend(hit.items())
    return pairs


def test_source_inventory_is_192_coloured_fields_and_unpainted_inner_body():
    c=TwinsPCubesState()
    assert len(c.solids)==166 and len(c.panels)==192
    assert Counter(f for h,f,p in c.panels)=={f:32 for f in range(6)}
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:120,2:24,3:8}
    assert data()['source']==fingerprint()
    assert {len(w) for p,w in generators()}=={1,7,9}


def test_both_exchange_families_replay_all_material_and_preserve_inverse():
    root=TwinsPCubesState();before=root.signature()
    for action,word in generators()[20:]:
        work=root.clone().apply_moves(word)
        assert work.aligned_permutation()==action
        work.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)))
        assert work.signature()==before


def test_all_48_old_colour_pairs_can_actually_separate():
    pairs=old_colour_pairs();assert len(pairs)==48
    # All pairs, including the inner/outer radial-looking panels, acquire
    # different actual colours under the certified 7/9-step families.
    results=[observed_colors(TwinsPCubesState().apply_moves(w)) for p,w in generators()[20:]]
    assert all(any(colors[a]!=colors[b] for colors in results) for a,b in pairs)
    for seed in range(6):
        colors=observed_colors(scrambled(seed,30,jumble=False))
        assert sum(colors[a]!=colors[b] for a,b in pairs)>=20


@pytest.mark.parametrize('seed',(0,1,5,11,19,21,22,38,40,45,50,54))
def test_scramble_mixes_both_parts_of_every_flower_instead_of_only_the_total_pairs(seed):
    from cube.twins_pcubes_aligned import flower_pairs,flower_quality
    c=scrambled(seed,30,jumble=False);colors=observed_colors(c)
    assert len(flower_pairs())==6 and all(len(face)==4 for face in flower_pairs())
    for different,inner_colours,outer_colours in flower_quality(colors):
        assert different>=2 and inner_colours>=2 and outer_colours>=2


@pytest.mark.parametrize('seed',range(6))
@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('shape',(False,True))
def test_deep_scrambles_reenter_without_history_and_guarded_solution_replays(seed,length,shape):
    from solver.twins_pcubes import solve
    source=scrambled(seed,length,jumble=shape)
    if shape:
        c=decode(json.loads(json.dumps(encode(source))))
        c=TwinsPCubesState.from_observation(json.loads(json.dumps(c.observation_data())))
    else:
        # Throw away poses too: a true face-colour-only reentry in the
        # canonical shell, rather than a disguised inverse scramble.
        c=TwinsPCubesState(paints=observed_colors(source))
    assert not hasattr(c,'history')
    before=c.signature();word=solve(c,seconds=30.)
    assert c.clone().apply_moves(word).is_solved()
    assert c.signature()==before


def test_checkpoint_fingerprint_and_bad_shape_are_rejected_without_mutation():
    c=scrambled(9,30);record=encode(c);record['v']['geometry_fingerprint']='old-drawing3'
    with pytest.raises(ValueError,match='twins.legacy_entry'):decode(record)
    c=TwinsPCubesState();before=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(Move(0,0,90.))
    assert c.signature()==before
    from solver.twins_pcubes import solve
    with pytest.raises(InterruptedError):solve(c,cancel=lambda:True)
    assert c.signature()==before


def test_public_factory_and_renderer_use_reference_without_manual_entry():
    from types import SimpleNamespace
    from app.application import CubeApp
    from renderer.twins_view import TwinsView,TwinsTwistView
    from ui.screens.polyhedral_screen import _view_for
    from ui.screens.twins_screen import TwinsInputScreen
    app=SimpleNamespace();CubeApp.new_twins(app)
    assert isinstance(app.cube,TwinsPCubesState)
    assert _view_for(app.cube) is TwinsView and _view_for(app.cube,True) is TwinsTwistView
    assert isinstance(TwinsInputScreen.make_scrambled(seed=1,length=4),TwinsPCubesState)
    view=SimpleNamespace(home_surfaces=TwinsView.home_surfaces,piece_filter=None)
    fields={row[3] for row in TwinsView._surfaces(view,app.cube) if row[3] is not None}
    assert fields==set(range(192))


def test_old_saved_cad_page_generates_reference_instead_of_the_old_paired_scramble(monkeypatch):
    from kivy.app import App
    from types import SimpleNamespace
    from cube.twins_state import TwinsState
    from ui.screens.twins_screen import TwinsInputScreen
    old=TwinsState();app=SimpleNamespace(cube=old)
    monkeypatch.setattr(App,'get_running_app',staticmethod(lambda:app))
    result=TwinsInputScreen.make_scrambled(seed=3,length=3)
    assert isinstance(result,TwinsPCubesState)
    assert len(old.frames)==190 and len(result.frames)==166
    app.cube=TwinsPCubesState()
    assert isinstance(TwinsInputScreen.make_scrambled(seed=3,length=3),TwinsPCubesState)


def test_background_solve_service_uses_reference_solver_and_replays_without_history():
    from services.solve_service import SolveService
    from threading import Event
    cube=decode(json.loads(json.dumps(encode(scrambled(17,30)))))
    before=cube.signature();done=Event();results=[]
    def complete(result):results.append(result);done.set()
    service=SolveService();service.start(cube,complete)
    assert done.wait(30.)
    assert results[0].success,results[0].message
    assert cube.clone().apply_moves(results[0].moves).is_solved()
    assert cube.signature()==before
