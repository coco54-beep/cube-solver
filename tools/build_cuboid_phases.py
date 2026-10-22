"""Generate compact fixed-cuboid phase tables on the development computer."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solver.cuboid_static import write_phase_tables


def main():
    root = Path(__file__).resolve().parents[1]/'solver/data'
    root.mkdir(exist_ok=True)
    for kind in ('cuboid_223', 'cuboid_332', 'cuboid_334'):
        target = root/f'{kind}_phases.bin'
        write_phase_tables(kind, target, lambda phase, count, actions: print(kind, phase, count, actions, flush=True))
        print(target.name, target.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
