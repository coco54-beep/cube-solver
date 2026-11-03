"""Portable rigid Tangram algorithms; no runtime symbolic dependency."""
import hashlib
import json
import zlib
from pathlib import Path
from functools import lru_cache
from time import monotonic

from cube.polyhedral import Move
from cube.articulated_observation import polygon_key
from solver.tangram_geometry import geometry


def geometry_fingerprint(kind):
    cube = geometry(kind).cube
    def stable(value):
        if isinstance(value, float):return round(value,8) or 0.0
        if isinstance(value,(tuple,list)):return tuple(stable(v) for v in value)
        return value
    data = stable((cube._bands(), tuple((s.role,s.anchor,s.faces) for s in cube.solids), cube.orientations,
                   tuple((m.axis,m.layer,m.amount) for m in geometry(kind).moves)))
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def compact(word):
    result=[]
    for move in word:
        amount=move.amount%6
        if result and (result[-1].axis,result[-1].layer)==(move.axis,move.layer):
            amount=(result.pop().amount+amount)%6
        if amount:result.append(Move(move.axis,move.layer,amount))
    return tuple(result)


@lru_cache(maxsize=2)
def load_table(kind):
    return TangramTable(kind)


class TangramTable:
    def __init__(self, kind, path=None):
        self.kind=kind;self.model=geometry(kind)
        path=Path(path) if path is not None else Path(__file__).resolve().parent/'data'/(kind+'_group.bin')
        if not path.exists():raise ValueError('rigid.solver_data')
        table=json.loads(zlib.decompress(path.read_bytes()))
        if (table.get('version')!=1 or table['kind']!=kind or table.get('geometry')!=geometry_fingerprint(kind)):
            raise ValueError('rigid.invalid')
        self.degree=table['degree'];self.base=table['base'];self.records=table['strong']
        self.words=[tuple(Move(*m) for m in w) for w in table['moves']]
        self.transversals=[]
        for level in table['transversals']:
            orbit={}
            for beta,item in level.items():
                inverse=[0]*self.degree
                for src,dst in enumerate(item['permutation']):inverse[dst]=src
                orbit[int(beta)]=tuple(inverse),tuple(item['product'])
            self.transversals.append(orbit)
        self.slots={};self.homes=[];self.desired=[];self._words={};self.images={}
        for home in range(len(self.model.cube.solids)):
            atoms=[]
            for poly,color in self.model.cube.placed_faces(home):
                if color<0:continue
                atom=len(self.slots);atoms.append(atom);self.slots[polygon_key(poly)]=atom;self.desired.append(color)
            self.homes.append(atoms)
        if len(self.slots)!=self.degree:raise ValueError('rigid.invalid')

    def strong_word(self, index):
        if index in self._words:return self._words[index]
        record=self.records[abs(index)-1]
        if index<0:word=tuple(m.inverse(6) for m in reversed(self.strong_word(-index)))
        elif 'shortcut' in record:word=tuple(Move(*m) for m in record['shortcut'])
        elif record['original'] is not None:word=self.words[record['original']]
        else:word=compact(m for ref in reversed(record['product']) for m in self.strong_word(ref))
        if len(word)>200000:raise ValueError('rigid.solver_data')
        self._words[index]=word
        return word

    def element(self, frames):
        result=[-1]*self.degree
        for h,p in enumerate(frames):
            if (h,p) not in self.images:
                self.images[h,p]=tuple(self.slots.get(polygon_key(poly),-1) for poly,c in self.model.cube.placed_faces(h,p) if c>=0)
            for atom,target in zip(self.homes[h],self.images[h,p]):result[atom]=target
        return tuple(result) if sorted(result)==list(range(self.degree)) else None

    def factors(self, element):
        if element is None:return None
        state=element;factors=[]
        for base,orbit in zip(self.base,self.transversals):
            beta=state[base]
            if beta not in orbit:return None
            inverse,product=orbit[beta]
            state=tuple(inverse[x] for x in state);factors.append(product)
        return factors if state==tuple(range(self.degree)) else None

    def solve(self, cube, cancel=None, seconds=None):
        if cancel and cancel():raise InterruptedError()
        element=self.element(cube.frames)
        if element is None:raise ValueError('rigid.invalid')
        def word_for(value):
            if cancel and cancel():raise InterruptedError()
            factors=self.factors(value)
            if factors is None:factors=self.coloured_factors(value,cancel,seconds)
            return compact(m for product in factors for ref in product for m in self.strong_word(-(ref+1)))
        word=word_for(element)
        if self.kind=='tangram_extreme' and len(word)>600:
            # Different short entries into the same stabilizer chain avoid
            # a long late parity correction. This only shortens an already
            # complete answer; it is never a limit on solving the state.
            if not hasattr(self,'_preparations'):
                root=self.model.cube.frames;basic=[]
                for frames,move in self.model.children(root):
                    action=self.element(frames)
                    if action is not None:basic.append((action,(move,)))
                choices=list(basic)
                for p,pw in basic:
                    for q,qw in basic:
                        if (pw[-1].axis,pw[-1].layer)==(qw[0].axis,qw[0].layer):continue
                        choices.append((tuple(q[a] for a in p),pw+qw))
                self._preparations=tuple(choices)
            for action,prefix in self._preparations:
                candidate=compact(prefix+word_for(tuple(action[a] for a in element)))
                if len(candidate)<len(word):word=candidate
                if len(word)<=600:break
        frames=tuple(cube.frames)
        for move in word:
            if cancel and cancel():raise InterruptedError()
            frames=self.model.apply(frames,move)
            if frames is None:raise ValueError('rigid.invalid')
        replay=cube.clone();replay.colors=frames
        if not replay.is_solved():raise ValueError('rigid.invalid')
        return word

    def coloured_factors(self, element, cancel=None, seconds=None):
        """Resolve equivalent same-colour piece labels from manual matching."""
        wanted=tuple(self.desired);colours=[-1]*self.degree
        for src,dst in enumerate(element):colours[dst]=wanted[src]
        begun=monotonic();nodes=0;seen=set()
        def visit(level,state):
            nonlocal nodes
            if cancel and cancel():raise InterruptedError()
            nodes+=1
            if seconds is not None and monotonic()-begun>seconds:raise ValueError('rigid.search_limit')
            if state==wanted:return ()
            if level==len(self.base) or (level,state) in seen:return None
            if len(seen)<12000:seen.add((level,state))
            base=self.base[level];following=[]
            for beta,(inverse,product) in self.transversals[level].items():
                if state[beta]!=wanted[base]:continue
                permutation=[0]*self.degree
                for i,x in enumerate(inverse):permutation[x]=i
                child=tuple(state[permutation[i]] for i in range(self.degree))
                cost=sum(len(self.strong_word(ref+1)) for ref in product)
                following.append((sum(a!=b for a,b in zip(child,wanted)),cost,beta,child,product))
            for _,cost,beta,child,product in sorted(following):
                result=visit(level+1,child)
                if result is not None:return (product,)+result
            return None
        answer=visit(0,tuple(colours))
        if answer is None:raise ValueError('rigid.state_unreachable')
        return answer
