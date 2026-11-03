"""Reconstruct source XML parameters in Python; never execute embedded pCubes code."""
import sys,json,zlib,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.twins_material import structure,EDGE_CUT
from cube.polyhedral import EDGE_AXES,Move,dot,scale,key
from cube.appearance import ROTATIONS,transform_frame
from cube.curvy_copter import JUMBLE
from cube.twins_state import SECOND


def build():
    root=Path(__file__).resolve().parents[1]
    source=root/'bin/pCubes/Puzzles/Other cubes/Mixed/Edge-Vertex/Skewby Twins.xml'
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    from cube.twins_pcubes import XML_SHA256
    if source_hash!=XML_SHA256:raise ValueError('Source parameters changed; recheck the Python reconstruction first')
    solids,unused=structure();following=[];hidden_fields=0
    for solid in solids:
        # Source HideContaining(0) leaves the inner body unpainted; its six
        # exterior openings are black plastic, not six extra coloured centres.
        inner=all(dot(n,p)<=EDGE_CUT+1e-8 for poly,f in solid for p in poly for n in EDGE_AXES)
        row=[]
        for poly,f in solid:
            if inner and f>=0:hidden_fields+=1;f=-1
            row.append((tuple(scale(p,2.) for p in poly),f))
        following.append(tuple(row))
    panels=tuple((h,f,p) for h,s in enumerate(following) for p,f in s if f>=0)
    if hidden_fields!=6 or len(panels)!=192:raise ValueError('Unexpected source colour-shell partition')
    source_key=hashlib.sha256((source_hash+'-source-contacts-hide-inner-v1').encode()).hexdigest()
    data=dict(version=1,profile='pcubes-skewby-twins-coloured-shell-v1',source=source_key,
              xml_sha256=source_hash,solids=following,panels=panels)
    target=root/'cube/data/twins_pcubes_material.bin'
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    from cube.twins_pcubes import TwinsPCubesState,AXES
    base=TwinsPCubesState();indices={key(n):i for i,n in enumerate(AXES)};found={}
    seven=tuple(Move(a,0,t) for a,t in ((0,SECOND),(8,SECOND),(10,SECOND),(14,120.),(10,-SECOND),(8,-SECOND),(0,-SECOND)))
    # Source Random3, with negative caps expressed by the opposite oriented axis.
    nine=tuple(Move(a,0,t) for a,t in ((4,-JUMBLE),(7,JUMBLE-180),(3,-JUMBLE),(11,JUMBLE-180),(9,-180.),(11,180-JUMBLE),(3,JUMBLE),(7,180-JUMBLE),(4,JUMBLE)))
    for frame in ROTATIONS:
        mapped=tuple(indices[key(transform_frame(frame,n))] for n in AXES)
        for seed in (seven,nine):
            word=tuple(Move(mapped[m.axis],0,m.amount) for m in seed)
            work=base.clone().apply_moves(word);action=work.aligned_permutation()
            inverse=tuple(Move(m.axis,0,-m.amount) for m in reversed(word))
            if work.apply_moves(inverse).signature()!=base.signature():raise ValueError('Interior did not reverse')
            found.setdefault(action,word)
    payload=dict(version=1,source=source_key,rows=[dict(action=p,word=[[m.axis,m.layer,m.amount] for m in w]) for p,w in found.items()])
    out=root/'cube/data/twins_pcubes_exchanges.bin'
    out.write_bytes(zlib.compress(json.dumps(payload,separators=(',',':')).encode(),9))
    print('Material',len(base.solids),'pieces',len(base.panels),'fields',target.stat().st_size,'bytes; exchanges',len(found),out.stat().st_size,'bytes',flush=True)


if __name__=='__main__':build()
