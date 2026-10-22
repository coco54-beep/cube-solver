"""Build portable Mixup geometry groups from source-independent legal loops.

Requires SymPy only on the development machine. No observation fixtures,
source scramble histories or input-specific solutions are read by this tool."""
import json
import sys
from pathlib import Path
from time import monotonic
from itertools import chain
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.articulated_observation import polygon_key
from solver.mixup_reduction import geometry,greedy_geometry,restore_layout
from cube.mixup import MixupSliceMove
from cube.polyhedral import Move
from cube.appearance import ROTATIONS,transform_frame
from sympy.combinatorics import Permutation,PermutationGroup


def build(kind):
    model=geometry(kind);cube=model.cube;root=(0,)*len(cube.solids);fs,key,_=model.describe(root)
    atoms=[];homes=[];slots={}
    for h in range(len(root)):
        indices=[]
        for poly,colour in cube.placed_faces(h):
            if colour<0:continue
            indices.append(len(atoms));slots[polygon_key(poly)]=len(atoms);atoms.append((h,colour))
        homes.append(tuple(indices))
    poses={}
    def permutation(frames):
        dest=list(range(len(atoms)))
        for h,p in enumerate(frames):
            if (h,p) not in poses:
                poses[h,p]=tuple(slots.get(polygon_key(poly),-1) for poly,col in cube.placed_faces(h,p) if col>=0)
            for src,target in zip(homes[h],poses[h,p]):
                if target<0:return None
                dest[src]=target
        return Permutation(dest)
    unique={};begun=monotonic()
    singles=((ch,model.describe(ch)[0],(mv,)) for ch,mv in model.children(root,fs) if mv.amount in (2,4,6))
    for child,ff,word in chain(singles,model.macro_children(root,fs),model.proper_macro_children(root,fs,long=True),model.long_macro_children(root,fs)):
        if model.describe(child)[1]!=key:continue
        perm=permutation(child)
        if perm is None or perm.is_Identity:continue
        sig=tuple(perm.array_form)
        if sig not in unique or len(unique[sig][1])>len(word):unique[sig]=perm,word
    print(kind,'loops',len(unique),'time',round(monotonic()-begun,2),flush=True)
    # Include ordinary cubical commutators in every spatial orientation. They
    # keep a reduced edge's attached inner strips together and avoid deriving
    # those small actions from enormous stabilizer expressions.
    formulas=("M2 U M U2 M' U M2","R U R' U R U2 R'","R U' L' U R' U' L U",
              "R U R' U' R' F R2 U' R' U' R U R' F'", "R U R' F' R U R' U' R' F R2 U' R'")
    for formula in formulas:
        for rotation in ROTATIONS:
            word=[]
            for token in formula.split():
                face=token[0];axis,sign={'R':(0,1),'L':(0,-1),'U':(1,1),'D':(1,-1),'F':(2,1),'B':(2,-1),'M':(0,-1)}[face]
                direction=transform_frame(rotation,tuple(sign if a==axis else 0 for a in range(3)))
                axis=max(range(3),key=lambda a:abs(direction[a]));sign=round(direction[axis]);amount=(-2*sign*(2 if '2' in token else -1 if "'" in token else 1))%8
                if face=='M':
                    layers=tuple(range(1,len(model.cuts[axis])))
                    move=Move(axis,1,amount) if len(layers)==1 else MixupSliceMove(axis,1,amount,layers)
                else:move=Move(axis,len(model.cuts[axis]) if sign>0 else 0,amount)
                word.append(move)
            trial=root,fs
            for move in word:
                trial=model.apply(*trial,move)
                if trial is None:break
            if trial is None or model.describe(trial[0])[1]!=key:continue
            perm=permutation(trial[0]);signature=tuple(perm.array_form)
            if signature not in unique or len(unique[signature][1])>len(word):unique[signature]=perm,tuple(word)
    # Schreier loops through neighbouring cube-shaped partitions include
    # split-layer cycles absent from a catalogue of fixed short commutators.
    from collections import deque
    states={key:(root,fs,())};pending=deque((key,))
    while pending:
        current=pending.popleft();state,features,prefix=states[current]
        singles=((ch,model.describe(ch)[0],(mv,)) for ch,mv in model.children(state,features) if mv.amount in (2,4,6))
        for child,cf,word in chain(singles,model.macro_children(state,features)):
            if any(f[1] for f in cf):continue
            ck=model.describe(child)[1]
            if ck not in states:
                if len(states)<64:states[ck]=(child,cf,prefix+word);pending.append(ck)
                continue
            inverse=tuple(m.inverse(8) for m in reversed(states[ck][2]));closed=child,cf
            for move in inverse:
                closed=model.apply(*closed,move)
                if closed is None:break
            if closed is None:continue
            perm=permutation(closed[0])
            if perm is None or perm.is_identity:continue
            loop=prefix+word+inverse;signature=tuple(perm.array_form)
            if signature not in unique or len(unique[signature][1])>len(loop):unique[signature]=perm,loop
    print(' graph loops',len(unique),'states',len(states),'time',round(monotonic()-begun,2),flush=True)
    import random
    rng=random.Random(1701)
    for sample in range(8):
        state=root;features=fs;word=[]
        for step in range(10):
            choices=[(ch,mv) for ch,mv in model.children(state,features) if mv.amount in (2,4,6)]
            if not choices:break
            state,mv=rng.choice(choices);features=model.describe(state)[0];word.append(mv)
        trial=cube.clone();trial.colors=state
        try:closing,trial,_=restore_layout(trial,seconds=15.)
        except ValueError:continue
        perm=permutation(trial.frames)
        if perm is not None and not perm.is_identity:
            unique[tuple(perm.array_form)]=perm,tuple(word)+closing
            print(' sampled geometry loop',sample,len(word)+len(closing),flush=True)
    # The odd Mixup slice cycle changes the parity sector and is absent from
    # commutators. Close its geometry independently of any test state.
    for axis in range(3):
        done=False
        for axis2 in range(3):
            if axis==axis2:continue
            def middle(a,amount):
                layers=tuple(range(1,len(model.cuts[a])))
                return Move(a,1,amount) if len(layers)==1 else MixupSliceMove(a,1,amount,layers)
            word=tuple(m for i in range(5) for m in (middle(axis,2 if i%2==0 else 6),middle(axis2,1)))
            trial=cube.clone()
            try:
                trial.apply_moves(word);a,trial,_=greedy_geometry(trial,seconds=5.);b,trial,_=restore_layout(trial,seconds=5.)
            except ValueError:continue
            perm=permutation(trial.frames)
            if perm is None:continue
            unique[tuple(perm.array_form)]=perm,word+a+b;done=True
            print(' parity loop',len(word+a+b),flush=True);break
        if done:break
    pairs=sorted(unique.values(),key=lambda p:(len(p[0].support()),len(p[1])))
    generators=[p for p,w in pairs];words=[w for p,w in pairs]
    selected=[];group=None
    for p in generators:
        if group is None or not group.contains(p):
            selected.append(p);group=PermutationGroup(selected);group.schreier_sims()
    print(' independent generators',len(selected),'of',len(generators),flush=True)
    base=[a for role in ('centre','inner_edge','edge','corner') for h,solid in enumerate(cube.solids) if solid.role==role for a in homes[h]]
    group._schreier_sims(base=base)
    print(' group order',group.order(),flush=True)
    import zlib
    strong=list(group.strong_gens)+[g for g in generators if g not in group.strong_gens]
    lookup={g:i+1 for i,g in enumerate(strong)}
    def reference(g):return lookup[g] if g in lookup else -lookup[g**-1]
    originals={g:i for i,g in enumerate(generators)}
    records=[]
    for g in strong:
        records.append({'permutation':g.array_form,'original':originals.get(g),
                        'product':[] if g in originals else [reference(s) for s in group._strong_gens_slp[g]]})
    from solver.mixup_group import TABLE_VERSION,geometry_fingerprint
    table={'version':TABLE_VERSION,'geometry':geometry_fingerprint(kind),'kind':kind,'degree':len(atoms),'base':group.base,
           'moves':[[[m.axis,m.layer,m.amount,list(getattr(m,'layers',()))] for m in w] for w in words],
           'strong':records,
           'transversals':[{str(beta):{'permutation':p.array_form,'product':group._transversal_slp[i][beta]}
                            for beta,p in orbit.items()} for i,orbit in enumerate(group.basic_transversals)]}
    out=Path('artifacts/development');out.mkdir(parents=True,exist_ok=True)
    (out/(kind+'-group.bin')).write_bytes(zlib.compress(json.dumps(table,separators=(',',':')).encode(),9))
    from collections import Counter
    print(' derived types',Counter(tuple(sorted(len(c) for c in g.cyclic_form)) for g in group.strong_gens if g not in originals),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind')
    parser.add_argument('--install',action='store_true')
    args=parser.parse_args()
    build(args.kind)
    from optimize_mixup_group_tables import optimize
    optimize(args.kind)
    if args.install:
        import shutil
        shutil.copyfile(Path('artifacts/development')/(args.kind+'-short-group.bin'),
                        Path('solver/data')/(args.kind+'_group.bin'))
