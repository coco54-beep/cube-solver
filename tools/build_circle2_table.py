import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from solver.circle2_table import build,TABLE
if __name__=='__main__':
 c,s=build();print(TABLE,c,s)
