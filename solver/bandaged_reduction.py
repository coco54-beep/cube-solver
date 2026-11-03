"""Bandage reduction through exhaustive uncoloured rigid-layout graphs."""
from functools import lru_cache
from pathlib import Path
from time import monotonic
import json
import struct
import zlib

from cube.appearance import ROTATIONS,transform_frame
from solver.bandaged_state import model


@lru_cache(maxsize=5)
def geometry(kind='burr_cube'):
    return BandageLayoutGeometry(kind)


class BandageLayoutGeometry:
    def __init__(self,kind):
        self.grid=model(kind)
        shapes=[[tuple(sorted(transform_frame(f,h) for h in unit)) for f in ROTATIONS] for unit in self.grid.units]
        self.shapes=tuple(sorted({shape for row in shapes for shape in row}))
        index={shape:i for i,shape in enumerate(self.shapes)}
        self.positions=tuple(tuple(index[s] for s in row) for row in shapes)
        self.bits=tuple(tuple(1<<i for i in row) for row in self.positions)
        poses={f:i for i,f in enumerate(ROTATIONS)}
        self.inverse=tuple(poses[tuple(zip(*f))] for f in ROTATIONS)
        self.product=tuple(tuple(poses[tuple(transform_frame(a,v) for v in b)] for b in ROTATIONS) for a in ROTATIONS)
        base=self.grid.base
        homes=sorted(base.cubies,key=lambda h:(-len(base.cubies[h].stickers),h))
        self.atoms=tuple((h,n,c) for h in homes for n,c in sorted(base.cubies[h].stickers.items()))
        slots={(h,n):i for i,(h,n,c) in enumerate(self.atoms)}
        self.homes=tuple(tuple(i for i,(h,n,c) in enumerate(self.atoms) if h in unit) for unit in self.grid.units)
        self.images=tuple(tuple(tuple(slots[transform_frame(f,self.atoms[i][0]),transform_frame(f,self.atoms[i][1])]
                                      for i in indices) for f in ROTATIONS) for indices in self.homes)

    def key(self,state):
        result=0
        for u,v in enumerate(state):result|=self.bits[u][v-(u%8)*24]
        return result

    def loop(self,child,representative):
        """Effect of reaching child, then reversing the representative path.

        Both endpoints have identical domino geometry. The inverse rigid
        frame at each occupied domino maps the child back to the root.
        """
        backwards={self.positions[u][v-(u%8)*24]:self.inverse[v-(u%8)*24] for u,v in enumerate(representative)}
        result=[0]*len(self.atoms)
        for u,v in enumerate(child):
            pose=v-(u%8)*24
            dest=self.product[backwards[self.positions[u][pose]]][pose]
            for source,target in zip(self.homes[u],self.images[u][dest]):result[source]=target
        return bytes(result)


def inverse_word(word):
    return tuple(m if m.endswith('2') else m[:-1] if m.endswith("'") else m+"'" for m in reversed(word))


@lru_cache(maxsize=5)
def assets(kind='burr_cube'):
    folder=Path(__file__).parent/'data'
    name=kind.removesuffix('_cube')
    try:
        raw=(folder/(name+'_shapes.bin')).read_bytes()
        size=struct.unpack_from('<I',raw,4)[0];header=json.loads(raw[8:8+size]);blob=zlib.decompress(raw[8+size:])
        group=json.loads(zlib.decompress((folder/(name+'_group.bin')).read_bytes()))
    except (OSError,ValueError,struct.error,zlib.error):raise ValueError('bandage.search_table') from None
    fingerprint=geometry(kind).grid.fingerprint
    if (raw[:4]!=b'BS01' or group.get('version')!=1 or group.get('kind')!=kind
        or header.get('geometry')!=fingerprint or group.get('geometry')!=fingerprint
        or header.get('count',0)*(header.get('key_bytes',14)+5)!=len(blob)):raise ValueError('bandage.search_table')
    return header,blob,group


def locate(key,header,blob):
    width=header.get('key_bytes',14)
    target=key.to_bytes(width,'big');lo=0;hi=header['count']
    while lo<hi:
        mid=(lo+hi)//2;value=blob[mid*width:mid*width+width]
        if value<target:lo=mid+1
        else:hi=mid
    return lo if lo<header['count'] and blob[lo*width:lo*width+width]==target else None


def solve_bandage_reduction(cube,cancel=None,seconds=None):
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return []
    g=geometry(cube.puzzle_kind);header,blob,data=assets(cube.puzzle_kind);grid=g.grid
    work=cube.clone();work.history=[];state=grid.encode(work)
    index=locate(g.key(state),header,blob)
    if index is None:raise ValueError('bandage.state_unreachable')
    prefix=[];count=header['count'];width=header.get('key_bytes',14)
    while True:
        if cancel and cancel():raise InterruptedError()
        parent=struct.unpack_from('<I',blob,count*width+index*4)[0]
        if parent==0xffffffff:break
        move=blob[count*(width+4)+index]
        prefix.extend(inverse_word((grid.moves[move],)));index=parent
    for move in prefix:
        if cancel and cancel():raise InterruptedError()
        work.apply_move(move)
    if g.key(grid.encode(work))!=header['root']:raise ValueError('bandage.search_replay')
    wanted=tuple(c for h,n,c in g.atoms)
    colours=tuple(work.cubies[h].stickers[n] for h,n,c in g.atoms)
    begun=monotonic();nodes=0;seen=set()
    def visit(level,current):
        nonlocal nodes
        if cancel and cancel():raise InterruptedError()
        nodes+=1
        if seconds is not None and monotonic()-begun>seconds:raise ValueError('rigid.search_limit')
        if current==wanted:return ()
        if level==len(data['base']) or (level,current) in seen:return None
        if len(seen)<12000:seen.add((level,current))
        point=data['base'][level];following=[]
        for beta,entry in data['transversals'][level].items():
            if current[int(beta)]!=wanted[point]:continue
            child=tuple(current[i] for i in entry['permutation'])
            following.append((sum(a!=b for a,b in zip(child,wanted)),len(entry['word']),int(beta),child,entry))
        for _,_,beta,child,entry in sorted(following):
            tail=visit(level+1,child)
            if tail is not None:return (entry,)+tail
        return None
    factors=visit(0,colours)
    if factors is None:raise ValueError('bandage.state_unreachable')
    word=prefix+[m for entry in factors for m in inverse_word(entry['word'])]
    replay=cube.clone()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('bandage.search_replay')
    return word
