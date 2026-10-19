"""Prepare the complete shortest colour-state table for ordinary Pyraminx Duo."""
from collections import deque, Counter
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import Move, PolyhedralPuzzle
from solver.lattice_data import geometry_key


def build():
    cube=PolyhedralPuzzle('pyraminx_duo',3)
    g=cube.geometry
    moves=tuple(Move(a,0,k) for a in range(4) for k in (1,2))
    maps=tuple(g.inverse_permutation(m) for m in moves)
    goal=tuple(cube.colors)
    words={goal:()}
    pending=deque((goal,))
    while pending:
        state=pending.popleft()
        for move,mapping in zip(moves,maps):
            target=tuple(state[i] for i in mapping)
            if target in words: continue
            words[target]=((move.axis,0,(-move.amount)%3),)+words[state]
            pending.append(target)
    counts=Counter(map(len,words.values()))
    if dict(counts)!={0:1,1:8,2:48,3:188,4:79}:
        raise ValueError(f'Duo state graph does not match its mechanism: {counts}')
    # Check generated records before shipping the table to mobile devices.
    for state,word in words.items():
        replay=PolyhedralPuzzle('pyraminx_duo',3,state)
        for atom in word: replay.apply_move(Move(*atom))
        if not replay.is_solved(): raise ValueError('Duo prepared word is incorrect')
    payload={'geometry':geometry_key(g),
             'solutions':{''.join(map(str,s)):w for s,w in words.items()}}
    path=Path(__file__).resolve().parents[1]/'solver/data/pyraminx_duo.bin'
    path.write_bytes(zlib.compress(json.dumps(payload,separators=(',',':')).encode(),9))
    print(f'{len(words)} states; maximum {max(counts)} moves; {path.stat().st_size} bytes')


if __name__=='__main__': build()
