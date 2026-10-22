"""Editing a mixed assembly must not drag or erase neighbouring pieces."""
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
import json
import random

import pytest

from cube.articulated import MIXUP_MODELS
from cube.articulated_observation import polygon_key,normal,project,centre2,contains
from cube.mixup import MixupCube
from cube.mixup_assembly import assemblies
from cube.mixup_entry import MixupEntryDraft
from cube.polyhedral import CUBE,Move,dot


@lru_cache(maxsize=24)
def mixed_cube(kind,seed=71):
    cube=MixupCube(kind);rng=random.Random(seed)
    # Bounded by a move count, not a time budget: every run uses the same case.
    turns=[Move(a,l,p) for a,b in enumerate(cube.geometry.layers)
           for l in range(1,len(b)-1) for p in (1,7)]
    rng.shuffle(turns)
    for move in turns:
        try:cube.apply_move(move);break
        except ValueError:continue
    else:raise AssertionError('No mixed pose available')
    for _ in range(10):
        choices=list(cube.moves());rng.shuffle(choices)
        for move in choices:
            try:cube.apply_move(move);break
            except ValueError:continue
    return cube


def skins(draft):
    return {(polygon_key(c['world']),c['color']) for b in draft.blocks
            for c in b['cells'] if c['world'] is not None}


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_physical_signature_ignores_guides_but_checks_complete_piece_geometry(kind):
    source=MixupEntryDraft.from_cube(mixed_cube(kind));expected=source.physical_signature()
    assert expected is not None
    restored=MixupEntryDraft(kind,json.loads(json.dumps(source.state())))
    assert restored.physical_signature()==expected
    for block in restored.blocks:
        block.update(rotation=3,assembly_source=None,composition=None)
        for cell in block['cells']:
            cell['guide']=tuple((0.,0.,0.) for _ in cell['guide']);cell['source_slot']=None
    assert restored.physical_signature()==expected
    for mutation in ('colour','missing','role','connectivity','incomplete','body','direction'):
        if mutation in ('body','direction') and not MIXUP_MODELS[kind][1]:continue
        draft=MixupEntryDraft(kind,source.state())
        cells=[c for b in draft.blocks for c in b['cells']]
        cell=next(c for c in cells if c['panel_role']==('inner_edge' if mutation in ('body','direction') else 'corner'))
        if mutation=='colour':cell['color']=(cell['color']+1)%6
        elif mutation=='missing':cell['world']=None
        elif mutation=='role':cell['panel_role']='centre'
        elif mutation=='connectivity':cell['piece_key']=(polygon_key(cell['world']),)
        elif mutation=='incomplete':next(b for b in draft.blocks if cell in b['cells'])['configured']=False
        elif mutation=='body':cell['body']=cell['body'][:-1]
        elif mutation=='direction':cell['inner_direction']=tuple(-v for v in cell['inner_direction'])
        assert draft.physical_signature()!=expected,mutation


