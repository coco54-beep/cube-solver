"""Compare entered-state prism solutions using reproducible legal scrambles."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.polyhedral import scramble,solve_polyhedral
from solver.polyhedral_optimize import optimize_solution
from solver.pentahedron_reduce import core_injection


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--seeds',nargs='+',type=int,default=[54,13,29])
    parser.add_argument('--length',type=int,default=24)
    args=parser.parse_args()
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('w',encoding='utf8') as stream:
        for n in (4,5):
            for seed in args.seeds:
                cube=PolyhedralPuzzle('pentahedron',n)
                scramble(cube,args.length,seed)
                cube=cube.entered()
                started=time.perf_counter()
                moves=solve_polyhedral(cube)
                elapsed=time.perf_counter()-started
                check=cube.entered()
                for move in moves:check.apply_move(move)
                assert check.is_solved(),(n,seed)
                row={'order':n,'seed':seed,'length':args.length,'moves':len(moves),
                     'seconds':round(elapsed,3),'replay':'pass',
                     'word':[[m.axis,m.layer,m.amount] for m in moves]}
                stream.write(json.dumps(row)+'\n');stream.flush()
                print({k:v for k,v in row.items() if k!='word'},flush=True)


if __name__=='__main__':main()
