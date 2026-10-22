"""Build the offline Two-Bar depth-7 shell."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from solver.twobar_table import build, TABLE

if __name__ == '__main__':
    count, size = build()
    print(f'{TABLE}: {count} states, {size} bytes')
