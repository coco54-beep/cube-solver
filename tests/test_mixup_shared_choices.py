"""Plus scaffold faces and edges must offer the same physical combinations."""
from copy import deepcopy
from functools import lru_cache

import pytest

from cube.articulated_observation import polygon_key
from cube.mixup import MixupCube
from cube.mixup_assembly import assemblies,assembly_group
from cube.mixup_entry import MixupEntryDraft


PLUS=('mixup_plus_333','mixup_plus_334','mixup_plus_344','mixup_plus_444')
EXPECTED=(2,5,7,3)


def sites(draft):
    return sorted({draft.linked_positions(i) for i,b in enumerate(draft.blocks)
                   if b['role'] in ('centre','edge')})


@pytest.mark.parametrize('kind,count',tuple(zip(PLUS,EXPECTED)))
def test_every_centre_and_edge_has_same_ordered_combination_choices(kind,count):
    draft=MixupEntryDraft(kind);reference=MixupEntryDraft(kind.replace('mixup_plus_','mixup_'));expected=None
    for region in sites(draft):
        choices=assemblies(kind,draft.blocks,region)
        signature=tuple((a.group_key,tuple(sorted(a.counts.items()))) for a in choices)
        assert len(signature)==len(set(signature))==count
        faces={draft.blocks[i]['face'] for i in region};role=draft.blocks[region[0]]['role']
        reference_region=next(r for r in sites(reference) if reference.blocks[r[0]]['role']==role and
                              {reference.blocks[i]['face'] for i in r}==faces)
        reference_groups={}
        for a in assemblies(reference.kind,reference.blocks,reference_region):
            reference_groups.setdefault(a.group_key,tuple(sorted(a.counts.items())))
        assert tuple(counts for _,counts in signature)==tuple(reference_groups.values())
        if expected is None:expected=signature
        assert signature==expected
        for choice in choices:
            assert choice.positions==region
            assert assembly_group(choice.pieces)==choice.group_key
            diagram=choice.diagram(draft.blocks,region[0])
            physical_panels={polygon_key(p) for part in choice.pieces for p in part.panels}
            assert 0<len(diagram)<=len(physical_panels)
            if choice.counts=={'centre':1}:assert len(diagram)==1
            if choice.counts=={'edge':1}:
                assert len(diagram)==2
                a,b=(set((round(x,6),round(y,6)) for x,y in poly) for _,poly,_ in diagram)
                assert len(a&b)==2  # The two skins stay joined as one edge.


@lru_cache(maxsize=4)
def real_skins(kind):
    cube=MixupCube(kind);found=set()
    for home,solid in enumerate(cube.solids):
        if solid.role not in ('centre','edge'):continue
        for pose in range(len(cube.orientations)):
            found.add((solid.role,tuple(sorted(polygon_key(poly)
                for poly,color in cube.placed_faces(home,pose) if color>=0))))
    return found


@pytest.mark.parametrize('kind',PLUS)
def test_shared_choices_are_real_rigid_piece_poses_without_resizing(kind):
    draft=MixupEntryDraft(kind);catalogue=real_skins(kind)
    for region in sites(draft):
        for choice in assemblies(kind,draft.blocks,region):
            for piece in choice.pieces:
                assert (piece.role,tuple(sorted(polygon_key(p) for p in piece.panels))) in catalogue


@pytest.mark.parametrize('kind',PLUS)
def test_all_shared_choices_can_be_entered_on_either_site_without_changing_neighbours(kind):
    initial=MixupEntryDraft(kind)
    for region in sites(initial):
        for choice in assemblies(kind,initial.blocks,region):
            draft=MixupEntryDraft(kind);before=deepcopy(draft.blocks)
            draft.set_assembly(region[0],choice)
            assert all(b==before[i] for i,b in enumerate(draft.blocks) if i not in region)
            entered=draft.assembly_at(region[0])
            assert entered is not None and entered.counts==choice.counts
            assert {polygon_key(p) for piece in entered.pieces for p in piece.panels}=={
                polygon_key(p) for piece in choice.pieces for p in piece.panels}


@pytest.mark.parametrize('kind',PLUS)
def test_centre_panels_at_edge_observation_share_colour_between_views(kind):
    draft=MixupEntryDraft(kind)
    region=next(r for r in sites(draft) if len(r)==2)
    choice=next(a for a in assemblies(kind,draft.blocks,region) if set(a.counts)=={'centre'})
    draft.set_assembly(region[0],choice)
    world=polygon_key(draft.blocks[region[0]]['cells'][0]['world'])
    draft.paint(region[0],0,3)
    panels=[c for i in region for c in draft.blocks[i]['cells'] if polygon_key(c['world'])==world]
    assert len(panels)==2
    assert all(c['panel_role']=='centre' and c['color']==3 for c in panels)


@pytest.mark.parametrize('site_role,piece_role',(('edge','centre'),('centre','edge')))
def test_legal_45_degree_exchange_can_be_entered_from_shared_choices(site_role,piece_role):
    from cube.polyhedral import Move
    cube=MixupCube('mixup_plus_333');cube.apply_move(Move(0,1,1))
    visible=MixupEntryDraft.from_cube(cube)
    colours={polygon_key(c['world']):c['color'] for b in visible.blocks for c in b['cells']}
    for index,block in enumerate(visible.blocks):
        if block['role']!=site_role:continue
        observed=visible.assembly_at(index)
        if observed is None or set(observed.counts)!={piece_role}:continue
        outline={polygon_key(p) for piece in observed.pieces for p in piece.panels}
        region=visible.linked_positions(index)
        for option in assemblies(cube.puzzle_kind,visible.blocks,region):
            if option.counts!=observed.counts:continue
            for turns in range(4):
                entered=MixupEntryDraft(cube.puzzle_kind)
                entered.set_assembly(index,option)
                if turns:entered.rotate_assembly(index,turns)
                panels={polygon_key(p) for piece in entered.assembly_at(index).pieces for p in piece.panels}
                if panels!=outline:continue
                # Only observed panel shapes and colours go into the empty
                # input. No source piece IDs, poses or history are installed.
                for bi in region:
                    for ci,cell in enumerate(entered.blocks[bi]['cells']):
                        entered.paint(bi,ci,colours[polygon_key(cell['world'])])
                assert {(polygon_key(c['world']),c['color']) for bi in region
                        for c in entered.blocks[bi]['cells']}=={(key,colours[key]) for key in outline}
                return
    pytest.fail('The observed exchanged shape cannot be selected and coloured')
