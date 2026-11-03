"""Small exact projected distances for corner-normalized macro search."""
from pathlib import Path
from itertools import product
import json
import struct
import sys
from time import monotonic
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from solver.camouflage_reduction import model
from solver.camouflage_octants import catalogue,fingerprint


def main(kind='camouflage_3'):
    start=monotonic();g=model(kind);words,actions,masks,_=catalogue(kind)
    from cube.cuboid import layout
    cells=layout(kind)[0]
    domains=[tuple(sorted({g.aliases[p][pose] for pose in row})) for p,row in enumerate(g.feasible)]
    variable=[p for p,row in enumerate(domains) if len(row)>1 and not all((p%8)*24+f in g.goals[p] for f in row)]
    heavy=tuple(p for p in variable if len(cells[p])==4)
    if kind=='mirror_camouflage_3':
        from cube.cuboid import CuboidCube
        base=CuboidCube.solved(kind).geometry
        panel_counts={p:len(base.pieces[p]) for p in variable}
        edges=tuple(p for p in variable if panel_counts[p]==2 and p not in heavy)
        centres=tuple(p for p in variable if panel_counts[p]==1)
    else:
        edges=tuple(p for p in variable if len(g.goals[p])==1 and p not in heavy)
        centres=tuple(p for p in variable if len(g.goals[p])>1)
    assert len(heavy)==3 and len(edges)==9 and len(centres)==6
    patterns=tuple(heavy+(p,) for p in edges)
    patterns+=tuple(heavy[:2]+centres[i:i+2] for i in range(0,6,2))
    patterns+=tuple(tuple(centres[(i+j)%6] for j in range(4)) for i in (0,2,4))
    rows=[];blob=bytearray()
    for pieces in patterns:
        poses=[domains[p] for p in pieces];radices=[len(row) for row in poses]
        weights=[];count=1
        for size in reversed(radices):weights.insert(0,count);count*=size
        inverse=[{(p%8)*24+pose:i for i,pose in enumerate(row)} for p,row in zip(pieces,poses)]
        unique={}
        for action in actions:
            tables=tuple(bytes(255 if (dest:=action[p//8][(p%8)*24+pose])==255 else inverse[j][dest]
                               for pose in row) for j,(p,row) in enumerate(zip(pieces,poses)))
            unique.setdefault(tables,None)
        tables=[tuple(np.frombuffer(row,dtype=np.uint8) for row in table) for table in unique]
        distance=np.full(count,255,dtype=np.uint8)
        goal_positions=[tuple(i for i,pose in enumerate(row) if (p%8)*24+pose in g.goals[p]) for p,row in zip(pieces,poses)]
        frontier=np.array([sum(i*w for i,w in zip(values,weights)) for values in product(*goal_positions)],dtype=np.int32)
        distance[frontier]=0;depth=0;edges_checked=0
        while len(frontier):
            decoded=[frontier//w%radix for w,radix in zip(weights,radices)];following=[]
            for table in tables:
                mapped=[row[index] for row,index in zip(table,decoded)]
                valid=np.logical_and.reduce([row!=255 for row in mapped]);edges_checked+=int(np.count_nonzero(valid))
                dest=sum(row.astype(np.int32)*w for row,w in zip(mapped,weights))[valid]
                dest=np.unique(dest[distance[dest]==255])
                if len(dest):distance[dest]=depth+1;following.append(dest)
            frontier=np.concatenate(following) if following else np.array([],dtype=np.int32);depth+=1
        row=dict(pieces=pieces,poses=poses,size=count,reachable=int(np.count_nonzero(distance!=255)),
                 maximum=int(distance[distance!=255].max()),projected_actions=len(tables),checked_edges=edges_checked)
        rows.append(row);blob.extend(distance.tobytes())
        print(len(rows),len(patterns),row['reachable'],row['maximum'],'seconds',round(monotonic()-start,3),flush=True)
    header=dict(version=1,geometry=fingerprint(kind),patterns=rows)
    encoded=json.dumps(header,separators=(',',':')).encode()
    path=Path(__file__).resolve().parents[1]/f'solver/data/{kind}_quotient_patterns.bin'
    path.write_bytes(b'CQ01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(blob,9))
    print('saved',path.stat().st_size,'bytes',len(blob),'decoded bytes',flush=True)


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'camouflage_3')
