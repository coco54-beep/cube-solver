"""Build the complete compact Super Floppy distance asset using wavefronts."""
from pathlib import Path
import sys,zlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.super_floppy import system,ATOMS,AXES

def build():
 *_,maps,placements,start=system()
 size=3041280;dist=np.full(size,255,dtype=np.uint8);dist[start]=0
 maps=tuple(np.asarray(m,dtype=np.int32) for m in maps)
 front=np.array([start],dtype=np.int32);depth=0;total=1
 while len(front):
  depth+=1;pending=[];ranks=front//256;bits=front%256
  for j,move in enumerate(ATOMS):
   targets=maps[j][ranks];valid=targets>=0
   shift=AXES.index(move.axis)*2
   target_bits=(bits&~(3<<shift))|((((bits>>shift)+move.amount)&3)<<shift)
   nxt=targets[valid]*256+target_bits[valid]
   nxt=nxt[dist[nxt]==255]
   if len(nxt):dist[nxt]=depth;pending.append(nxt)
  front=np.concatenate(pending) if pending else np.array([],dtype=np.int32)
  total+=len(front);print(depth,len(front),total,flush=True)
 if total!=size or int(dist.max())!=15:raise ValueError('Super Floppy graph does not match the original mechanism')
 path=Path(__file__).resolve().parents[1]/'solver/data/super_floppy.bin'
 path.write_bytes(b'SF01'+zlib.compress(dist.tobytes(),9));print(path,path.stat().st_size,flush=True)

if __name__=='__main__':build()
