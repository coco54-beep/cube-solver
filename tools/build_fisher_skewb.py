"""Prepare centre-direction finishers for the Fisher Skewb's Skewb mechanism."""
import heapq
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.mastermorphix import IDENTITY
from cube.mirror_skewb import MirrorSkewbCube
from cube.mirror_pyraminx import marker_system,placements
from cube.mirror_tower import Piece,frame_key
from solver.polyhedral import StabilizerChain,simplify
from solver.lattice_data import geometry_key


def build():
    cube=MirrorSkewbCube()
    _,_,virtual=marker_system(3,'skewb')
    class Markers:
        geometry=virtual
        def moves(self): return cube.moves()
    chain=StabilizerChain(Markers())
    homes=[p for p,s in enumerate(cube.geometry.pieces) if len(s)==1]
    flipped={h:next(f for f in placements(3,h,h,'skewb')
                    if frame_key(f)!=frame_key(IDENTITY)) for h in homes}
    raw={0:()}
    for mask in range(1,64):
        pieces=dict(cube.pieces)
        for bit,h in enumerate(homes):
            if mask>>bit&1: pieces[h]=Piece(h,flipped[h])
        state=MirrorSkewbCube(pieces).labeled_state()
        try:
            raw[mask]=simplify(tuple(chain.solve(state).flatten(3)),3)
        except ValueError:
            pass
    # Short ordinary-state loops expose centre flips much more efficiently
    # than expanding the general chain. Conjugation spreads them to all faces.
    atoms=tuple(m for move in cube.moves() for m in (move,move.inverse(3)))
    for a in atoms:
        for b in atoms:
            if a.axis==b.axis: continue
            loop=(a,b,a.inverse(3),b.inverse(3))
            work=cube.clone()
            for power in range(1,13):
                for move in loop: work.apply_move(move)
                if any(p.home!=pos or (len(cube.geometry.pieces[pos])==3 and
                       frame_key(p.frame)!=frame_key(IDENTITY)) for pos,p in work.pieces.items()):
                    continue
                mask=sum(1<<bit for bit,h in enumerate(homes)
                         if frame_key(work.pieces[h].frame)!=frame_key(IDENTITY))
                word=simplify(loop*power,3)
                if len(word)<len(raw.get(mask,word+(a,))): raw[mask]=word
                break
    transfers=[]
    for a in atoms:
        perm=cube.geometry.permutation(a)
        transfer=[homes.index(cube.geometry.stickers[perm[cube.geometry.pieces[h][0]]].piece)
                  for h in homes]
        transfers.append((a,transfer))
    changed=True
    while changed:
        changed=False
        for mask,word in tuple(raw.items()):
            for a,transfer in transfers:
                target=sum(1<<transfer[i] for i in range(6) if mask>>i&1)
                candidate=simplify((a.inverse(3),)+word+(a,),3)
                if target not in raw or len(candidate)<len(raw[target]):
                    raw[target]=candidate
                    changed=True
    # Returned words fix all ordinary pieces. Their centre twists combine
    # by XOR, so short finishers can replace long stabilizer-chain words.
    best={0:()}
    queue=[(0,0)]
    while queue:
        cost,mask=heapq.heappop(queue)
        if cost!=len(best[mask]): continue
        for bits,word in raw.items():
            target=mask^bits
            candidate=simplify(best[mask]+word,3)
            if target not in best or len(candidate)<len(best[target]):
                best[target]=candidate
                heapq.heappush(queue,(len(candidate),target))
    for mask,word in best.items():
        pieces=dict(cube.pieces)
        for bit,h in enumerate(homes):
            if mask>>bit&1: pieces[h]=Piece(h,flipped[h])
        replay=MirrorSkewbCube(pieces)
        for move in word: replay.apply_move(move)
        if not replay.is_solved(): raise ValueError('Invalid Fisher centre finisher')
    path=Path(__file__).resolve().parents[1]/'solver/data/fisher_skewb.bin'
    path.write_bytes(zlib.compress(json.dumps(dict(geometry=geometry_key(cube.geometry),homes=homes,
        finishers={str(i):[(m.axis,m.layer,m.amount) for m in word] for i,word in best.items()}),
        separators=(',',':')).encode(),9))
    print('finishers',len(best),'max length',max(map(len,best.values())),'bytes',path.stat().st_size)


if __name__=='__main__': build()
