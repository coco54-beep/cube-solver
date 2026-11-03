"""Bind the original curved CAD panels to reference bodies, entirely offline."""
import sys,json,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.probe_twins_curved_mapping import map_panels,check_mapping
from cube.twins_pcubes import TwinsPCubesState,fingerprint
from cube.twins_cad_material import structure as cad,fingerprint as cad_fingerprint
from cube.crazy_comet import vertices
from cube.polyhedral import CUBE,triangulate,mean,cross,dot,add,scale,unit
from cube.compound_solids import face_normal


def build():
    mapping=map_panels();checks=check_mapping(mapping)
    if any(row['bad'] for row in checks):raise ValueError('CAD panels do not follow reference exchanges')
    c=TwinsPCubesState();old=cad()[2];rows=[[] for _ in c.solids];panels=[]
    for h,solid in enumerate(c.solids):
        # Keep hidden reference material as black plastic. Its original flat
        # painted faces are replaced by the CAD surface, not drawn underneath.
        for poly,color in solid:
            if color>=0 or any(all(abs(dot(n,p)-1)<1e-7 for p in poly) for n in CUBE):continue
            normal=face_normal(poly)
            rows[h].extend((t,normal,-1) for t in triangulate(poly,normal))
    for slot,(h,f,unused) in enumerate(c.panels):
        poly=old[mapping[slot]][2]
        if dot(face_normal(poly),CUBE[f])<0:poly=poly[::-1]
        panels.append((h,f,poly))
        rows[h].extend((t,CUBE[f],slot) for t in triangulate(poly,CUBE[f]))
        # Close the decorative patch behind its curved boundary. These black
        # display backs avoid holes when opened; they do not define hidden
        # tracks or override the reference material's whole-piece move gates.
        centre=mean(vertices(c.solids[h]))
        for a,b in zip(poly,poly[1:]+poly[:1]):
            n=cross(add(b,scale(a,-1)),add(centre,scale(a,-1)))
            if dot(n,n)<1e-18:continue
            rows[h].append(((a,b,centre),unit(n),-1))
    value=dict(version=1,source=fingerprint(),cad_source=cad_fingerprint(),
               panels=panels,surfaces=rows,mapping=[mapping[i] for i in range(192)])
    target=Path('cube/data/twins_pcubes_skin.bin')
    target.write_bytes(zlib.compress(json.dumps(value,separators=(',',':')).encode(),9))
    print(json.dumps(dict(panels=len(panels),bodies=len(rows),triangles=sum(map(len,rows)),
                          bytes=target.stat().st_size,certified_generators=len(checks)),indent=2))


if __name__=='__main__':build()
