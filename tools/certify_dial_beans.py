"""Exhaust the conjugate triple orbits; certify the model's colour solver."""
import json,sys
from pathlib import Path
from time import perf_counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.dial_beans import KINDS
from cube.polyhedral import PolyhedralPuzzle
from solver.dial_beans import primitive
from solver.polyhedral_reduction import Transports


def main():
    rows=[]
    for kind,n in KINDS.items():
        started=perf_counter();cube=PolyhedralPuzzle(kind,n);word,base=primitive(cube)
        orbit=tuple(range(8,80)) if kind=='time_machine' else tuple(range(len(cube.colors)))
        transport=Transports(cube,orbit,base,both_directions=True)
        while transport._expand():pass
        count=int(np.count_nonzero(transport.parents>=0));size=len(orbit)
        expected=size*(size-1)*(size-2)//3
        assert count==expected,(kind,count,expected)
        rows.append(dict(kind=kind,cycle_length=3,cycle_word_moves=len(word),
                         all_other_slots_fixed=True,orbit_size=size,conjugate_cycles=count,
                         expected_cycles=expected,complete=True,seconds=round(perf_counter()-started,3)))
        print(kind,count,flush=True)
    root=Path('reports/expansion/2026-10-26/time-beans');root.mkdir(parents=True,exist_ok=True)
    (root/'cycle-certificate.json').write_text(json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':main()
