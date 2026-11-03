"""Independent geometry, observation, colour-group and production routing."""
from collections import Counter
import json
import pytest
from cube.twins_state import TwinsState
from cube.suncube import SunCube
from cube.polyhedral import Move,key
from cube.crazy_comet import vertices,volume

PROFILES=(('twins',TwinsState,190,192,20),('suncube',SunCube,122,150,36))


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_closed_material_inventory_and_shared_polygons(module,factory,count,panels,actions):
    cube=factory();assert len(cube.solids)==count and len(cube.panels)==panels
    assert Counter(f for h,f,p in cube.panels)=={i:panels//6 for i in range(6)}
    if module=='twins':
        from cube.twins_cad_material import data,group
        assert set(map(group,data()['atoms']))==set(cube.signatures)
        return
    for solid in cube.solids:
        assert volume(solid)>1e-11
        edges=Counter(tuple(sorted((key(a),key(b)))) for p,f in solid for a,b in zip(p,p[1:]+p[:1]))
        assert set(edges.values())=={2}


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_all_closed_macro_words_replay_complete_material(module,factory,count,panels,actions):
    import importlib
    model=importlib.import_module('cube.'+module+'_aligned');rows=model.generators()
    assert len(rows)==actions
    if module=='twins':assert {len(w) for a,w in rows}=={1}
    for action,word in rows:
        replay=factory().apply_moves(word)
        assert replay.aligned_permutation()==action
        assert sorted(action)==list(range(panels))
        replay.apply_moves(tuple(Move(m.axis,0,-m.amount) for m in reversed(word)))
        assert replay.is_solved()


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_observation_json_session_and_draft_full_circle_preserve_all_paints(module,factory,count,panels,actions):
    from app.session import encode,decode
    from cube.curvy_copter import multiply
    from cube.appearance import IDENTITY_FRAME
    from cube.polyhedral import rotate
    import math,importlib
    model=importlib.import_module('cube.'+module+'_aligned');source=model.scrambled(71,30)
    reentered=factory.from_observation(json.loads(json.dumps(source.observation_data())))
    assert reentered.signature()==source.signature() and not hasattr(reentered,'history')
    assert decode(json.loads(json.dumps(encode(reentered)))).signature()==source.signature()
    selected=source.panels[0][0];before=source.signature()
    turn=tuple(rotate(v,(1.,0.,0.),math.pi/2) for v in IDENTITY_FRAME)
    for _ in range(4):source.set_piece_frame(selected,multiply(turn,source.frames[selected]))
    assert source.signature()==before


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_entered_observations_and_world_colours_solve_without_history(module,factory,count,panels,actions,seed,length):
    import importlib
    model=importlib.import_module('cube.'+module+'_aligned');solver=importlib.import_module('solver.'+module)
    source=model.scrambled(seed,length);entered=factory.from_observation(json.loads(json.dumps(source.observation_data())))
    before=entered.signature();word=solver.solve(entered)
    assert entered.clone().apply_moves(word).is_solved() and entered.signature()==before
    flat=model.scrambled(seed,length,jumble=False);entered=factory(paints=model.observed_colors(flat))
    word=solver.solve(entered);assert entered.clone().apply_moves(word).is_solved()


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_asset_transversals_match_their_actual_guarded_macros(module,factory,count,panels,actions):
    import importlib
    from solver.polyhedral import apply_word
    model=importlib.import_module('cube.'+module+'_aligned');solver=importlib.import_module('solver.'+module)
    if module=='twins':
        from cube.twins_cad_reduced import AlignedReducedTwins
        aligned=AlignedReducedTwins();solver_panels=len(aligned.colors)
    else:aligned=model.AlignedSunCube();solver_panels=panels
    base,rows=solver.prepared();fixed=[]
    for point,row in zip(base,rows):
        for beta,permutation,word in row:
            assert permutation[point]==beta and all(permutation[i]==i for i in fixed)
            assert apply_word(aligned.geometry,word)==permutation
        fixed.append(point)
    import zlib
    data=json.loads(zlib.decompress(solver.ASSET.read_bytes()))
    assert data['version']==2 and solver.ASSET.stat().st_size<(300000 if module=='twins' else 50000)
    assert sorted(list(base)+[s for row in data['leaf_stages'] for s in row['slots']])==list(range(solver_panels))
    from solver.polyhedral_reduction import Transports
    allowed={s for row in data['leaf_stages'] for s in row['slots']}
    for row in data['leaf_stages']:
        word=tuple(Move(*m) for m in row['word']);action=apply_word(aligned.geometry,word)
        assert all(action[s]==s for s in range(solver_panels) if s not in allowed)
        assert {s for s in row['slots'] if action[s]!=s}==set(row['base'])
        orbit=tuple(aligned.geometry.stickers[s].piece for s in row['slots'])
        root=tuple(aligned.geometry.stickers[s].piece for s in row['base'])
        transport=Transports(aligned,orbit,root,both_directions=True)
        while transport._expand():pass
        import numpy as np
        assert np.count_nonzero(transport.parents>=0)==row['coverage']==4048
        allowed-=set(row['slots'])


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_failed_incomplete_cancel_and_timeout_never_mutate_observation(module,factory,count,panels,actions):
    import importlib
    solver=importlib.import_module('solver.'+module);model=importlib.import_module('cube.'+module+'_aligned')
    cube=factory(paints=(-1,)*panels);before=cube.signature()
    with pytest.raises(ValueError,match='every sticker'):solver.solve(cube)
    assert cube.signature()==before
    cube=model.scrambled(31);before=cube.signature()
    with pytest.raises(InterruptedError):solver.solve(cube,cancel=lambda:True)
    assert cube.signature()==before
    with pytest.raises(TimeoutError):solver.solve_colours(model.observed_colors(model.scrambled(31,jumble=False)),seconds=0)


@pytest.mark.parametrize('module,factory,count,panels,actions',PROFILES)
def test_single_catalogue_home_shared_routes_and_all_original_lessons(module,factory,count,panels,actions):
    from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family
    from demo.expanded_support import make_cube,entry_screen,view_class
    from demo.expanded_tutorials import lessons
    kind=factory.puzzle_kind;stem='Twins' if module=='twins' else 'SunCube'
    assert catalogue_family(kind)=='edge_family'
    assert sum(kind in v for v in CATALOGUE_FAMILIES.values())==1
    if module=='twins':
        # The CAD continuation remains readable for old checkpoints; new
        # lessons and directory entries use the independently movable reference.
        from cube.twins_pcubes import TwinsPCubesState
        assert type(make_cube(kind,3)) is TwinsPCubesState
    else:assert type(make_cube(kind,3)) is factory
    assert entry_screen(kind)==stem+'InputScreen' and view_class(kind).__name__==stem+'View'
    for lesson in lessons(kind,3):
        for case in lesson['cases']:assert case['initial'].clone().apply_moves(case['moves']).is_solved()


@pytest.mark.parametrize('seed',range(3))
def test_visible_twins_reentry_infers_hidden_cells_and_solves_the_actual_source(seed):
    from cube.twins_aligned import scrambled
    from cube.appearance import IDENTITY_FRAME
    from solver.twins import solve
    source=scrambled(seed,30,jumble=False)
    visible={h for h,f,p in source.panels};entered=source.clone()
    entered.frames=tuple(f if h in visible else IDENTITY_FRAME for h,f in enumerate(source.frames))
    before=entered.signature();inferred=entered.complete_hidden()
    assert entered.signature()==before and inferred.paints==entered.paints
    assert all(inferred.frames[h]==entered.frames[h] for h in visible)
    inferred.validate_pose();word=solve(inferred)
    assert source.clone().apply_moves(word).is_solved()
