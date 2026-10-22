"""Solve colour/geometry observations without retaining scramble histories."""
import argparse
import json
from pathlib import Path
import sys
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.articulated_observation import match_observations
from cube.mixup_entry import MixupEntryDraft
from solver.mixup import solve_mixup


def audit(path):
    kind=path.stem.rsplit('-',1)[0];begun=monotonic()
    row={'kind':kind,'fixture':path.name,'history_free':False,'solved':False}
    try:
        draft=MixupEntryDraft(kind,json.loads(path.read_text(encoding='utf-8')))
        match=match_observations(draft.observations());row['match']=match.status
        cube=match.cube
        if cube is None:raise ValueError('Input did not match')
        row['history_free']=not cube.history
        assert row['history_free']
        result=solve_mixup(cube)
        replay=cube.clone();replay.apply_moves(result.moves)
        row.update(solved=result.success and replay.is_solved(),moves=len(result.moves))
    except Exception as exc:row['error']=type(exc).__name__+': '+str(exc)
    row['seconds']=round(monotonic()-begun,3)
    print(json.dumps(row),flush=True)
    return row


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',action='append');parser.add_argument('--seed')
    parser.add_argument('--output',default='reports/input-audit/2026-10-22/mixup-solver.json')
    parser.add_argument('--fresh',type=int,help='Generate independent observation fixtures with this random seed')
    parser.add_argument('--input-directory',default='reports/input-audit/2026-10-21/mixup-manual-inputs')
    parser.add_argument('--also-fresh',action='store_true',help='Include the separately saved independent observation cases')
    args=parser.parse_args();rows=[]
    directory=Path(args.input_directory)
    if args.fresh is not None:
        import random
        from cube.articulated import MIXUP_MODELS
        from cube.mixup import scramble_mixup
        directory=Path('reports/input-audit/2026-10-22/fresh-manual-inputs');directory.mkdir(parents=True,exist_ok=True)
        for kind in args.kind or MIXUP_MODELS:
            random.seed(args.fresh)
            source=scramble_mixup(kind,seconds=1.)
            state=MixupEntryDraft.from_cube(source).state()
            for block in state['blocks']:
                block.update(composition=None,assembly_source=None,rotation=0)
                for cell in block['cells']:
                    cell['source_slot']=None;cell.pop('piece_key',None)
            (directory/(kind+'-'+str(args.fresh)+'.json')).write_text(json.dumps(state),encoding='utf-8')
    paths=list(directory.glob('*.json'))
    if args.also_fresh:paths.extend(Path('reports/input-audit/2026-10-22/fresh-manual-inputs').glob('*.json'))
    for path in sorted(paths):
        kind,seed=path.stem.rsplit('-',1)
        if args.kind and kind not in args.kind or args.seed and args.seed!=seed:continue
        rows.append(audit(path))
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(rows,indent=2),encoding='utf-8')


if __name__=='__main__':main()
