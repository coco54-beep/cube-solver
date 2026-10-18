"""Replay-checked standard-cube solve used by the isolated memory audit."""
import json
import random
import sys
import time

from cube.scramble import random_scramble


def main():
    n=int(sys.argv[1])
    if n in (3,4,5):
        module=__import__(f'cube.cube{n}',fromlist=[f'Cube{n}'])
        cube=getattr(module,f'Cube{n}').solved()
    else:
        from cube.cube_n import CubeN
        cube=CubeN.solved(n)
    scramble=random_scramble(n,random.Random(12345))
    cube.apply_moves(scramble)
    start=time.perf_counter()
    if n==3:
        from solver.solver3 import solve_3x3
        from cube.conversion import cubies_to_facelets
        result=solve_3x3(cubies_to_facelets(cube.cubies,n))
    elif n in (4,5):
        module=__import__(f'solver.solver{n}',fromlist=[f'solve_{n}x{n}'])
        result=getattr(module,f'solve_{n}x{n}')(cube)
    else:
        from solver.solver_n import solve_nxn
        result=solve_nxn(cube)
    elapsed=time.perf_counter()-start
    if not result.success: raise RuntimeError(result.message)
    cube.apply_moves(result.moves)
    print(json.dumps({'kind':'cube','n':n,'scramble_length':len(scramble),
        'seconds':round(elapsed,3),'moves':len(result.moves),'replay_ok':cube.is_solved()}))


if __name__=='__main__': main()
