"""Audit current public material scrambles without changing puzzle rules.

Same-colour equivariance is evidence of a restricted action subgroup, not
proof of a manufactured puzzle defect. A separately legal closed word must
break it before this audit labels the restriction a demonstrated omission.
"""
import sys,json,importlib
from pathlib import Path
from collections import Counter
from itertools import combinations,product
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import Move,dot
from cube.curvy_copter import JUMBLE
OUT=Path('reports/optimization/2026-11-02/scramble-coupling-audit')

CASES=(
 ('helicopter','cube.edge_jumbling','HelicopterCube',None),
 ('rua','cube.edge_jumbling','RuaCube',None),
 ('clover','cube.spherical_jumbling','CloverCube',None),
 ('mf8_bauhinia_minx','cube.spherical_jumbling','BauhiniaCube',None),
 ('helicopter_14','cube.edge_jumbling','Helicopter14Cube','cube.helicopter_14_aligned'),
 ('lanlan_curvy_copter','cube.copter_input','CopterCube','cube.copter_aligned'),
 ('lanlan_flower_copter','cube.flower_copter','FlowerCopterCube','cube.flower_copter_aligned'),
 ('lanlan_butterflower','cube.butterflower','ButterflowerCube','cube.butterflower_aligned'),
 ('mf8_suncube_2','cube.suncube','SunCube','cube.suncube_aligned'),
 ('lanlan_comet_physical','cube.lanlan_comet','LanlanCometCube','cube.lanlan_comet_aligned'),
 ('lanlan_hexagram','cube.hexagram','HexagramCube','cube.hexagram_aligned'),
 ('mf8_twins','cube.twins_pcubes','TwinsPCubesState','cube.twins_pcubes_aligned'),
)


def orbit_data(cube,actions):
    goal=cube.paints;left=set(range(len(goal)));orbits=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for s in queue:
            for p in actions:
                if p[s] not in orbit:orbit.add(p[s]);queue.append(p[s])
        orbits.append(tuple(sorted(orbit)));left-=orbit
    counts=Counter(h for h,f,p in cube.panels);representatives=[];pairs=[]
    for orbit in orbits:
        if len({goal[s] for s in orbit})<2:continue
        if any(counts[cube.panels[s][0]]!=1 for s in orbit):continue
        # A hidden pairing can also live inside one orbit when an action
        # swaps the two members; do not only compare two separate orbits.
        for target in orbit[1:]:
            if goal[target]!=goal[orbit[0]]:continue
            mapping={orbit[0]:target};queue=[orbit[0]];valid=True
            for s in queue:
                if goal[s]!=goal[mapping[s]]:valid=False;break
                for p in actions:
                    a,b=p[s],p[mapping[s]]
                    if a in mapping and mapping[a]!=b:valid=False;break
                    if a not in mapping:mapping[a]=b;queue.append(a)
                if not valid:break
            if valid and set(mapping.values())==set(orbit):
                pairs.extend((a,b) for a,b in mapping.items() if a<b and cube.panels[a][0]!=cube.panels[b][0])
        matched=None
        for rep in representatives:
            if len(rep)!=len(orbit):continue
            for target in orbit:
                mapping={rep[0]:target};queue=[rep[0]];valid=True
                for s in queue:
                    if goal[s]!=goal[mapping[s]]:valid=False;break
                    for p in actions:
                        a,b=p[s],p[mapping[s]]
                        if a in mapping and mapping[a]!=b:valid=False;break
                        if a not in mapping:mapping[a]=b;queue.append(a)
                    if not valid:break
                if valid and set(mapping.values())==set(orbit):matched=mapping;break
            if matched is not None:break
        if matched is None:representatives.append(orbit)
        else:pairs.extend(matched.items())
    return orbits,pairs


def probe(cube,actions,pairs,budget=15):
    start=monotonic();orbits,_=orbit_data(cube,actions)
    owner={s:i for i,o in enumerate(orbits) for s in o}
    relation={frozenset(p) for p in pairs};checked=0;found=[];blocked=0
    angle=JUMBLE
    if cube.puzzle_kind=='mf8_bauhinia_minx':
        from cube.spherical_jumbling import BAU_JUMBLE
        angle=BAU_JUMBLE
    # Only a representative target is tested: these profiles have symmetric
    # edge/vertex axes. Absence of a hit is never a completeness claim.
    target=0;axes=cube.turn_axes
    adjacent=[i for i,n in enumerate(axes) if i!=target and dot(n,axes[target])>0]
    def guard():
        if monotonic()-start>budget:raise TimeoutError()
    try:
        for a,b in combinations(adjacent,2):
            for sa,sb in product((-1,1),repeat=2):
                word=(Move(a,0,sa*angle),Move(b,0,sb*angle),Move(target,0,cube.turn_steps[target]),
                      Move(b,0,-sb*angle),Move(a,0,-sa*angle))
                work=cube.clone();checked+=1
                try:
                    for m in word:work.apply_move(m,guard)
                    action=work.aligned_permutation()
                except ValueError:blocked+=1;continue
                broken=[(x,y) for x,y in pairs if frozenset((action[x],action[y])) not in relation]
                crossed=sum(owner[s]!=owner[action[s]] for s in range(len(action)))
                if not broken and not crossed:continue
                inverse=tuple(Move(m.axis,0,-m.amount) for m in reversed(word))
                work.apply_moves(inverse)
                if work.signature()!=cube.signature():raise ValueError('Probe did not reverse complete material')
                found.append(dict(word=[[m.axis,m.layer,m.amount] for m in word],
                                  broken_pairs=broken,crossed_regular_orbit_fields=crossed))
    except TimeoutError:pass
    return dict(candidate_words=checked,blocked_or_unaligned=blocked,seconds=monotonic()-start,
                scope='Bounded five-step geometric probes, not exhaustive or physical rail certification',witnesses=found)


def run():
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    for kind,module,name,provider in CASES:
        start=monotonic();cube=getattr(importlib.import_module(module),name)()
        if provider:
            records=importlib.import_module(provider).generators()
        else:
            records=tuple((cube.clone().apply_move(Move(a,0,t)).aligned_permutation(),(Move(a,0,t),))
                          for a,t in enumerate(cube.turn_steps))
        actions=[p for p,w in records];orbits,pairs=orbit_data(cube,actions)
        row=dict(kind=kind,panels=len(cube.panels),generator_words=len(records),
                 word_lengths=sorted({len(w) for p,w in records}),
                 orbit_sizes=list(map(len,orbits)),same_colour_singleton_pairs=pairs)
        if provider is None or kind=='lanlan_flower_copter':row['probe']=probe(cube,actions,pairs)
        row['seconds']=monotonic()-start;rows.append(row)
        (OUT/'material-models.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(kind,'actions',len(actions),'pairs',len(pairs),'new-word witnesses',len(row.get('probe',{}).get('witnesses',[])),
              'seconds',round(row['seconds'],2),flush=True)


if __name__=='__main__':run()
