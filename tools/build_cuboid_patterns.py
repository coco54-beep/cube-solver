"""Build compact bandaged-cuboid pruning tables on the development computer."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solver.cuboid_search import build_patterns, build_endgame

if __name__ == '__main__':
    for kind in sys.argv[1:] or ('camouflage_3', 'cuboid_442'):
        target = Path(__file__).resolve().parents[1]/'solver'/'data'/f'{kind}_patterns.bin'
        build_patterns(kind, target, lambda *args: print(kind, *args, flush=True))
        print(target.name, target.stat().st_size, flush=True)
        target = target.with_name(kind+'_endgame.bin')
        build_endgame(kind, target, report=lambda *args: print(kind, 'endgame', *args, flush=True))
        print(target.name, target.stat().st_size, flush=True)
