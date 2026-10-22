"""Inner strips retain real bevel geometry, half-turn choices and colours."""
from copy import deepcopy
from itertools import combinations
import json

import pytest

from cube.articulated_observation import polygon_key,normal
from cube.mixup_assembly import assemblies,inner_pattern,inner_arrangement,inner_ridge,half_turn_inner,AssemblyPiece,CATALOG_VERSION
from cube.mixup_entry import MixupEntryDraft,_panel_shape
from cube.polyhedral import dot,mean


PLUS=('mixup_plus_333','mixup_plus_334','mixup_plus_344','mixup_plus_444')


@pytest.mark.parametrize('kind,expected',(
    ('mixup_plus_333',{'whole'}),
    ('mixup_plus_334',{'whole','same','opposite_a','opposite_b'}),
    ('mixup_plus_344',{'whole','same','opposite_a','opposite_b'}),
    ('mixup_plus_444',{'same','opposite_a','opposite_b'})))
def test_all_inner_positions_offer_model_specific_compositions(kind,expected):
    draft=MixupEntryDraft(kind)
    for i,block in enumerate(draft.blocks):
        if block['role']!='inner_edge':continue
        options=assemblies(kind,draft.blocks,(i,))
        assert {inner_arrangement(a.pieces) for a in options}==expected
        assert len({a.group_key for a in options})==len(expected)


def bevel_shape(body):
    points=tuple({p for poly in body for p in poly})
    return tuple(sorted(round(sum((x-y)**2 for x,y in zip(p,q)),6) for p,q in combinations(points,2)))


def colours_by_ridge(block):
    return {polygon_key(inner_ridge(AssemblyPiece('inner_edge',(c['world'],),0,c['body'],c['inner_direction']))):c['color']
            for c in block['cells']}


@pytest.mark.parametrize('kind',PLUS)
def test_half_turn_changes_the_whole_bevel_and_keeps_its_rigid_shape(kind):
    draft=MixupEntryDraft(kind)
    piece=assemblies(kind,draft.blocks,(2,))[0].pieces[0]
    flipped=half_turn_inner(piece)
    assert polygon_key(flipped.panels[0])!=polygon_key(piece.panels[0])
    assert polygon_key(inner_ridge(flipped))==polygon_key(inner_ridge(piece))
    assert dot(normal(flipped.panels[0]),normal(piece.panels[0]))<1-1e-6
    assert bevel_shape(flipped.body)==bevel_shape(piece.body)
    assert tuple(sorted(polygon_key(p) for p in flipped.body))!=tuple(sorted(polygon_key(p) for p in piece.body))
    n=normal(piece.panels[0])
    # The whole solid and skin rotate together about the fixed black ridge.
    assert dot(normal(flipped.panels[0]),flipped.direction)==pytest.approx(dot(n,piece.direction))
    assert polygon_key(half_turn_inner(flipped).body[0])==polygon_key(piece.body[0])


@pytest.mark.parametrize('kind',PLUS[1:])
@pytest.mark.parametrize('index',(2,5,8))
def test_switching_relative_direction_preserves_each_panel_colour_after_turn(kind,index):
    draft=MixupEntryDraft(kind)
    choices={inner_pattern(a.pieces):a for a in assemblies(kind,draft.blocks,(index,))}
    draft.set_assembly(index,choices['same'])
    draft.paint(index,0,2);draft.paint(index,1,4)
    draft.rotate_assembly(index,draft.rotation_step(index))
    before=deepcopy(draft.blocks)
    expected=colours_by_ridge(draft.blocks[index])
    for pattern in ('opposite','same','opposite'):
        draft.set_assembly(index,choices[pattern])
        assert colours_by_ridge(draft.blocks[index])==expected
        assert inner_pattern(draft.assembly_at(index).pieces)==pattern
        parts=draft.assembly_at(index).pieces
        if pattern=='opposite':assert dot(normal(parts[0].panels[0]),normal(parts[1].panels[0]))<1-1e-6
        assert all(b==before[i] for i,b in enumerate(draft.blocks) if i!=index)
    restored=MixupEntryDraft(kind,json.loads(json.dumps(draft.state())))
    assert inner_pattern(restored.assembly_at(index).pieces)=='opposite'
    assert colours_by_ridge(restored.blocks[index])==expected


@pytest.mark.parametrize('kind',PLUS[1:3])
def test_unsplit_to_split_keeps_colour_when_input_has_turned_180(kind):
    draft=MixupEntryDraft(kind)
    choices={inner_pattern(a.pieces):a for a in assemblies(kind,draft.blocks,(2,))}
    draft.set_assembly(2,choices['whole']);draft.paint(2,0,3)
    draft.rotate_assembly(2,2)
    for pattern in ('same','opposite','whole'):
        draft.set_assembly(2,choices[pattern])
        assert all(c['color']==3 for c in draft.blocks[2]['cells'])


@pytest.mark.parametrize('kind',PLUS[1:3])
def test_merging_two_different_colours_keeps_input_atomically(kind):
    draft=MixupEntryDraft(kind)
    choices={inner_pattern(a.pieces):a for a in assemblies(kind,draft.blocks,(2,))}
    draft.set_assembly(2,choices['same']);draft.paint(2,0,2);draft.paint(2,1,4)
    before=draft.state()
    with pytest.raises(ValueError,match='mixup.entry_colour_merge_conflict'):
        draft.set_assembly(2,choices['whole'])
    assert draft.state()==before


def test_packaged_choices_match_current_generator_version():
    from pathlib import Path
    data=json.loads((Path(__file__).resolve().parents[1]/'assets/mixup_assemblies.json').read_text(encoding='utf8'))
    assert data['version']==CATALOG_VERSION


def test_legacy_arrow_only_variant_repairs_its_bevel_without_erasing_colour():
    draft=MixupEntryDraft('mixup_plus_444')
    choices={inner_pattern(a.pieces):a for a in assemblies(draft.kind,draft.blocks,(2,))}
    draft.set_assembly(2,choices['same']);draft.paint(2,0,4)
    state=draft.state();cell=state['blocks'][2]['cells'][0]
    cell['inner_direction']=tuple(-v for v in cell['inner_direction'])
    restored=MixupEntryDraft(draft.kind,state)
    assert restored.repaired
    assert restored.blocks[2]['cells'][0]['color']==4
    assert polygon_key(restored.blocks[2]['cells'][0]['world'])!=polygon_key(cell['world'])
    assert inner_pattern(restored.assembly_at(2).pieces)=='opposite'
    assert not MixupEntryDraft(draft.kind,restored.state()).repaired
