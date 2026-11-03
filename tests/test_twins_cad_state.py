"""Application replacement must use CAD fields and complete CSG cells."""
import json
from collections import Counter
import pytest
from cube.twins_state import TwinsState
from cube.twins_cad_material import data,group,structure,cuts,frame_action,transform_group,fingerprint
from cube.polyhedral import CUBE,Move
from cube.appearance import ROTATIONS,IDENTITY_FRAME
from cube.twins_aligned import scrambled,observed_colors,generators


def test_source_csg_inventory_includes_hidden_material_and_all_actual_face_fields():
    from cube.spherical_cells import Arrangement,Plane
    c=TwinsState();d=data()
    assert len(c.frames)==190 and len(c.panels)==192
    assert Counter(f for h,f,p in c.panels)=={f:32 for f in range(6)}
    assert Counter(Counter(h for h,f,p in c.panels).values())=={1:120,2:24,3:8}
    atoms=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts()).positive_masks()
    assert set(atoms)==set(d['atoms']) and set(map(group,atoms))==set(c.signatures)
    assert d['source']==fingerprint()
    for frame in ROTATIONS:
        assert {transform_group(g,frame_action(frame)) for g in c.signatures}==set(c.signatures)


@pytest.mark.parametrize('axis',range(20))
def test_regular_turn_moves_whole_material_and_actual_polygons_to_matching_slots(axis):
    from shapely.geometry import Polygon
    from cube.curvy_copter import inverse_point
    c=TwinsState();before=c.signature();selected=set(c.selection(axis));amount=180 if axis<12 else 120
    c.apply_move(Move(axis,0,amount));action=c.aligned_permutation()
    assert sorted(action)==list(range(192))
    assert all(c.frames[h]==IDENTITY_FRAME for h in range(190) if h not in selected)
    world=c.world_panels()
    for i,target in enumerate(action):
        h,f,poly=c.panels[target];n=CUBE[f];u=next(p for p in CUBE if sum(a*b for a,b in zip(n,p))==0)
        from cube.polyhedral import cross,dot
        v=cross(n,u)
        xy=lambda p:(dot(p,u),dot(p,v))
        actual=Polygon(tuple(xy(p) for p in world[i]));expected=Polygon(tuple(xy(p) for p in poly))
        assert actual.hausdorff_distance(expected)<1e-4
    c.apply_move(Move(axis,0,-amount));assert c.signature()==before


@pytest.mark.parametrize('move',(Move(0,0,70.529),Move(12,0,17.),Move(0,0,90.)))
def test_unsupported_stop_angles_are_atomic_and_classified_as_blocked(move):
    from services.failures import classify
    c=scrambled(17,100);before=c.signature()
    with pytest.raises(ValueError,match='rigid.blocked'):c.apply_move(move)
    assert c.signature()==before


def test_old_model_observations_and_198_colours_are_rejected_without_misreading():
    old=dict(model='mf8-twins-material',version=1,frames=[IDENTITY_FRAME]*166,paints=[0]*198)
    with pytest.raises(ValueError):TwinsState.from_observation(old)
    with pytest.raises(ValueError):TwinsState(old['frames'],old['paints'])
    c=scrambled(71,100);assert TwinsState.from_observation(json.loads(json.dumps(c.observation_data()))).signature()==c.signature()
    from app.session import encode,decode
    checkpoint=encode(c);assert decode(json.loads(json.dumps(checkpoint))).signature()==c.signature()
    checkpoint['v']['geometry_fingerprint']='old-radius'
    with pytest.raises(ValueError,match='twins.legacy_entry'):decode(checkpoint)


def test_equivariant_solver_reduction_never_merges_editable_colour_fields():
    from cube.twins_cad_reduced import reduction,compress,generators as reduced_generators
    kept,copies=reduction();assert len(kept)==144 and len(copies)==48
    c=scrambled(51,100);colors=list(observed_colors(c));assert len(compress(colors))==144
    for a,b in copies:
        assert colors[a]==colors[b]
    a,b=copies[0];colors[b]=(colors[a]+1)%6
    with pytest.raises(ValueError,match='tilted.group_unresolved') as error:compress(colors)
    assert error.value.locations==[dict(sticker=a),dict(sticker=b)]


def test_discrete_hidden_completion_preserves_every_observable_pose_and_colour():
    c=scrambled(19,100);entered=c.clone();visible={h for h,f,p in c.panels}
    entered.frames=tuple(f if h in visible else IDENTITY_FRAME for h,f in enumerate(c.frames))
    before=entered.signature();fixed=entered.complete_hidden();fixed.validate_pose()
    assert entered.signature()==before and fixed.paints==c.paints
    assert all(fixed.frames[h]==c.frames[h] for h in visible)
    assert observed_colors(fixed)==observed_colors(c)


@pytest.mark.parametrize('seed',range(3))
@pytest.mark.parametrize('length',(30,100))
def test_manual_world_colour_reentry_solves_without_history(seed,length):
    from solver.twins import solve
    source=scrambled(seed,length);entered=TwinsState(paints=observed_colors(source));before=entered.signature()
    assert not hasattr(entered,'history')
    word=solve(entered,seconds=60.)
    assert entered.clone().apply_moves(word).is_solved() and entered.signature()==before
