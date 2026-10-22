"""Build offline shells for Fused and Bandaged C."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from solver.bandaged_table import build
if __name__=='__main__':
 for kind,depth,name in (('fused_cube',7,'fused'),('bandaged_c',11,'bandaged_c')):
  count,size=build(kind,ROOT/'solver'/'data'/f'{name}_table.bin',depth)
  print(kind,count,size,flush=True)
