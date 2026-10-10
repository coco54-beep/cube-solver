"""State-based solvers for polyhedral puzzles.

Strong generating sequences are sifted on sticker permutations, rather than
on stored scrambles. Input identification is restricted to legal piece orbits.
"""
from collections import Counter, defaultdict, deque
from functools import lru_cache
from pathlib import Path
import re
import random

from cube.polyhedral import Move, PolyhedralPuzzle, key, rotate, dot, unit
import math


def compose(a,b):
    """First a, then b (permutations map source to destination)."""
    return tuple(map(b.__getitem__, a))


def inverse(p):
    result=[0]*len(p)
    for i,j in enumerate(p):
        result[j]=i
    return tuple(result)


def apply_word(geometry,word):
    result=tuple(range(len(geometry.stickers)))
    for move in word:
        result=compose(result,geometry.permutation(move))
    return result


def inverse_word(word,order):
    return tuple(move.inverse(order) for move in reversed(word))


def simplify(word,order):
    result=[]
    for move in word:
        if result and (result[-1].axis,result[-1].layer)==(move.axis,move.layer):
            amount=(result.pop().amount+move.amount)%order
            if amount:
                result.append(Move(move.axis,move.layer,amount))
        elif move.amount%order:
            result.append(Move(move.axis,move.layer,move.amount%order))
    return tuple(result)


@lru_cache(maxsize=8)
def piece_orbits(kind,n):
    cube=PolyhedralPuzzle(kind,n)
    g=cube.geometry
    neighbors=[set() for _ in g.pieces]
    for move in cube.moves():
        perm=g.permutation(move)
        for piece,indices in enumerate(g.pieces):
            neighbors[piece].add(g.stickers[perm[indices[0]]].piece)
    left=set(range(len(g.pieces)))
    orbits=[]
    while left:
        start=min(left)
        found={start}
        queue=deque([start])
        while queue:
            for q in neighbors[queue.popleft()]:
                if q not in found:
                    found.add(q)
                    queue.append(q)
        orbits.append(tuple(sorted(found)))
        left-=found
    return tuple(orbits)


def identify(cube):
    """Recover home sticker labels from painted piece colors and legal orbits."""
    g=cube.geometry
    if any(not isinstance(c,int) or not 0<=c<len(g.spec.normals) for c in cube.colors):
        raise ValueError('Please enter every sticker')
    if Counter(cube.colors)!=Counter(s.face for s in g.stickers):
        raise ValueError('The color counts do not match this puzzle')
    state=[None]*len(g.stickers)
    oriented=_oriented_identities(cube.puzzle_kind,cube.n)
    for orbit in piece_orbits(cube.puzzle_kind,cube.n):
        available=defaultdict(deque)
        for home in orbit:
            available[tuple(sorted(g.stickers[i].face for i in g.pieces[home]))].append(home)
        for position in orbit:
            slots=g.pieces[position]
            colors=tuple(sorted(cube.colors[i] for i in slots))
            if not available[colors]:
                raise ValueError('A piece has an impossible color combination or position')
            if len(slots)>1:
                painted=tuple(sorted((g.stickers[i].face,cube.colors[i]) for i in slots))
                home=oriented.get((position,painted))
                if home is None or home not in available[colors]:
                    raise ValueError('A piece has a mirrored or impossible orientation')
                available[colors].remove(home)
            else:
                home=available[colors].popleft()
            labels={g.stickers[i].face:i for i in g.pieces[home]}
            if len(labels)!=len(slots):
                raise ValueError('Repeated color on a piece')
            for destination in slots:
                state[labels[cube.colors[destination]]]=destination
        if len(g.pieces[orbit[0]])==1 and len(orbit)>1:
            index={home:i for i,home in enumerate(orbit)}
            perm=[index[g.stickers[state[g.pieces[home][0]]].piece] for home in orbit]
            if _parity(perm):
                duplicates=defaultdict(list)
                for home in orbit:
                    s=g.pieces[home][0]
                    duplicates[g.stickers[s].face].append(s)
                pair=next((ids[:2] for ids in duplicates.values() if len(ids)>1),None)
                if pair:
                    a,b=pair
                    state[a],state[b]=state[b],state[a]
    if len(set(state))!=len(state):
        raise ValueError('Duplicate piece')
    return tuple(state)


def _parity(perm):
    seen=set()
    result=0
    for start in range(len(perm)):
        length=0
        j=start
        while j not in seen:
            seen.add(j)
            length+=1
            j=perm[j]
        if length:
            result^=(length-1)%2
    return result


@lru_cache(maxsize=4)
def _body_frames(kind):
    g=PolyhedralPuzzle(kind,3).geometry
    axes=list(g.spec.axes[:2])
    order=g.spec.turn_order
    identity=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    frames=[identity]
    seen={tuple(key(v) for v in identity)}
    for frame in frames:
        for axis in axes:
            nxt=tuple(rotate(v,axis,2*math.pi/order) for v in frame)
            signature=tuple(key(v) for v in nxt)
            if signature not in seen:
                seen.add(signature)
                frames.append(nxt)
    return tuple(frames)


