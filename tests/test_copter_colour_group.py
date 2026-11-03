"""Offline-certified closed-shape actions and entered Copter colour states."""
import math,json
import pytest
from cube.copter_aligned import AlignedCopter,generators,observed_colors
from cube.curvy_copter import CopterState
from cube.polyhedral import Move


def test_each_abstract_generator_replays_on_all_solids_and_is_an_involution():
    rows=generators();assert len(rows)==36
    assert {len(word) for action,word in rows}=={1,5}
    for action,word in rows:
        work=CopterState();before=work.signature()
        for move in word:work.apply_move(move)
        assert work.aligned_permutation()==action
        assert sorted(action)==list(range(72))
        for move in word:work.apply_move(move)
        assert work.signature()==before


def test_compiled_transversals_fix_previous_points_and_match_their_words():
    from solver.copter_colours import prepared
    from solver.polyhedral import apply_word
    base,rows=prepared();cube=AlignedCopter();fixed=[];order=1
    for point,row in zip(base,rows):
        order*=len(row)
        for beta,action,word in row:
            assert action[point]==beta and all(action[i]==i for i in fixed)
            assert apply_word(cube.geometry,word)==action
        fixed.append(point)
    assert order==56024105772127003079121410457600000


@pytest.mark.parametrize('seed',range(12))
def test_entered_colour_solution_uses_no_hidden_leaf_identifiers(seed):
    from random import Random
    from solver.copter_colours import solve
    rng=Random(seed);cube=AlignedCopter()
    for _ in range(100):cube.apply_move(rng.choice(cube.moves()))
    colors=tuple(cube.colors);entered=AlignedCopter(colors)
    word=solve(colors)
    for m in word:entered.apply_move(m)
    assert entered.is_solved() and tuple(cube.colors)==colors
    # Same-colour leaf identities were never supplied as an input.
    assert all(type(c) is int and c in range(6) for c in colors)


def test_incomplete_illegal_edge_and_cancelled_input_keep_colours():
    from solver.copter_colours import solve
    cube=AlignedCopter();colors=list(cube.colors);colors[0]=-1
    with pytest.raises(ValueError,match='every sticker'):solve(colors)
    assert colors[0]==-1
    with pytest.raises(InterruptedError):solve(cube.colors,lambda:True)
    edge=next(p for p in cube.geometry.pieces if len(p)==2)
    colors=list(cube.colors);colors[edge[0]]=(colors[edge[0]]+1)%6
    with pytest.raises(ValueError):solve(colors)


def test_global_corner_twist_and_edge_parity_are_checked_before_search():
    from solver.copter_colours import solve,validate
    from cube.polyhedral import dot,cross
    c=AlignedCopter();g=c.geometry;goal=list(c.colors)
    edge=next(p for p in g.pieces if len(p)==2)
    corners=[p for p in g.pieces if len(p)==3]
    def ordered(slots):
        out=sorted(slots,key=lambda i:goal[i]);ns=[g.spec.normals[goal[i]] for i in out]
        if dot(cross(ns[0],ns[1]),ns[2])<0:out[1],out[2]=out[2],out[1]
        return out
    colors=list(goal);a,b=edge;colors[a],colors[b]=colors[b],colors[a]
    with pytest.raises(ValueError,match='orientation or permutation'):validate(colors)
    corner=ordered(corners[0]);colors=list(goal)
    for i,j in zip(corner,corner[1:]+corner[:1]):colors[i]=goal[j]
    with pytest.raises(ValueError,match='orientation or permutation'):validate(colors)
    colors=list(goal);a,b=ordered(corners[0]),ordered(corners[1])
    for i,j in zip(a,b):colors[i],colors[j]=colors[j],colors[i]
    with pytest.raises(ValueError,match='orientation or permutation'):validate(colors)
    # The same odd corner permutation becomes legal with one edge flip.
    a,b=edge;colors[a],colors[b]=colors[b],colors[a]
    validate(colors);work=AlignedCopter(colors)
    for move in solve(colors):work.apply_move(move)
    assert work.is_solved()


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('seed',range(6))
def test_observed_jumbled_reference_restores_shape_and_colours_without_history(seed,length):
    from tests.test_curvy_copter_solids import walk
    from solver.curvy_copter import solve
    source=walk(20261027+seed,length)
    observed=CopterState.from_observation(json.loads(json.dumps(source.observation_data())));before=observed.signature()
    word=solve(observed);replay=CopterState(observed.frames,observed.paints)
    for move in word:replay.apply_move(move)
    assert observed_colors(replay)==tuple(face for home,face,p in replay.panels)
    assert observed.signature()==before


@pytest.mark.parametrize('seed',range(6))
def test_colour_mixed_by_many_closed_jumbles_then_partially_turned(seed):
    from random import Random
    from solver.curvy_copter import solve
    from cube.curvy_copter import JUMBLE
    rng=Random(20261027+seed);source=CopterState()
    for _ in range(30):
        for m in rng.choice(generators())[1]:source.apply_move(m)
    # Add a visible shape phase after crossing the old regular leaf orbits.
    source.apply_move(Move(seed,0,JUMBLE))
    observed=CopterState(source.frames,source.paints);before=observed.signature()
    word=solve(observed);replay=observed.clone()
    for m in word:replay.apply_move(m)
    assert observed_colors(replay)==tuple(face for home,face,p in replay.panels)
    assert observed.signature()==before


