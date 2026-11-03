"""Closed reference Twins actions with both source exchange families."""
from functools import lru_cache
from pathlib import Path
import json,zlib
from cube.twins_pcubes import TwinsPCubesState,AXES,fingerprint
from cube.polyhedral import Move,Spec,Geometry,Sticker,CUBE
from cube.pisces_aligned import AlignedPisces,expand_circuits
from cube.crazy_comet import observed_colors


@lru_cache(maxsize=1)
def flower_pairs():
    """The four inner/outer petal contacts on each of the six body faces."""
    from collections import Counter
    from cube.polyhedral import mean,dot,scale,add
    c=TwinsPCubesState();counts=Counter(h for h,f,p in c.panels);faces=[]
    for face,normal in enumerate(CUBE):
        groups={}
        for slot,(home,f,poly) in enumerate(c.panels):
            if f!=face or counts[home]!=1:continue
            centre=mean(poly);tangent=add(centre,scale(normal,-dot(centre,normal)))
            coordinates=[x for x,n in zip(tangent,normal) if not n]
            if abs(abs(coordinates[0])-abs(coordinates[1]))>1e-7:continue
            direction=tuple(x>0 for x in coordinates)
            groups.setdefault(direction,[]).append((dot(tangent,tangent),slot))
        if len(groups)!=4 or any(len(g)<2 for g in groups.values()):raise ValueError('Twins petal layout changed')
        faces.append(tuple(tuple(s for r,s in sorted(groups[d])[:2]) for d in sorted(groups)))
    return tuple(faces)


def flower_quality(colors):
    """Require visible mixing within the petals, as well as across their seam."""
    faces=[]
    for pairs in flower_pairs():
        inner={colors[a] for a,b in pairs};outer={colors[b] for a,b in pairs}
        different=sum(colors[a]!=colors[b] for a,b in pairs)
        faces.append((different,len(inner),len(outer)))
    return tuple(faces)


def _mixed_faces(colors):
    quality=flower_quality(colors)
    return sum(d>=2 and i>=2 and o>=2 for d,i,o in quality)


def _mix_petals(cube,rows,rng,guard):
    colors=observed_colors(cube)
    if _mixed_faces(colors)==6:return
    # Choose a bounded additional legal word using small colour permutations.
    # Only the selected word is then replayed on complete material. No paint
    # values are changed directly, and the word is not stored on the cube.
    nine=[j for j,(p,w) in enumerate(rows) if len(w)==9]
    inverses=[]
    for p,w in rows:
        q=[0]*len(p)
        for a,b in enumerate(p):q[b]=a
        inverses.append(tuple(q))
    chosen=None
    for attempt in range(64):
        guard();current=colors;path=[]
        for depth in range(16):
            j=rng.choice(nine if depth%3==0 else range(len(rows)));reverse=bool(rng.randrange(2))
            pullback=rows[j][0] if reverse else inverses[j]
            current=tuple(current[s] for s in pullback);path.append((j,reverse))
            if _mixed_faces(current)==6:chosen=path;break
        if chosen is not None:break
    if chosen is None:raise TimeoutError('copter.scramble_timeout')
    for j,reverse in chosen:
        word=rows[j][1]
        if reverse:word=tuple(Move(m.axis,0,-m.amount) for m in reversed(word))
        for move in word:cube.apply_move(move,guard)
    if _mixed_faces(observed_colors(cube))!=6:raise ValueError('Twins petal scramble replay mismatch')


def source_key():return fingerprint()+'-source-random2-random3-v1'


@lru_cache(maxsize=1)
def generators():
    c=TwinsPCubesState();rows=[]
    for a in range(20):
        word=(Move(a,0,180. if a<12 else 120.),)
        rows.append((c.clone().apply_moves(word).aligned_permutation(),word))
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/twins_pcubes_exchanges.bin').read_bytes()))
    if data.get('version')!=1 or data.get('source')!=fingerprint():raise ValueError('Stale Twins reference exchanges')
    for row in data['rows']:
        p=tuple(row['action']);word=tuple(Move(*m) for m in row['word'])
        order=3 if len(word)==7 else 2
        if len(word) not in (7,9) or sorted(p)!=list(range(len(c.panels))):raise ValueError('Invalid Twins reference exchange')
        q=tuple(range(len(p)))
        for _ in range(order):q=tuple(p[s] for s in q)
        if q!=tuple(range(len(p))):raise ValueError('Invalid Twins reference order')
        rows.append((p,word))
    return tuple(rows)


@lru_cache(maxsize=1)
def geometry():
    c=TwinsPCubesState();rows=generators();g=c.geometry
    axes=tuple(AXES[w[len(w)//2].axis] for p,w in rows)
    steps=tuple(2 if w[len(w)//2].axis>=12 else 3 for p,w in rows)
    layers=tuple((tuple(h for h,s in enumerate(g.pieces) if any(p[i]!=i for i in s)),) for p,w in rows)
    return Geometry(Spec('_twins_pcubes',3,CUBE,axes,(),6,axis_steps=steps),
                    tuple(Sticker(h,f,p) for h,f,p in c.panels),g.pieces,g.centres,
                    tuple((p,) for p,w in rows),layers)


class AlignedTwinsPCubes(AlignedPisces):
    puzzle_kind='_twins_pcubes'
    def __init__(self,colors=None):
        self.geometry=geometry();self.colors=list(colors) if colors is not None else [s.face for s in self.geometry.stickers]
        if len(self.colors)!=len(self.geometry.stickers):raise ValueError('Wrong reference Twins field count')


def expand(word):return expand_circuits(word,generators())


def scrambled(seed=None,length=30,cancel=None,jumble=True):
    from random import Random
    from time import monotonic
    rng=Random(seed);c=TwinsPCubesState();rows=generators();previous=-1;deadline=monotonic()+15.
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:raise TimeoutError('copter.scramble_timeout')
    seven=[i for i,(p,w) in enumerate(rows) if len(w)==7]
    nine=[i for i,(p,w) in enumerate(rows) if len(w)==9]
    for step in range(length):
        guard();pool=seven if step%4==0 else nine if step%4==2 else range(len(rows))
        j=rng.choice([i for i in pool if i!=previous]);previous=j;word=rows[j][1]
        if rng.randrange(2):word=tuple(Move(m.axis,0,-m.amount) for m in reversed(word))
        for move in word:c.apply_move(move,guard)
    if length:_mix_petals(c,rows,rng,guard)
    if jumble and length:
        # A prefix of a certified exchange gives a legal shape-changing
        # suffix. The solver receives only poses and paints, never this word.
        word=rows[rng.choice(seven+nine)][1]
        for move in word[:1]:c.apply_move(move,guard)
    return c