def _transform(frame,p):
    return tuple(sum(frame[j][i]*p[j] for j in range(3)) for i in range(3))


@lru_cache(maxsize=4)
def _oriented_identities(kind,n):
    g=PolyhedralPuzzle(kind,n).geometry
    positions={key(p):i for i,p in enumerate(g.centres)}
    faces={key(p):i for i,p in enumerate(g.spec.normals)}
    orbit_id={p:i for i,orbit in enumerate(piece_orbits(kind,n)) for p in orbit}
    result={}
    for home,slots in enumerate(g.pieces):
        if len(slots)==1:
            continue
        for frame in _body_frames(kind):
            point=_transform(frame,g.centres[home])
            position=positions.get(key(point))
            if position is None:
                position=min(range(len(g.centres)),key=lambda i:sum((a-b)**2
                             for a,b in zip(point,g.centres[i])))
                if sum((a-b)**2 for a,b in zip(point,g.centres[position]))>1e-9:
                    continue
            if orbit_id[home]!=orbit_id[position]:
                continue
            painted=tuple(sorted((faces[key(_transform(frame,g.spec.normals[g.stickers[i].face]))],
                                  g.stickers[i].face) for i in slots))
            signature=(position,painted)
            if signature in result and result[signature]!=home:
                raise ValueError('Ambiguous oriented piece identity')
            result[signature]=home
    return result


_MINX_NAMES=('U','F','L','BL','BR','R','FR','FL','DL','B','DR','D')


@lru_cache(maxsize=4)
def minx_chain(n=3):
    g=PolyhedralPuzzle('megaminx',n).geometry
    source=Path(__file__).parent/'data'/'megaminx.sgs.txt'
    lines=source.read_text(encoding='utf-8').splitlines()
    sizes=next(tuple(map(int,line.split()[1:])) for line in lines if line.startswith('SubgroupSizes'))
    words=[]
    for line in lines:
        if not line.startswith('Alg '):
            continue
        tokens=line[4:].split()
        word=[]
        for token in tokens:
            match=re.fullmatch(r'([A-Za-z]+)([234]?)(\'?)',token)
            if not match:
                raise ValueError('Unsupported SGS notation')
            name,power,prime=match.groups()
            if name.endswith('v'):
                # The first two stages choose the global orientation. User
                # input assigns the twelve reference colors explicitly.
                word=None
                break
            amount=int(power or 1)*(-1 if not prime else 1)
            word.append(Move(_MINX_NAMES.index(name),0,amount%5))
        words.append(tuple(word) if word is not None else None)
    offset=0
    groups=[]
    identity=tuple(range(len(g.stickers)))
    for size in sizes:
        batch=words[offset:offset+size-1]
        offset+=size-1
        groups.append([(apply_word(g,w),w) for w in batch if w is not None]+[(identity,())])
    processed=set()
    chain=[]
    for stage in reversed(groups[2:]):
        moved={i for perm,_ in stage for i,p in enumerate(perm) if p!=i}
        base=tuple(sorted(moved-processed))
        processed|=moved
        table={tuple(p[i] for i in base):(inverse(p),inverse_word(w,5)) for p,w in stage}
        if len(table)!=len(stage):
            raise ValueError('SGS move mapping does not produce distinct transversals')
        chain.append((base,table))
    return tuple(reversed(chain))


def solve_minx(cube,cancel=None,progress=None):
    if cube.n not in (2,3):
        raise ValueError('Higher-order minx reduction is not yet available')
    entered=identify(cube)
    if cube.n==2:
        # A kilominx has exactly the megaminx corner orbit. Embed the entered
        # corners in an otherwise solved 3-order state, and reuse its chain.
        full=PolyhedralPuzzle('megaminx',3)
        sets={tuple(sorted(full.geometry.stickers[i].face for i in p)):p
              for p in full.geometry.pieces if len(p)==3}
        for piece in cube.geometry.pieces:
            expected=tuple(sorted(cube.geometry.stickers[i].face for i in piece))
            target=sets[expected]
            by_face={full.geometry.stickers[i].face:i for i in target}
            for i in piece:
                full.colors[by_face[cube.geometry.stickers[i].face]]=cube.colors[i]
        state=identify(full)
    else:
        state=entered
    solution=[]
    for stage,(base,table) in enumerate(minx_chain()):
        if cancel and cancel():
            raise InterruptedError()
        signature=tuple(state[i] for i in base)
        if signature not in table:
            raise ValueError('The entered pieces violate an orientation or permutation constraint')
        perm,word=table[signature]
        state=compose(state,perm)
        solution.extend(word)
        if progress:
            progress(stage+1,len(minx_chain()))
    solution=simplify(solution,5)
    check=cube.entered()
    for move in solution:
        check.apply_move(move)
    if not check.is_solved():
        raise ValueError('Solution replay did not restore the entered puzzle')
    return solution