def regions(draft):
    return sorted({draft.linked_positions(i) for i,b in enumerate(draft.blocks)
                   if b['role']!='corner' and draft.assembly_at(i) is not None})


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_every_editable_region_returns_to_same_physical_state_after_full_turn(kind):
    source=MixupEntryDraft.from_cube(mixed_cube(kind));expected=source.physical_signature()
    assert expected is not None
    for region in regions(source):
        index=region[0]
        if not source.can_rotate_assembly(index):continue
        draft=MixupEntryDraft(kind,source.state());step=draft.rotation_step(index)
        for _ in range(4//step):draft.rotate_assembly(index,step)
        assert draft.physical_signature()==expected,(kind,region)


def assert_whole_pieces(draft):
    locations=defaultdict(set)
    for bi,block in enumerate(draft.blocks):
        for cell in block['cells']:
            if cell.get('panel_role')=='corner' or cell['world'] is None:continue
            locations[tuple(cell['piece_key'])].add(draft.linked_positions(bi))
    assert locations
    assert all(len(value)==1 for value in locations.values())


@pytest.mark.parametrize('kind',MIXUP_MODELS)
@pytest.mark.parametrize('seed',(71,194))
def test_mixed_input_keeps_all_panels_and_whole_piece_ownership(kind,seed):
    cube=mixed_cube(kind,seed);draft=MixupEntryDraft.from_cube(cube)
    expected={(polygon_key(p),color) for h in range(len(cube.solids))
              for p,color in cube.placed_faces(h) if color>=0}
    assert skins(draft)==expected
    assert_whole_pieces(draft)
    restored=MixupEntryDraft(kind,json.loads(json.dumps(draft.state())))
    assert skins(restored)==expected
    assert_whole_pieces(restored)
    # No blank placeholders are introduced when importing a complete state.
    assert all(c['world'] is not None and c['color']>=0 for b in restored.blocks for c in b['cells'])
    assert restored.observations().complete==[True]*6


def test_45_degree_edge_does_not_share_an_edit_with_adjacent_centre():
    cube=MixupCube();cube.apply_move(Move(0,1,1))
    draft=MixupEntryDraft.from_cube(cube)
    for region in regions(draft):
        assembly=draft.assembly_at(region[0])
        assert len(assembly.pieces)==1
    centre=next(i for i,b in enumerate(draft.blocks)
                if b['role']=='centre' and len(b['cells'])==2)
    before=deepcopy(draft.blocks)
    draft.rotate_assembly(centre,1)
    assert skins(draft)!=skins(MixupEntryDraft.from_cube(cube))
    assert all(b==before[i] for i,b in enumerate(draft.blocks) if i!=centre)
    for _ in range(3):draft.rotate_assembly(centre,1)
    assert skins(draft)==skins(MixupEntryDraft.from_cube(cube))


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_rotate_replace_and_clear_are_local_and_fail_atomically(kind):
    initial=MixupEntryDraft.from_cube(mixed_cube(kind));success=0
    for region in regions(initial):
        index=region[0]
        edits=[lambda d:d.rotate_assembly(index,1),lambda d:d.clear_position(index)]
        edits.extend(lambda d,a=a:d.set_assembly(index,a)
                     for a in assemblies(kind,initial.blocks,region))
        for edit in edits:
            draft=MixupEntryDraft(kind,initial.state());before=deepcopy(draft.blocks)
            try:edit(draft)
            except ValueError as exc:
                assert str(exc) in ('mixup.entry_neighbour_conflict','mixup.entry_colour_merge_conflict')
                assert draft.blocks==before
            else:
                success+=1
                assert all(b==before[i] for i,b in enumerate(draft.blocks) if i not in region)
                assert all(c['world'] is not None for i,b in enumerate(draft.blocks)
                           if i not in region for c in b['cells'])
    assert success>len(regions(initial))  # clear AND at least one shape edit


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_colouring_one_panel_preserves_all_other_panels_and_geometry(kind):
    draft=MixupEntryDraft.from_cube(mixed_cube(kind))
    bi,ci=next((i,j) for i,b in enumerate(draft.blocks) for j,c in enumerate(b['cells'])
               if c['panel_role']=='edge')
    selected=draft.blocks[bi]['cells'][ci];key=polygon_key(selected['world'])
    before=skins(draft);draft.paint(bi,ci,(selected['color']+1)%6)
    assert {k for k,_ in skins(draft)}=={k for k,_ in before}
    assert {(k,c) for k,c in skins(draft) if k!=key}=={(k,c) for k,c in before if k!=key}


@pytest.mark.parametrize('kind',MIXUP_MODELS)
def test_reloaded_mixed_draft_matches_without_scramble_history(kind):
    from cube.articulated_observation import match_observations
    cube=mixed_cube(kind);draft=MixupEntryDraft.from_cube(cube)
    # Colour edits and their reversal must not leave stale physical poses or
    # detach a face. Serialize the user data, then match with no known cube.
    bi,ci=next((i,j) for i,b in enumerate(draft.blocks) for j,c in enumerate(b['cells'])
               if c['panel_role']=='edge')
    color=draft.blocks[bi]['cells'][ci]['color']
    draft.paint(bi,ci,(color+1)%6);draft.paint(bi,ci,color)
    restored=MixupEntryDraft(kind,json.loads(json.dumps(draft.state())))
    result=match_observations(restored.observations())
    assert result.status=='matched'
    assert skins(MixupEntryDraft.from_cube(result.cube))==skins(draft)


def test_legacy_split_faces_are_regrouped_without_losing_colours():
    cube=MixupCube();cube.apply_move(Move(0,1,1))
    draft=MixupEntryDraft.from_cube(cube);original=skins(draft)
    # Recreate the old surface-centroid assignment used by v6 saved drafts.
    state=draft.state();state['version']=6
    cells=[c for b in state['blocks'] for c in b['cells']]
    for block in state['blocks']:block['cells']=[]
    for cell in cells:
        n=normal(cell['world']);face=max(range(6),key=lambda f:dot(n,CUBE[f]))
        point=centre2(project(cell['world'],face))
        choices=[(i,b) for i,b in enumerate(draft.blocks) if b['face']==face]
        index=next((i for i,b in choices if contains(b['outline'],point)),None)
        if index is None:
            index=min(choices,key=lambda ib:sum((x-y)**2 for x,y in zip(point,centre2(ib[1]['outline']))))[0]
        state['blocks'][index]['cells'].append(cell)
    restored=MixupEntryDraft(cube.puzzle_kind,json.loads(json.dumps(state)))
    assert skins(restored)==original
    assert_whole_pieces(restored)
    assert all(len(restored.assembly_at(r[0]).pieces)==1 for r in regions(restored))


def test_overlapping_replacement_retains_original_draft():
    from cube.mixup_assembly import Assembly,AssemblyPiece
    draft=MixupEntryDraft.from_cube(MixupCube());index=4
    other=draft.blocks[1]['cells'][0]['world']
    # A stale/wrongly positioned card must not overwrite a different centre.
    a=Assembly('assembly_bad',draft.kind,(index,),(AssemblyPiece('centre',(other,),0),))
    before=draft.state()
    with pytest.raises(ValueError,match='mixup.entry_'):
        draft.set_assembly(index,a)
    assert draft.state()==before
