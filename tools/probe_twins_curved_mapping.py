"""Check whether the original CAD face patches can follow reference bodies."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon
from cube.twins_cad_material import structure as cad
from cube.twins_pcubes import TwinsPCubesState
from cube.twins_pcubes_aligned import generators
from cube.appearance import transform_frame
from cube.polyhedral import CUBE,dot


def flat(poly,face):
    indices=[i for i,x in enumerate(CUBE[face]) if not x]
    return Polygon([tuple(p[i] for i in indices) for p in poly])


def map_panels():
    c=TwinsPCubesState();old=cad()[2];mapping={};score=[]
    for face in range(6):
        ns=[i for i,(h,f,p) in enumerate(c.panels) if f==face]
        os=[i for i,(h,f,p) in enumerate(old) if f==face]
        cost=np.array([[-flat(c.panels[n][2],face).intersection(flat(old[o][2],face)).area
                        for o in os] for n in ns])
        ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):mapping[ns[i]]=os[j];score.append(float(-cost[i,j]))
    return mapping


def check_mapping(mapping):
    c=TwinsPCubesState();old=cad()[2];rows=[]
    for action,word in generators():
        work=c.clone().apply_moves(word);bad=[]
        for n,target in enumerate(action):
            home=c.panels[n][0];p=old[mapping[n]][2];dest=old[mapping[target]]
            moved=tuple(transform_frame(work.frames[home],v) for v in p)
            normal=transform_frame(work.frames[home],CUBE[old[mapping[n]][1]])
            face=max(range(6),key=lambda f:dot(normal,CUBE[f]))
            distance=flat(moved,face).hausdorff_distance(flat(dest[2],dest[1])) if face==dest[1] else 100.
            if distance>2e-5:bad.append((n,target,distance))
        rows.append(dict(length=len(word),bad=len(bad),examples=bad[:2]))
    return rows


def main():
    mapping=map_panels();rows=check_mapping(mapping)
    out=Path('reports/optimization/2026-11-02/twins-curved-reference');out.mkdir(parents=True,exist_ok=True)
    result=dict(mapping=mapping,generators=rows)
    (out/'mapping-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(bad_generators=sum(bool(r['bad']) for r in rows),rows=rows),indent=2))


if __name__=='__main__':main()
