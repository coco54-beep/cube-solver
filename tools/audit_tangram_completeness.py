"""Certify that the prepared Tangram root groups cover the whole legal model.

Extreme's middle 60-degree turn exchanges two available-axis sets. Fixed
actions are certified in the phase-zero fibre, including conjugated actions
from phase one. Exact setwise stabilizer search certifies the compiled root
group. The middle turn bijects the two fibres; the complete shape orbit has
8*C(12,6)^3 states. This certifies the software's geometric mechanism, not
physical manufacturing tolerances or unmodelled internal rails.
"""
import sys
import json
import hashlib
import zlib
from math import factorial,comb,prod
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation,PermutationGroup
from cube.articulated_observation import polygon_key
from solver.tangram_geometry import geometry
from solver.tangram_table import load_table,geometry_fingerprint
from tools.build_tangram_shape_patterns import projected_states
from cube.polyhedral import Move


def phase_words(model):
    """Fixed actions in the phase-zero fibre of the moving-axis mechanism.

    A middle 60-degree turn T exchanges the available edge-axis sets. The
    second phase's edge actions are represented by T A T^-1. Every closed
    word can be rewritten into these actions; the omitted T is the phase.
    """
    t=Move(6,1,1);back=t.inverse(6)
    words=[(m,) for m in model.moves if m.axis<3 or
           (m.axis==6 and (m.layer!=1 or m.amount%2==0))]
    words += [(t,Move(a,0,3),back) for a in range(3,6)]
    lookup={w:i for i,w in enumerate(words)}
    def refs(word):
        phase=0;result=[]
        for m in word:
            if m.axis==6 and m.layer==1:
                total=phase+m.amount
                amount=2*(total//2)%6
                if amount:result.append(lookup[(Move(6,1,amount),)])
                phase=total%2
            else:result.append(lookup[(t,m,back) if phase and m.axis<6 else (m,)])
        assert phase==0,'Root stabilizer word changed axis phase'
        return result
    return words,refs


def run(kind):
    model=geometry(kind);root=tuple(model.cube.frames);allowed=set(model.shape(root))
    if kind=='tangram_extreme':words,refs=phase_words(model)
    else:
        words=[(m,) for m in model.moves]
        refs=lambda word:[model.move_indices[m] for m in word]
    representatives={}
    for (h,p),(sid,*_) in model.features.items():representatives.setdefault(sid,(h,p))
    def follow(h,p,word):
        for m in word:
            i=model.move_indices[m];sid,blocked,selected=model.features[h,p]
            assert not blocked>>i&1,'A phase-zero action crosses material'
            if selected>>i&1:p=model.turns[p,m]
        return p
    while True:
        following=set(allowed)
        for sid in allowed:
            h,p=representatives[sid]
            for word in words:following.add(model.features[h,follow(h,p,word)][0])
        if following==allowed:break
        allowed=following
    keys={};samples={};core=set();origins={}
    for (h,pose),(sid,*_) in model.features.items():
        if sid not in allowed:continue
        for j,(poly,colour) in enumerate(model.cube.placed_faces(h,pose)):
            if colour<0:continue
            key=sid,polygon_key(poly);keys.setdefault(key,len(keys));samples.setdefault(key,(h,pose,j))
            if model.cube.solids[h].role=='band' or len({c for poly,c in model.cube.solids[h].faces if c>=0})>=3:core.add(keys[key])
            if pose==0:origins[keys[key]]=colour
    skin_count=len(keys);sids={s:i+skin_count for i,s in enumerate(sorted(allowed))};perms=[]
    for word in words:
        p=[-1]*(skin_count+len(sids))
        # Check every home/pose occurrence, not only one representative key.
        for (h,pose),(sid,forbidden,selected) in model.features.items():
            if sid not in allowed:continue
            q=follow(h,pose,word)
            before=model.cube.placed_faces(h,pose);after=model.cube.placed_faces(h,q)
            for (poly,c),(target,tc) in zip(before,after):
                if c<0:continue
                a=keys[sid,polygon_key(poly)];b=keys[model.features[h,q][0],polygon_key(target)]
                assert p[a] in (-1,b);p[a]=b
        for sid in allowed:
            h,q=representatives[sid];p[sids[sid]]=sids[model.features[h,follow(h,q,word)][0]]
        assert sorted(p)==list(range(len(p)));perms.append(tuple(p))
    full=PermutationGroup([Permutation(p) for p in perms]);full_order=full.order()
    old=load_table(kind);loops=[];root_atoms={}
    for h in range(len(model.cube.solids)):
        for poly,colour in model.cube.placed_faces(h):
            if colour>=0:root_atoms[old.slots[polygon_key(poly)]]=keys[model.features[h,0][0],polygon_key(poly)]
    atom_at={value:key for key,value in root_atoms.items()}
    root_occupied=set(origins)|{sids[s] for s in model.shape(root)}
    for j,record in enumerate(old.records):
        p=tuple(range(len(perms[0])))
        for index in refs(old.strong_word(j+1)):
            turn=perms[index];p=tuple(turn[a] for a in p)
        assert {p[a] for a in root_occupied}==root_occupied
        assert tuple(atom_at[p[root_atoms[a]]] for a in range(old.degree))==tuple(record['permutation'])
        loops.append(Permutation(p))
    root_group=PermutationGroup(loops);root_order=root_group.order()
    shape_orbit=1;detail={}
    if kind == 'tangram_extreme':
        # Certify the exact setwise stabilizer instead of assuming that the
        # old model's A12 kernel still applies after the material correction.
        occupied=frozenset(root_occupied)
        base,strong=full.schreier_sims_incremental(base=sorted(occupied))
        def preserves(p):return all((a in occupied)==(p(a) in occupied) for a in range(full.degree))
        tests=[(lambda words,level=i,points=tuple(base[:i+1]):all((a in occupied)==(words[level](a) in occupied) for a in points))
               for i in range(len(base))]
        print('certifying set stabilizer',full.degree,'base',len(base),'known order',root_order,flush=True)
        exact=full.subgroup_search(preserves,base=base,strong_gens=strong,tests=tests,init_subgroup=root_group)
        assert exact.order()==root_order,'Prepared root algorithms do not cover the physical stabilizer'
        phase_zero_order=full_order
        assert phase_zero_order%root_order==0
        full_order*=2
        shape_orbit=2*(phase_zero_order//root_order)
        detail=dict(phase_zero_action_order=str(phase_zero_order),axis_phase_count=2,
                    stabilizer_certificate='exact setwise subgroup search with partial-base pruning',
                    action_scope='two phase fibres; fixed-action group certified in phase zero')
    assert full_order==root_order*shape_orbit
    # Prove the stored transversals cover the exact visible root group.
    visible=PermutationGroup([Permutation(r['permutation']) for r in old.records]);visible._schreier_sims(base=old.base)
    assert visible.order()==root_order
    path=Path('solver/data')/(kind+'_group.bin');data=json.loads(zlib.decompress(path.read_bytes()));checked=0
    for level,(point,orbit) in enumerate(zip(data['base'],data['transversals'])):
        assert {int(beta) for beta in orbit}==set(visible.basic_orbits[level])
        for beta,entry in orbit.items():
            p=tuple(range(old.degree))
            for ref in reversed(entry['product']):
                turn=old.records[ref]['permutation'];p=tuple(turn[a] for a in p)
            assert p==tuple(entry['permutation']) and p[point]==int(beta)
            assert all(p[a]==a for a in data['base'][:level]);checked+=1
    report=dict(kind=kind,geometry=geometry_fingerprint(kind),reachable_shape_positions=len(allowed),
                coloured_position_degree=skin_count,all_moves_legal_on_reachable_positions=True,
                full_move_group_order=str(full_order),complete_shape_orbit=shape_orbit,
                full_root_stabilizer_order=str(root_order),verified_transversals=checked,
                asset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**detail)
    print(json.dumps(report),flush=True);return report


if __name__=='__main__':
    rows=[run(kind) for kind in ('tangram','tangram_extreme')]
    Path('reports/solver-audit/2026-10-23/tangram-completeness-proof.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
