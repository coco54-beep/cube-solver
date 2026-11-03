"""Colour-constrained solving on separately certified whole-material actions."""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json,time,zlib
from cube.rigid_placements import placements
from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import simplify,inverse_word


class MaterialSolver:
    def __init__(self,factory,aligned,generators,source_key,expand,observed_colors,asset,complete_group=True):
        self.factory=factory;self.aligned=aligned;self.generators=generators
        self.source_key=source_key;self.expand=expand;self.observed_colors=observed_colors
        self.asset=Path(__file__).resolve().parent/'data'/asset
        self.complete_group=complete_group

    @lru_cache(maxsize=8)
    def data(self):
        data=json.loads(zlib.decompress(self.asset.read_bytes()));cube=self.aligned();n=len(cube.colors)
        macros=[[[m.axis,m.layer,m.amount] for m in w] for a,w in self.generators()]
        if (data.get('version') not in (1,2) or data.get('geometry')!=geometry_key(cube.geometry)
                or data.get('source')!=self.source_key() or data.get('macros')!=macros
                or len(data.get('transversals',()))!=len(data.get('base',()))):
            raise ValueError('Material solver data do not match the guarded mechanism')
        core=data.get('core_points',list(range(n)))
        if sorted(data.get('base',()))!=sorted(core):raise ValueError('Invalid material quotient base')
        covered=list(core)
        from solver.polyhedral import apply_word
        allowed={s for row in data.get('leaf_stages',()) for s in row['slots']}
        for row in data.get('leaf_stages',()):
            slots=tuple(row['slots']);covered.extend(slots);word=tuple(Move(*m) for m in row['word'])
            if len(set(slots))!=len(slots) or any(len(cube.geometry.pieces[cube.geometry.stickers[s].piece])!=1 for s in slots):
                raise ValueError('Invalid singleton stage')
            counts=Counter(cube.geometry.stickers[s].face for s in slots)
            if min(counts.values())<2:raise ValueError('Singleton stage has no same-colour parity spare')
            action=apply_word(cube.geometry,word);trip=tuple(row['base'])
            if (len(set(trip))!=3 or not set(trip)<=set(slots)
                    or {s for s in slots if action[s]!=s}!=set(trip)
                    or any(action[s]!=s for s in range(n) if s not in allowed)
                    or any(action[a]!=b for a,b in zip(trip,trip[1:]+trip[:1]))):
                raise ValueError('Material stage does not preserve completed orbits')
            if row.get('coverage')!=len(slots)*(len(slots)-1)*(len(slots)-2)//3:
                raise ValueError('Material stage has no complete triple certificate')
            if any(set(action[s] for s in slots)!=set(slots) for action,w in self.generators()):
                raise ValueError('Material singleton stage is not an invariant orbit')
            allowed-=set(slots)
        if sorted(covered)!=list(range(n)):raise ValueError('Incomplete material stages')
        return data

    @lru_cache(maxsize=8)
    def prepared(self):
        data=self.data()
        return tuple(data['base']),tuple(tuple((int(beta),tuple(r['permutation']),tuple(Move(*m) for m in r['word']))
                                              for beta,r in row.items()) for row in data['transversals'])


    @lru_cache(maxsize=8)
    def local_patterns(self):
        c=self.factory();result=[set() for _ in c.solids];g=self.aligned().geometry
        for home in range(len(c.solids)):
            for destination,frame,mapping in placements(self.factory,home):
                paint={target:c.panels[source][1] for source,target in mapping}
                result[destination].add(tuple(paint[i] for i in g.pieces[destination]))
        return tuple(frozenset(row) for row in result)


    def validate(self,colors):
        cube=self.aligned(colors);g=cube.geometry;goal=tuple(s.face for s in g.stickers)
        if any(type(c) is not int or c not in range(cube.color_count) for c in colors):raise ValueError('Please enter every sticker')
        if Counter(colors)!=Counter(goal):raise ValueError('The color counts do not match this puzzle')
        for home,slots in enumerate(g.pieces):
            if tuple(colors[i] for i in slots) not in self.local_patterns()[home]:
                error=ValueError('A piece has a mirrored or impossible orientation')
                error.locations=[dict(sticker=i) for i in slots];raise error
        owner={s:h for h,slots in enumerate(g.pieces) for s in slots};parent=list(range(len(g.pieces)))
        def root(h):
            while parent[h]!=h:parent[h]=parent[parent[h]];h=parent[h]
            return h
        for action,w in self.generators():
            for slots in g.pieces:
                if slots:parent[root(owner[slots[0]])]=root(owner[action[slots[0]]])
        groups={}
        for home,slots in enumerate(g.pieces):
            if slots:groups.setdefault(root(home),[]).append(slots)
        for pieces in groups.values():
            if Counter(tuple(sorted(colors[i] for i in slots)) for slots in pieces)!=Counter(
                    tuple(sorted(goal[i] for i in slots)) for slots in pieces):
                error=ValueError('A piece has an impossible color combination or position' if self.complete_group else 'tilted.group_unresolved')
                error.locations=[dict(sticker=i) for slots in pieces for i in slots];raise error
        return cube


    def solve_colours(self,colors,cancel=None,progress=None,seconds=30.):
        started=time.monotonic()
        def guard():
            if cancel and cancel():raise InterruptedError()
            if time.monotonic()-started>=seconds:raise TimeoutError('comet.timeout')
        guard();cube=self.validate(tuple(colors));start=tuple(cube.colors);goal=tuple(s.face for s in cube.geometry.stickers)
        if start==goal:return ()
        base,rows=self.prepared();seen=set();nodes=0
        def choices(level,current):
            guard()
            if all(current[k]==goal[k] for k in base):return iter((None,))
            if level==len(base) or (level,current) in seen:return iter(())
            if len(seen)<20000:seen.add((level,current))
            k=base[level];options=[]
            for beta,p,w in rows[level]:
                if current[beta]!=goal[k]:continue
                child=tuple(current[i] for i in p)
                options.append((sum(a!=b for a,b in zip(child,goal)),len(w),beta,child,w))
            options.sort(key=lambda r:r[:3]);return iter(options)
        factors=[];stack=[(0,start,choices(0,start))];found=None
        while stack:
            guard();level,current,options=stack[-1];item=next(options,False)
            if item is None:found=tuple(factors);break
            if item is False:
                stack.pop()
                if factors:factors.pop()
                continue
            _,_,_,child,w=item;factors.append(w);nodes+=1
            stack.append((level+1,child,choices(level+1,child)))
            if progress and nodes%128==0:progress(-1,0)
        if found is None:
            raise ValueError('The entered puzzle is not a legal state' if self.complete_group else 'tilted.group_unresolved')
        result=simplify(tuple(m for w in found for m in inverse_word(w,cube.geometry.spec.turn_order)),cube.geometry.spec.turn_order)
        replay=cube.clone()
        for move in result:guard();replay.apply_move(move)
        if self.data().get('leaf_stages'):
            result=self.finish_leaves(replay,result,guard,cancel)
        if not replay.is_solved():raise ValueError('Material colour replay failed')
        from solver.solution_loops import shorten_polyhedral_word
        return shorten_polyhedral_word(cube,result,cancel)

    def finish_leaves(self,cube,prefix,guard,cancel):
        from solver.polyhedral import _parity
        from solver.polyhedral_reduction import Transports,orbit_word,color_orbit_word
        g=cube.geometry;order=g.spec.turn_order;result=list(prefix)
        allowed={s for row in self.data()['leaf_stages'] for s in row['slots']}
        for row in self.data()['leaf_stages']:
            guard();slots=tuple(row['slots']);actual=[cube.colors[s] for s in slots]
            goal=[g.stickers[s].face for s in slots];homes={c:[i for i,x in enumerate(goal) if x==c] for c in set(goal)}
            destination=[None]*len(slots)
            for i,color in enumerate(actual):
                if i in homes[color]:homes[color].remove(i);destination[i]=i
            for i,color in enumerate(actual):
                if destination[i] is None:destination[i]=homes[color].pop()
            if _parity(destination):
                a,b=next((a,b) for a in range(len(slots)) for b in range(a+1,len(slots)) if actual[a]==actual[b])
                destination[a],destination[b]=destination[b],destination[a]
            if destination==list(range(len(slots))):allowed-=set(slots);continue
            orbit=tuple(g.stickers[s].piece for s in slots);base=tuple(g.stickers[s].piece for s in row['base'])
            primitive=tuple(Move(*m) for m in row['word'])
            def stop():guard();return False
            transport=Transports(cube,orbit,base,stop,both_directions=True)
            word=orbit_word(transport,orbit,destination,primitive,result,search_budget=.02)
            word=color_orbit_word(cube,transport,orbit,primitive,word,result,budget=.03)
            before=tuple(cube.colors)
            for move in word:guard();cube.apply_move(move)
            if (any(cube.colors[s]!=g.stickers[s].face for s in slots)
                    or any(cube.colors[s]!=c for s,c in enumerate(before) if s not in allowed)):
                raise ValueError('Material singleton stage replay failed')
            result.extend(word)
            allowed-=set(slots)
        return simplify(result,order)


    def solve(self,cube,cancel=None,progress=None,seconds=60.):
        from solver.rigid_shape import normalize
        started=time.monotonic()
        if cancel and cancel():raise InterruptedError()
        if any(c<0 for c in cube.paints):raise ValueError('Please enter every sticker')
        # Physical face IDs need not be colour IDs: the fourteen-face
        # Helicopter has eight different cap faces with the same gold paint.
        if Counter(cube.paints)!=Counter(self.factory().paints):raise ValueError('The color counts do not match this puzzle')
        if hasattr(cube,'validate_pose'):cube.validate_pose()
        work,prefix=normalize(cube,cancel,seconds)
        tail=self.expand(self.solve_colours(self.observed_colors(work),cancel,progress,max(.001,seconds-(time.monotonic()-started))))
        def guard():
            if cancel and cancel():raise InterruptedError()
            if time.monotonic()-started>=seconds:raise TimeoutError('comet.timeout')
        for move in tail:work.apply_move(move,guard)
        if not work.is_solved():raise ValueError('Material guarded replay failed')
        return prefix+tail