def test_complete_reference_solve_preserves_partial_input_and_cancel():
    from solver.curvy_copter import solve
    source=CopterState();paints=list(source.paints);paints[0]=-1
    observed=CopterState(source.frames,paints);before=observed.signature()
    with pytest.raises(ValueError,match='every sticker'):solve(observed)
    assert observed.signature()==before
    with pytest.raises(InterruptedError):solve(source,lambda:True)


def test_wrong_colour_counts_do_not_start_shape_search(monkeypatch):
    import solver.curvy_copter as module
    source=CopterState();source.paints=(0,)*72
    monkeypatch.setattr(module,'normalize',lambda *a,**kw:pytest.fail('Invalid colours started shape search'))
    before=source.signature()
    with pytest.raises(ValueError,match='color counts'):module.solve(source)
    assert source.signature()==before


@pytest.mark.parametrize('corruption',('model','version','count','numeric','frame','paints','colour','nil_frames'))
def test_malformed_observation_is_rejected_without_changing_source(corruption):
    source=CopterState();before=source.signature();data=json.loads(json.dumps(source.observation_data()))
    if corruption=='model':data['model']='some other puzzle'
    elif corruption=='version':data['version']=True
    elif corruption=='count':data['frames'].pop()
    elif corruption=='numeric':data['frames'][0][0][0]='invalid'
    elif corruption=='frame':data['frames'][0][0][0]=.5
    elif corruption=='paints':data['paints']=None
    elif corruption=='colour':data['paints'][0]=True
    elif corruption=='nil_frames':data['frames']=None
    with pytest.raises(ValueError,match='rigid.invalid'):CopterState.from_observation(data)
    assert source.signature()==before


def test_congruent_leaf_names_are_not_needed_to_solve_the_same_observation():
    from random import Random
    from cube.appearance import ROTATIONS,transform_frame
    from cube.curvy_copter import cuts,multiply,JUMBLE
    from cube.polyhedral import key
    from solver.curvy_copter import solve
    rng=Random(54);source=CopterState()
    for _ in range(20):
        for m in rng.choice(generators())[1]:source.apply_move(m)
    source.apply_move(Move(0,0,JUMBLE))
    slots={h:[] for h in range(len(source.regions))}
    for i,(h,face,p) in enumerate(source.panels):slots[h].append(i)
    leaves=[h for h,s in slots.items() if len(s)==1];shuffled=list(leaves);rng.shuffle(shuffled)
    indices={key(c.centre):i for i,c in enumerate(cuts())}
    def rotated(mask,frame):
        return sum(1<<indices[key(transform_frame(frame,c.centre))] for i,c in enumerate(cuts()) if mask&(1<<i))
    frames=list(source.frames);paints=list(source.paints)
    for target,home in zip(leaves,shuffled):
        frame=next(r for r in ROTATIONS if rotated(source.signatures[target],r)==source.signatures[home])
        frames[target]=multiply(source.frames[home],frame);paints[slots[target][0]]=source.paints[slots[home][0]]
    observed=CopterState(frames,paints)
    def visible(c):
        return sorted((tuple(sorted(key(p) for p in polygon)),color)
                      for polygon,color in zip(c.world_panels(),c.paints))
    assert visible(observed)==visible(source)
    before=observed.signature();word=solve(observed)
    result=observed.clone()
    for m in word:result.apply_move(m)
    assert observed_colors(result)==tuple(face for home,face,p in result.panels)
    assert observed.signature()==before


def test_bounded_offline_word_pool_keeps_the_exact_group():
    from sympy.combinatorics import Permutation,PermutationGroup
    from tools.weighted_group_builder import build
    raw=((1,2,3,0,5,4),(1,0,2,3,4,5));degree=6
    pool={p:((i,1),) for i,p in enumerate(raw)}
    group=PermutationGroup([Permutation(p) for p in pool]);base=list(range(degree))
    group._schreier_sims(base=base)
    def compact(word):
        out=[]
        for m in word:
            if out and out[-1]==(m[0],-m[1]):out.pop()
            else:out.append(m)
        return tuple(out)
    def inverse(word):return tuple((i,-sign) for i,sign in reversed(word))
    with pytest.raises(ValueError,match='exact group'):
        build(pool,base,group.basic_orbits,group.orbits(),compact,inverse,bucket_limit=1)
    relations=[]
    rows=build(pool,base,group.basic_orbits,group.orbits(),compact,inverse,
               limit=1,bucket_limit=1,preserve_group=True,on_relation=relations.append)
    assert math.prod(map(len,rows))==group.order()==48
    for row in rows:
        for record in row.values():
            action=list(range(degree))
            for i,sign in record['word']:
                atom=tuple(Permutation(raw[i])**sign)
                action=[atom[j] for j in action]
            assert tuple(action)==tuple(record['permutation'])
    assert relations
    for word in relations:
        action=list(range(degree))
        for i,sign in word:
            atom=tuple(Permutation(raw[i])**sign);action=[atom[j] for j in action]
        assert action==list(range(degree))
