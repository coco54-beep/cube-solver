"""Audit random Mixups through observation matching, with no solution history.

The source cube is an oracle only. The solver receives only the fresh result
of matching geometric/colour observations. Menu coverage is audited separately
so ideal observation import is never mistaken for a successful UI round trip.
"""
import json
from pathlib import Path
import random
import sys
from time import monotonic

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from cube.articulated import MIXUP_MODELS
from cube.articulated_observation import match_observations,polygon_key
from cube.mixup import scramble_mixup
from cube.mixup_assembly import assemblies,assembly_key
from cube.mixup_entry import MixupEntryDraft
from solver.mixup import solve_mixup


def geometry(draft):
    return {(polygon_key(c['world']),c['color']) for b in draft.blocks
            for c in b['cells'] if c['world'] is not None}


def menu_coverage(target):
    """Use only selectable menu assemblies and the public input rotations."""
    regions=sorted({target.linked_positions(i) for i,b in enumerate(target.blocks) if b['role']!='corner'})
    missing=[];covered=0;empty=0;choices=[]
    for region in regions:
        index=region[0];expected=target.assembly_at(index)
        if expected is None:
            empty+=1;missing.append({'region':region,'role':target.blocks[index]['role'],'reason':'no_empty_choice'})
            continue
        found=None
        for assembly in assemblies(target.kind,target.blocks,region):
            for turn in range(0,4,2 if target.blocks[index]['role']=='inner_edge' else 1):
                probe=MixupEntryDraft(target.kind)
                try:
                    probe.set_assembly(index,assembly)
                    if turn:probe.rotate_assembly(index,turn)
                except ValueError:continue
                entered=probe.assembly_at(index)
                if entered is not None and assembly_key(entered.pieces)==assembly_key(expected.pieces):
                    found=(assembly,turn);break
            if found:break
        if found:
            covered+=1;choices.append((index,*found))
        else:missing.append({'region':region,'role':target.blocks[index]['role'],'reason':'no_geometry_choice',
                             'pieces':dict(expected.counts)})
    result={'total_regions':len(regions),'covered_regions':covered,'empty_regions':empty,'missing':missing,
            'blank_entry_rebuilt':False}
    if missing:return result,None
    # A second pass builds the entire blank input, allowing collisions or
    # linked edits to reveal interactions between otherwise available choices.
    entry=MixupEntryDraft(target.kind)
    try:
        for index,assembly,turn in choices:
            entry.set_assembly(index,assembly)
            if turn:entry.rotate_assembly(index,turn)
        colours=dict(geometry(target))
        for bi,block in enumerate(entry.blocks):
            for ci,cell in enumerate(block['cells']):
                entry.paint(bi,ci,colours[polygon_key(cell['world'] or cell['guide'])])
        result['blank_entry_rebuilt']=geometry(entry)==geometry(target)
    except (ValueError,KeyError) as exc:result['blank_entry_error']=str(exc)
    return result,entry if result['blank_entry_rebuilt'] else None


def audit(kind,seed):
    row={'kind':kind,'seed':seed};started=monotonic();random.seed(seed)
    try:source=scramble_mixup(kind,seconds=6.)
    except Exception as exc:return dict(row,generation_error=str(exc),elapsed=round(monotonic()-started,3))
    row['source_moves']=len(source.history)
    target=MixupEntryDraft.from_cube(source)
    row['menu'],blank_entry=menu_coverage(target)
    # Serialize only entry data. No frames, home IDs, source slots, remembered
    # combination or original pose can enter the matching/solving pipeline.
    state=(blank_entry or target).state()
    row['input_path']='blank_menu_combinations_rotation_paint' if blank_entry else 'ideal_geometry_observations_only'
    for block in state['blocks']:
        block.update(composition=None,assembly_source=None,rotation=0)
        for cell in block['cells']:
            cell['source_slot']=None;cell.pop('piece_key',None)
    entry=MixupEntryDraft(kind,json.loads(json.dumps(state)))
    path=Path('reports/input-audit/2026-10-21/mixup-manual-inputs')/(kind+'-'+str(seed)+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    row['input_data']=str(path)
    tick=monotonic();matched=match_observations(entry.observations())
    row.update(match=matched.status,match_seconds=round(monotonic()-tick,3))
    if matched.status=='matched':
        cube=matched.cube
        assert not cube.history
        same=geometry(MixupEntryDraft.from_cube(cube))==geometry(target)
        row.update(history_before_solve=len(cube.history),same_surfaces=same)
        if not same:raise AssertionError('Matched cube differs from the observation oracle')
        tick=monotonic()
        try:
            solved=solve_mixup(cube,cancel=lambda:monotonic()-tick>60.)
            replay=cube.clone();replay.apply_moves(solved.moves)
            row.update(solved=solved.success,solution_moves=len(solved.moves),replay_solved=replay.is_solved(),
                       shape_moves=len(solved.stages[0].moves),core_moves=len(solved.stages[1].moves))
        except InterruptedError:row.update(solved=False,solve_error='audit.cancelled_after_60s')
        except Exception as exc:row.update(solved=False,solve_error=str(exc))
        row['solve_seconds']=round(monotonic()-tick,3)
    row['elapsed']=round(monotonic()-started,3)
    row['manual_roundtrip_passed']=bool(blank_entry and row.get('replay_solved'))
    return row


def main():
    output=Path('reports/input-audit/2026-10-21/mixup-manual-random-roundtrip.json')
    rows=[]
    for kind in MIXUP_MODELS:
        for seed in (211021,211022):
            try:row=audit(kind,seed)
            except Exception as exc:row={'kind':kind,'seed':seed,'audit_error':repr(exc)}
            rows.append(row)
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            menu=row.get('menu',{})
            print(json.dumps({k:v for k,v in row.items() if k!='menu'}|{'menu_coverage':str(menu.get('covered_regions'))+'/'+str(menu.get('total_regions'))},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
