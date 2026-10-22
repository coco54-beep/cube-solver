"""Portable stabilizer-chain words for the Mixup geometry boundary.

Tables are generated from legal physical loops. Runtime needs only the standard
library; SymPy is used by the offline builder, never by the app.
"""
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path
import zlib
import hashlib

from cube.articulated_observation import polygon_key
from cube.mixup import Move,MixupSliceMove
from solver.mixup_reduction import geometry

TABLE_VERSION=1


def geometry_fingerprint(kind):
    cube=geometry(kind).cube
    payload=(cube._bands(),tuple((s.role,s.anchor,s.faces) for s in cube.solids),cube.orientations)
    def stable(value):
        if isinstance(value,float):return round(value,8) or 0.0
        if isinstance(value,(tuple,list)):return tuple(stable(v) for v in value)
        return value
    return hashlib.sha256(json.dumps(stable(payload),separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=2)
def load_group(kind):
    path=Path(__file__).resolve().parent/'data'/(kind+'_group.bin')
    if not path.exists():raise ValueError('mixup.shape_limit')
    return GeometryGroup(kind,path)


def compact(moves):
    result=[]
    for move in moves:
        if result and (result[-1].axis,result[-1].layer,getattr(result[-1],'layers',()))==(move.axis,move.layer,getattr(move,'layers',())):
            old=result.pop();amount=(old.amount+move.amount)%8
            if amount:
                move=(MixupSliceMove(move.axis,move.layer,amount,move.layers) if getattr(move,'layers',()) else Move(move.axis,move.layer,amount))
            else:continue
        result.append(move)
    return tuple(result)


def erase_coloured_loops(cube,moves,cancel=None):
    """Drop excursions which return every visible rigid piece to its state.

    Equal-coloured identical pieces need no invisible identity bookkeeping.
    The final independent physical replay still verifies every retained turn.
    """
    model=geometry(cube.puzzle_kind);lookup={};cache={}
    from cube.appearance import transform_frame
    def state_key(frames):
        ids=[]
        for h,pose in enumerate(frames):
            hp=h,pose
            if hp not in cache:
                solid=cube.solids[h];faces=cube.placed_faces(h,pose)
                panels=tuple(sorted((colour,polygon_key(poly)) for poly,colour in faces if colour>=0))
                body=tuple(sorted(polygon_key(poly) for poly,col in faces)) if solid.role=='inner_edge' else ()
                anchor=tuple(round(x,6) for x in transform_frame(cube.orientations[pose],solid.anchor))
                key=solid.role,panels,body,anchor
                if key not in lookup:lookup[key]=len(lookup)
                cache[hp]=lookup[key]
            ids.append(cache[hp])
        return tuple(sorted(ids))
    frames=tuple(cube.frames);features=model.describe(frames)[0]
    initial=state_key(frames);keys=[initial];seen={initial:0};result=[]
    for move in moves:
        if cancel and cancel():raise InterruptedError()
        trial=model.apply(frames,features,move)
        if trial is None:raise ValueError('mixup.replay_failed')
        frames,features=trial;key=state_key(frames)
        if key in seen:
            at=seen[key]
            for old in keys[at+1:]:seen.pop(old,None)
            del keys[at+1:];del result[at:]
        else:
            result.append(move);keys.append(key);seen[key]=len(result)
    return compact(result)


class GeometryGroup:
    def __init__(self,kind,path):
        self.kind=kind;self.model=geometry(kind)
        table=json.loads(zlib.decompress(Path(path).read_bytes()))
        if (table['kind']!=kind or table.get('version')!=TABLE_VERSION
                or table.get('geometry')!=geometry_fingerprint(kind)):raise ValueError('mixup.shape_limit')
        self.base=table['base'];self.records=table['strong'];self.degree=table['degree']
        self.words=tuple(tuple(self.move(v) for v in word) for word in table['moves'])
        self.transversals=[]
        for level in table['transversals']:
            entries={}
            for beta,item in level.items():
                inverse=[0]*self.degree
                for source,dest in enumerate(item['permutation']):inverse[dest]=source
                entries[int(beta)]=(tuple(inverse),tuple(item['product']))
            self.transversals.append(entries)
        self.homes=[];self.slots={};self.pose_images={};self._words={};self._costs={}
        self.desired=[];self.groups={}
        cube=self.model.cube
        from cube.articulated import MIXUP_MODELS
        from cube.articulated_observation import project
        from cube.polyhedral import CUBE,dot,mean
        dimensions,plus=MIXUP_MODELS[kind];self.order=4 if dimensions==(4,4,4) else 3
        depth=(2*2**.5-1)/7 if plus else 2**.5-1
        cuts=(-depth,0.,depth) if self.order==4 else (-depth,depth)
        for home in range(len(cube.solids)):
            atoms=[]
            for poly,colour in cube.placed_faces(home):
                if colour<0:continue
                atom=len(self.slots);atoms.append(atom);self.slots[polygon_key(poly)]=atom;self.desired.append(colour)
                x,y=mean(tuple((u,v,0.) for u,v in project(poly,colour)))[:2]
                row=sum(-y>b+1e-7 for b in cuts);col=sum(x>b+1e-7 for b in cuts)
                self.groups.setdefault((colour,row,col),[]).append(atom)
            self.homes.append(tuple(atoms))
        if len(self.slots)!=self.degree:raise ValueError('mixup.shape_limit')

    @staticmethod
    def move(value):
        axis,layer,amount,layers=value
        return MixupSliceMove(axis,layer,amount,tuple(layers)) if layers else Move(axis,layer,amount)

    def strong_word(self,index):
        if index in self._words:return self._words[index]
        record=self.records[abs(index)-1]
        if index<0:word=tuple(m.inverse(8) for m in reversed(self.strong_word(-index)))
        elif 'shortcut' in record:word=tuple(self.move(v) for v in record['shortcut'])
        elif record['original'] is not None:word=self.words[record['original']]
        else:word=compact(m for ref in reversed(record['product']) for m in self.strong_word(ref))
        self._words[index]=word;return word

    def strong_cost(self,index):
        index=abs(index)
        if index in self._costs:return self._costs[index]
        record=self.records[abs(index)-1]
        if 'shortcut' in record:return len(record['shortcut'])
        if record['original'] is not None:return len(self.words[record['original']])
        cost=min(100000,sum(self.strong_cost(ref) for ref in record['product']))
        self._costs[index]=cost;return cost

    def element(self,frames):
        result=[-1]*self.degree
        for home,pose in enumerate(frames):
            if (home,pose) not in self.pose_images:
                self.pose_images[home,pose]=tuple(self.slots.get(polygon_key(p),-1) for p,c in self.model.cube.placed_faces(home,pose) if c>=0)
            for src,dest in zip(self.homes[home],self.pose_images[home,pose]):result[src]=dest
        return tuple(result) if sorted(result)==list(range(self.degree)) else None

    def factors(self,element):
        if element is None:return None
        h=tuple(element);result=[]
        for base,orbit in zip(self.base,self.transversals):
            beta=h[base]
            if beta not in orbit:return None
            inverse,word=orbit[beta];h=tuple(inverse[x] for x in h);result.append(word)
        return result if h==tuple(range(self.degree)) else None

    def equivalent_element(self,element,cancel=None,seconds=2.):
        """Try equivalent labels only as a guide for the coloured search."""
        from time import monotonic
        begun=monotonic();groups={};cube=self.model.cube
        if not hasattr(self,'_atom_orbits'):
            links=list(range(self.degree))
            def find(a):
                while links[a]!=a:links[a]=links[links[a]];a=links[a]
                return a
            for record in self.records:
                if record['original'] is None:continue
                for a,b in enumerate(record['permutation']):links[find(a)]=find(b)
            self._atom_orbits=tuple(find(a) for a in range(self.degree))
        for h,s in enumerate(cube.solids):
            if s.role not in ('centre','inner_edge'):continue
            poly,colour=next((p,c) for p,c in s.faces if c>=0)
            size=tuple(sorted(round(sum((p[a]-q[a])**2 for a in range(3)),6) for i,p in enumerate(poly) for q in poly[i+1:]))
            atom=self.homes[h][0]
            groups.setdefault((self._atom_orbits[atom],s.role,colour,size),[]).append(atom)
        representatives={}
        for (orbit,role,colour,size),group in groups.items():
            if len(group)>1:representatives.setdefault(orbit,tuple(group[:2]))
        reps=tuple(representatives.values())
        for count in range(1,len(reps)+1):
            for changes in combinations(reps,count):
                if cancel and cancel():raise InterruptedError()
                if monotonic()-begun>seconds:return None
                p=list(element)
                for a,b in changes:p[a],p[b]=p[b],p[a]
                if self.factors(p) is not None:return tuple(p)
        swaps=[pair for group in groups.values() for pair in combinations(group,2)]
        for count in (1,2):
            for changes in combinations(swaps,count):
                if cancel and cancel():raise InterruptedError()
                if monotonic()-begun>seconds:return None
                p=list(element)
                for a,b in changes:p[a],p[b]=p[b],p[a]
                if self.factors(p) is not None:return tuple(p)
        return None

    def coherent(self,colours):
        facelets={f:[[None]*self.order for _ in range(self.order)] for f in ('U','R','F','D','L','B')}
        from cube.colors import DEFAULT_COLORS
        faces=tuple(facelets)
        for (face,row,col),atoms in self.groups.items():
            colour=colours[atoms[0]]
            if any(colours[a]!=colour for a in atoms):return False
            facelets[faces[face]][row][col]=DEFAULT_COLORS[faces[colour]]
        if self.order==4:return True
        from solver.solver3 import verify_3x3
        from solver.mixup import valid_center_frame
        try:return valid_center_frame(facelets) and verify_3x3(facelets)[0]
        except (KeyError,ValueError):return False

    def handoff(self,cube,frames,ready):
        if ready is None:return None
        element=self.element(frames)
        if element is None:return None
        colours=[-1]*self.degree
        for source,dest in enumerate(element):colours[dest]=self.desired[source]
        if not self.coherent(colours):return None
        work=cube.clone();work.colors=frames
        try:virtual=ready(work)
        except ValueError:return None
        return work,virtual

    def transport_values(self,values,desired,cancel=None,seconds=15.,node_limit=50000,coherent=None):
        """Transport composite cut patterns, with no physical piece labels."""
        from time import monotonic
        begun=monotonic();seen={};nodes=0;wanted=tuple(desired)
        def visit(level,state,budget):
            nonlocal nodes
            if cancel and cancel():raise InterruptedError()
            nodes+=1
            if monotonic()-begun>seconds or nodes>node_limit:raise ValueError('mixup.shape_limit')
            if state==wanted or coherent is not None and coherent(state):return ()
            if level==len(self.base) or seen.get((level,state),-1)>=budget:return None
            seen[level,state]=budget;base=self.base[level];candidates=[]
            for beta,(inverse,product) in self.transversals[level].items():
                if state[beta]!=wanted[base]:continue
                permutation=[0]*self.degree
                for i,v in enumerate(inverse):permutation[v]=i
                child=tuple(state[permutation[i]] for i in range(self.degree))
                wrong=sum(a!=b for a,b in zip(child,wanted))
                cost=sum(self.strong_cost(ref+1) for ref in product)
                if cost>budget:continue
                unpaired=sum(any(child[a]!=child[atoms[0]] for a in atoms) for atoms in self.groups.values()) if coherent is not None else 0
                candidates.append((unpaired,wrong,cost,beta,child))
            for unpaired,wrong,cost,beta,child in sorted(candidates):
                result=visit(level+1,child,budget-cost)
                if result is not None:return ((level,beta),)+result
            return None
        factors=visit(0,tuple(values),20000)
        if factors is None:raise ValueError('mixup.shape_limit')
        return compact(m for level,beta in factors for ref in self.transversals[level][beta][1]
                       for m in self.strong_word(-(ref+1)))

    def inner_cycles(self,cancel=None):
        """Conjugacy tree for pure cycles of three whole inner assemblies."""
        if hasattr(self,'_inner_cycles'):return self._inner_cycles
        from collections import deque
        from cube.polyhedral import CUBE,dot
        from cube.appearance import transform_frame
        indices=tuple(a for h,s in enumerate(self.model.cube.solids) if s.role=='inner_edge' for a in self.homes[h])
        atoms=set(indices);seeds=[];transport=[]
        def canonical(c):return min(c,c[1:]+c[:1],c[2:]+c[:2])
        options=[]
        for record in self.records:
            original=record['original']
            if original is None:continue
            p=record['permutation'];word=self.words[original];support={i for i,v in enumerate(p) if i!=v}
            if len(word)<=3:transport.append((p,word))
            options.append((p,word))
        def inverse(p):
            result=[0]*len(p)
            for i,v in enumerate(p):result[v]=i
            return result
        # Single physical quarter turns suffice as conjugating transports.
        # Keep short commutators for seeds, then avoid a quadratic BFS fanout.
        seed_transport=list(transport)
        for p,pw in seed_transport:
            pi=inverse(p)
            for q,qw in seed_transport:
                qi=inverse(q);permutation=tuple(qi[pi[q[p[i]]]] for i in range(self.degree))
                options.append((permutation,compact(pw+qw+tuple(m.inverse(8) for m in reversed(pw))+tuple(m.inverse(8) for m in reversed(qw)))))
        if self.kind=='mixup_plus_444':options.extend(self.composite_inner_seeds(cancel))
        protected={a for h,s in enumerate(self.model.cube.solids) if s.role=='edge' for a in self.homes[h]}
        for p,word in options:
            support={i for i,v in enumerate(p) if i!=v and (i in atoms or self.kind!='mixup_plus_444')}
            if len(support)!=3 or not support<=atoms:continue
            if self.kind=='mixup_plus_444' and any(p[a]!=a for a in protected):continue
            if self.kind=='mixup_plus_444':
                a=min(support);seeds.append((canonical((a,p[a],p[p[a]])),word));continue
            frames=(0,)*len(self.model.cube.solids);fs=self.model.describe(frames)[0]
            for move in word:
                trial=self.model.apply(frames,fs,move)
                if trial is None:break
                frames,fs=trial
            else:
                safe=True
                for h,s in enumerate(self.model.cube.solids):
                    if s.role!='centre':continue
                    colour=next(c for poly,c in s.faces if c>=0);normal=CUBE[colour]
                    tangent=next(n for n in CUBE if dot(n,normal)==0)
                    if abs(dot(tangent,transform_frame(self.model.cube.orientations[frames[h]],tangent)))<1-1e-7:safe=False;break
                if safe:
                    a=min(support);seeds.append((canonical((a,p[a],p[p[a]])),word))
        parents={};queue=deque()
        for cycle,word in sorted(seeds,key=lambda item:len(item[1])):
            if cycle not in parents:parents[cycle]=(None,word);queue.append(cycle)
        simple=[(p,w) for p,w in transport if len(w)==1]
        if simple and self.kind=='mixup_plus_444':transport=simple
        while queue:
            if cancel and cancel():raise InterruptedError()
            cycle=queue.popleft()
            for p,word in transport:
                child=canonical(tuple(p[a] for a in cycle))
                if child not in parents:parents[child]=(cycle,word);queue.append(child)
        self._inner_cycles=indices,parents
        return self._inner_cycles

    def composite_inner_seeds(self,cancel=None):
        """Split a whole-inner 3-cycle using a genuine fine-layer conjugate."""
        from collections import deque
        coarse=load_group('mixup_plus_333');_,tree=coarse.inner_cycles(cancel)
        seed=next(word for parent,word in tree.values() if parent is None)
        mapped=[]
        for move in seed:
            layers=(0,) if move.layer==0 else (3,) if move.layer==2 else (1,2)
            mapped.append(Move(move.axis,layers[0],move.amount) if len(layers)==1 else MixupSliceMove(move.axis,1,move.amount,layers))
        frames=(0,)*len(self.model.cube.solids);fs=self.model.describe(frames)[0]
        for move in mapped:
            frames,fs=self.model.apply(frames,fs,move)
        initial=self.element(frames)
        if initial is None:raise ValueError('mixup.shape_limit')
        atoms={a for h,s in enumerate(self.model.cube.solids) if s.role=='inner_edge' for a in self.homes[h]}
        def inv(p):
            result=[0]*len(p)
            for i,v in enumerate(p):result[v]=i
            return result
        transports=[(r['permutation'],self.words[r['original']]) for r in self.records
                    if r['original'] is not None and len(self.words[r['original']])==1]
        queue=deque([(initial,tuple(mapped))]);seen={initial};samples=[];results=[]
        while queue and len(seen)<3000:
            if cancel and cancel():raise InterruptedError()
            p,pw=queue.popleft();ps={a for a in atoms if p[a]!=a};pi=inv(p)
            for q,qw,qs in samples[:64]:
                common=ps&qs
                if len(common)!=1:continue
                qi=inv(q);comm=tuple(qi[pi[q[p[i]]]] for i in range(self.degree))
                support={a for a in atoms if comm[a]!=a}
                if len(support)!=3:continue
                word=compact(pw+qw+tuple(m.inverse(8) for m in reversed(pw))+tuple(m.inverse(8) for m in reversed(qw)))
                results.append((comm,word))
                if len(results)>=12:return results
            samples.append((p,pw,ps))
            for q,qw in transports:
                qi=inv(q);child=tuple(q[p[qi[i]]] for i in range(self.degree))
                if child in seen:continue
                seen.add(child);word=tuple(m.inverse(8) for m in reversed(qw))+pw+qw
                queue.append((child,word))
        if not results:raise ValueError('mixup.shape_limit')
        return results

    def inner_pattern_word(self,current,desired,cancel=None):
        from solver.nxn_orbits import parity,three_cycles
        indices,parents=self.inner_cycles(cancel)
        source=[current[a] for a in indices];target=[desired[a] for a in indices]
        destination=[None]*len(indices);lookup={a:i for i,a in enumerate(indices)};links=list(range(len(indices)))
        def find(i):
            while links[i]!=i:links[i]=links[links[i]];i=links[i]
            return i
        for cycle in parents:
            a,b,c=(lookup[x] for x in cycle);links[find(a)]=find(b);links[find(c)]=find(b)
        orbits={}
        for i in range(len(indices)):orbits.setdefault(find(i),[]).append(i)
        for orbit in orbits.values():
            if sorted(source[i] for i in orbit)!=sorted(target[i] for i in orbit):raise ValueError('mixup.shape_limit')
            available=set(orbit)
            for i in orbit:
                if source[i]==target[i]:destination[i]=i;available.remove(i)
            for i in orbit:
                if destination[i] is None:
                    dest=next(j for j in sorted(available) if target[j]==source[i])
                    destination[i]=dest;available.remove(dest)
            local={i:j for j,i in enumerate(orbit)}
            if parity([local[destination[i]] for i in orbit]):
                a,b=next((a,b) for a in orbit for b in orbit if a>b and source[a]==source[b])
                destination[a],destination[b]=destination[b],destination[a]
        result=[];cycles=[]
        for orbit in orbits.values():
            local={i:j for j,i in enumerate(orbit)}
            cycles.extend(tuple(orbit[i] for i in cycle) for cycle in three_cycles([local[destination[i]] for i in orbit]))
        for cycle in cycles:
            c=tuple(indices[i] for i in cycle);c=min(c,c[1:]+c[:1],c[2:]+c[:2]);before=[];after=[]
            if c not in parents:raise ValueError('mixup.shape_limit')
            while parents[c][0] is not None:
                c,word=parents[c];before.extend(m.inverse(8) for m in reversed(word));after.append(word)
            result.extend(before);result.extend(parents[c][1]);result.extend(m for word in reversed(after) for m in word)
        return compact(result)

    def restore_colours(self,cube,cancel=None,ready=None,seconds=20.,node_limit=50000):
        """Solve the coloured coset, without assigning invisible piece labels."""
        from time import monotonic
        colours=[-1]*self.degree
        for home in range(len(cube.solids)):
            for poly,colour in cube.placed_faces(home):
                if colour>=0:colours[self.slots[polygon_key(poly)]]=colour
        if self.kind=='mixup_plus_444':
            inner={a for h,s in enumerate(cube.solids) if s.role=='inner_edge' for a in self.homes[h]}
            desired=list(colours)
            for atoms in self.groups.values():
                fat=next((a for a in atoms if a not in inner),None)
                if fat is None:continue
                for a in atoms:
                    if a in inner:desired[a]=colours[fat]
            word=self.inner_pattern_word(colours,desired,cancel)
            work=cube.clone()
            for move in word:
                if cancel and cancel():raise InterruptedError()
                work.apply_move(move)
            return word,work,ready(work) if ready is not None else None
        begun=monotonic();seen={};nodes=0;costs={}
        def cost(level,beta):
            k=level,beta
            if k not in costs:costs[k]=sum(self.strong_cost(ref+1) for ref in self.transversals[level][beta][1])
            return costs[k]
        element=self.element(cube.frames);preferred=self.factors(element)
        if preferred is None and element is not None:
            equivalent=self.equivalent_element(element,cancel)
            if equivalent is not None:element=equivalent;preferred=self.factors(element)
        preferred_beta=[]
        if preferred is not None:
            residual=tuple(element)
            for base,orbit in zip(self.base,self.transversals):
                beta=residual[base];preferred_beta.append(beta);inverse,_=orbit[beta]
                residual=tuple(inverse[x] for x in residual)
        def visit(level,state,budget,on_preferred=True):
            nonlocal nodes
            if cancel and cancel():raise InterruptedError()
            nodes+=1
            if monotonic()-begun>seconds or nodes>node_limit:raise ValueError('mixup.shape_limit')
            if self.coherent(state):return ()
            if level==len(self.base):return None
            key=level,bytes(state)
            if seen.get(key,-1)>=budget:return None
            seen[key]=budget;base=self.base[level];wanted=self.desired[base]
            candidates=[]
            for beta,(inverse,product) in self.transversals[level].items():
                if state[beta]!=wanted:continue
                steps=cost(level,beta)
                if steps>budget:continue
                permutation=[0]*self.degree
                for i,v in enumerate(inverse):permutation[v]=i
                next_state=tuple(state[permutation[i]] for i in range(self.degree))
                incorrect=sum(a!=b for a,b in zip(next_state,self.desired))
                priority=0 if on_preferred and preferred is not None and beta==preferred_beta[level] else 1
                candidates.append((priority,steps,incorrect,beta,next_state))
            for priority,steps,incorrect,beta,next_state in sorted(candidates):
                result=visit(level+1,next_state,budget-steps,on_preferred and priority==0)
                if result is not None:return ((level,beta),)+result
            return None
        try:factors=visit(0,tuple(colours),60000)
        except ValueError:
            word=self.transport_values(colours,self.desired,cancel,seconds=5.,coherent=self.coherent)
            state=tuple(cube.frames);features=self.model.describe(state)[0]
            for move in word:
                if cancel and cancel():raise InterruptedError()
                trial=self.model.apply(state,features,move)
                if trial is None:raise ValueError('mixup.replay_failed')
                state,features=trial
            work=cube.clone();work.colors=state
            return word,work,ready(work) if ready is not None else None
        self.last_search={'nodes':nodes,'seconds':monotonic()-begun}
        if factors is None:raise ValueError('mixup.shape_limit')
        frames=tuple(cube.frames);features=self.model.describe(frames)[0];path=[]
        for level,beta in factors:
            word=compact(m for ref in self.transversals[level][beta][1] for m in self.strong_word(-(ref+1)))
            for move in word:
                if cancel and cancel():raise InterruptedError()
                result=self.model.apply(frames,features,move)
                if result is None:raise ValueError('mixup.replay_failed')
                frames,features=result;path.append(move)
                handoff=self.handoff(cube,frames,ready)
                if handoff is not None:return compact(path),handoff[0],handoff[1]
        work=cube.clone();work.colors=frames
        return compact(path),work,ready(work) if ready is not None else None