def scramble(cube,length=30,seed=None):
    rng=random.Random(seed)
    moves=cube.moves()
    last=-1
    word=[]
    for _ in range(length):
        options=[m for m in moves if m.axis!=last]
        move=rng.choice(options)
        move=Move(move.axis,move.layer,rng.randrange(1,cube.geometry.spec.turn_order))
        cube.apply_move(move)
        word.append(move)
        last=move.axis
    return tuple(word)


class Word:
    """An algorithm DAG; stabilizer calculations never expand long words."""
    __slots__=('left','right','move','length','inv')

    def __init__(self,left=None,right=None,move=None,inv=False):
        self.left,self.right,self.move,self.inv=left,right,move,inv
        self.length=1 if move is not None else ((left.length if left else 0)+
                                                (right.length if right else 0))

    def inverse(self):
        return Word(self,inv=True)

    def then(self,other):
        if not self.length:
            return other
        if not other.length:
            return self
        return Word(self,other)

    def flatten(self,order,cancel=None):
        stack=[(self,False)]
        count=0
        while stack:
            node,reverse=stack.pop()
            reverse^=node.inv
            if node.move is not None:
                yield node.move.inverse(order) if reverse else node.move
                count+=1
                if count%1024==0 and cancel and cancel():
                    raise InterruptedError()
            elif node.right is None:
                if node.left:
                    stack.append((node.left,reverse))
            elif reverse:
                stack.extend(((node.left,True),(node.right,True)))
            else:
                stack.extend(((node.right,False),(node.left,False)))


class StabilizerChain:
    """Knuth's incremental Schreier-Sims construction with retained words.

    The finite group is generated by this model's actual layer permutations.
    It can validate and solve a labeled state without enumerating its full
    state space. A caller can cancel during both construction and expansion.
    """
    def __init__(self,cube,cancel=None,progress=None,points=None):
        self.g=cube.geometry
        self.cancel=cancel
        self.progress=progress
        self.calls=0
        self.points=tuple(range(len(self.g.stickers))) if points is None else tuple(points)
        point_index={s:i for i,s in enumerate(self.points)}
        self.identity=tuple(range(len(self.points)))
        self.empty=Word()
        self.trans=[{i:(self.identity,self.empty)} for i in self.identity]
        self.generators=[[] for _ in self.identity]
        moves=list(cube.moves())
        # Add inverses as generators to avoid unnecessarily long positive
        # walks in each orbit's spanning tree.
        for index,move in enumerate(moves):
            for atom in (move,move.inverse(self.g.spec.turn_order)):
                full=self.g.permutation(atom)
                permutation=tuple(point_index[full[s]] for s in self.points)
                self._insert(len(self.identity)-1,permutation,Word(move=atom))
            if progress:
                progress(index+1,len(moves))

    def _check(self):
        self.calls+=1
        if self.calls%256==0 and self.cancel and self.cancel():
            raise InterruptedError()

    def _resolves(self,p):
        for k in range(len(p)-1,-1,-1):
            j=p[k]
            if j!=k:
                info=self.trans[k].get(j)
                if info is None:
                    return False
                p=compose(p,inverse(info[0]))
        return True

    def _insert(self,k,p,word):
        self._check()
        if k<0 or p==self.identity:
            return
        self.generators[k].append((p,word))
        for q,w in tuple(self.trans[k].values()):
            self._extend(k,compose(q,p),w.then(word))

    def _extend(self,k,p,word):
        self._check()
        j=p[k]
        info=self.trans[k].get(j)
        if info is None:
            self.trans[k][j]=(p,word)
            for q,w in tuple(self.generators[k]):
                self._extend(k,compose(p,q),word.then(w))
        else:
            remainder=compose(p,inverse(info[0]))
            if not self._resolves(remainder):
                self._insert(k-1,remainder,word.then(info[1].inverse()))

    def solve(self,state):
        word=self.empty
        for k in range(len(state)-1,-1,-1):
            j=state[k]
            if j==k:
                continue
            info=self.trans[k].get(j)
            if info is None:
                raise ValueError('The entered puzzle is not a legal state')
            state=compose(state,inverse(info[0]))
            word=word.then(info[1].inverse())
        if state!=self.identity:
            raise ValueError('The entered puzzle is not a legal state')
        return word


def solve_polyhedral(cube,cancel=None,progress=None):
    """Solve an entered state and verify it by replay on a fresh instance."""
    if cube.is_solved():
        return ()
    if cube.puzzle_kind=='megaminx':
        if cube.n in (2,3):
            return solve_minx(cube,cancel,progress)
        from solver.polyhedral_reduction import solve_high_minx
        return solve_high_minx(cube,cancel,progress)
    if cube.puzzle_kind in ('pyraminx','moyu','skewb'):
        from solver.polyhedral_reduction import solve_tetrahedral
        return solve_tetrahedral(cube,cancel,progress)
    raise ValueError('Unsupported puzzle family')
