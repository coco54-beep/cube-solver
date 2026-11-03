"""Rebuild silver Camouflage's checked, model-specific offline search assets."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.cuboid_search import build_patterns,build_endgame
from tools.build_camouflage_octants import main as build_macros
from tools.build_camouflage_quotient_patterns import main as build_quotient


def main():
    kind='mirror_camouflage_3'
    output=Path(__file__).resolve().parents[1]/'solver/data'
    build_patterns(kind,output/f'{kind}_patterns.bin',strong=False,
                   report=lambda *row:print('pattern',*row,flush=True))
    # Large endgame tables mostly duplicate the macro shortcut. Three layers
    # cover short examples, leaving complete fallback independent of this cap.
    build_endgame(kind,output/f'{kind}_endgame.bin',maximum=12000,depth=3,
                  report=lambda *row:print('endgame',*row,flush=True))
    build_macros(kind)
    build_quotient(kind)


if __name__=='__main__':main()
