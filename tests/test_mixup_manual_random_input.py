"""Replay saved random observations through the real empty input controls.

No source frames/history are available in either saved observation file.
"""
import json
from pathlib import Path

import pytest

from tests.test_mixup_input_screen import editor,wait_until
from cube.articulated_observation import polygon_key
from cube.mixup_entry import MixupEntryDraft
from solver.mixup import solve_mixup


def region_shape(draft,region):
    return {(polygon_key(c['world']),c.get('panel_role'),
             tuple(sorted(polygon_key(poly) for poly in c.get('body',()))))
            for bi in region for c in draft.blocks[bi]['cells'] if c['world'] is not None}


@pytest.mark.parametrize('kind',('mixup_344','mixup_444'))
def test_random_manual_input_runs_real_controls_and_solver(editor,kind):
    root=Path(__file__).resolve().parents[1]
    path=root/'reports/input-audit/2026-10-21/mixup-manual-inputs'/(kind+'-211021.json')
    target=MixupEntryDraft(kind,json.loads(path.read_text(encoding='utf-8')))
    screen=editor(kind,[]);screen.clear()
    assert not screen._cube.history and screen._cube.is_solved()
    regions=sorted({target.linked_positions(i) for i,b in enumerate(target.blocks) if b['role']!='corner'})
    for region in regions:
        index=region[0];screen.pick(index*1024)
        wait_until(lambda:screen._assembly_job is None)
        found=None
        for assembly in screen._assemblies:
            for turn in range(4):
                probe=MixupEntryDraft(kind);probe.set_assembly(index,assembly)
                if turn:probe.rotate_assembly(index,turn)
                if region_shape(probe,region)==region_shape(target,region):
                    found=assembly,turn;break
            if found:break
        assert found is not None,(kind,region)
        screen.select_assembly(found[0])
        for _ in range(found[1]):screen.rotate_assembly(1)
        assert region_shape(screen._get_draft(),region)==region_shape(target,region)
    colours={polygon_key(c['world']):c['color'] for b in target.blocks for c in b['cells']}
    for colour in range(6):
        screen.select_color(colour)
        for bi,block in enumerate(screen._get_draft().blocks):
            for ci,cell in enumerate(block['cells']):
                if colours[polygon_key(cell['world'] or cell['guide'])]==colour:screen.pick(bi*1024+ci)
    assert not screen._applied()  # Must match new entry; cannot reuse the solved cube.
    screen.apply();wait_until(lambda:screen._job is None)
    assert screen._applied() and not screen._cube.history
    entered=MixupEntryDraft.from_cube(screen._cube)
    assert {(polygon_key(c['world']),c['color']) for b in entered.blocks for c in b['cells']}==set(colours.items())
    result=solve_mixup(screen._cube.clone())
    replay=screen._cube.clone();replay.apply_moves(result.moves)
    assert result.success and replay.is_solved()
