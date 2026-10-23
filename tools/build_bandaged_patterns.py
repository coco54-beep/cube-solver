"""Offline pattern tables for state-based, constrained bandage solving."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.bandaged_state import model
from solver.cuboid_search import build_patterns


def build(kind):
    geometry=model(kind)
    path=Path('solver/data')/(kind+'_patterns.bin')
    build_patterns(kind,path,strong=False,model=geometry.data,
                   metadata={'bandage_geometry':geometry.fingerprint},
                   report=lambda *p:print(kind,*p,flush=True))
    print('saved',kind,path.stat().st_size,flush=True)


if __name__=='__main__':
    for kind in (sys.argv[1:] or ('ai_cube','burr_cube')):build(kind)
