"""Paired entered-state benchmarks for prism, football and high-order minx."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import solve_polyhedral,scramble
import solver.polyhedral_optimize
import solver.football
import solver.high_minx_reduction
import solver.pentahedron_reduce


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--kinds',nargs='+',default=['pentahedron','football','megaminx'])
    parser.add_argument('--seeds',nargs='+',type=int,default=[54,13,29])
    args=parser.parse_args()
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    orders={'pentahedron':[4,5],'football':[3,5],'megaminx':[4,5,8,13]}
    with path.open('w',encoding='utf8') as out:
        for kind in args.kinds:
            for n in orders[kind]:
                for seed in args.seeds:
                    cube=PolyhedralPuzzle(kind,n)
                    length=24
                    scramble(cube,length,seed)
                    cube=cube.entered();initial=tuple(cube.colors)
                    start=time.perf_counter()
                    moves=solve_polyhedral(cube)
                    seconds=time.perf_counter()-start
                    replay=cube.entered()
                    for move in moves:replay.apply_move(move)
                    assert replay.is_solved() and tuple(cube.colors)==initial
                    row={'kind':kind,'order':n,'seed':seed,'length':length,
                         'steps':len(moves),'seconds':round(seconds,3),'replay':'pass',
                         'word':[[m.axis,m.layer,m.amount] for m in moves]}
                    out.write(json.dumps(row)+'\n');out.flush()
                    print({k:v for k,v in row.items() if k!='word'},flush=True)


if __name__=='__main__':main()
