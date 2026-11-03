"""Enumerate every projected half-cube setup and compile legal slice macros."""
from collections import deque
from pathlib import Path
import hashlib
import json
import struct
import sys
from time import monotonic
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from cube.cuboid import IDENTITY
from cube.appearance import ROTATIONS
from cube.polyhedral import Move
from solver.camouflage_reduction import model


def main(kind='camouflage_3'):
    begun=monotonic();g=model(kind);identity=ROTATIONS.index(IDENTITY)
    halves=tuple(g.at[Move(face,1,amount)] for face in g.inner_faces for amount in (1,2,3))
    from cube.polyhedral import CUBE
    primary=g.inner_faces[0];normal=CUBE[primary]
    tracked=tuple(i for i,(p,c) in enumerate(g.corners) if sum(v*w for v,w in zip(c,normal))>0)
    root=bytes([identity]*8);queue=deque([0]);states=[root];parents=[-1];moves=[255]
    seen={bytes(root[i] for i in tracked)}
    def half(state,index):
        return bytes(g.transitions[p][state[i]][index] for i,(p,c) in enumerate(g.corners))
    while queue:
        current=queue.popleft()
        for index in halves:
            child=half(states[current],index);key=bytes(child[i] for i in tracked)
            if key in seen:continue
            seen.add(key);queue.append(len(states));states.append(child);parents.append(current);moves.append(index)
    assert len(states)==68040,len(states)
    print('complete setup projection',len(states),'seconds',round(monotonic()-begun,3),flush=True)
    def word(i):
        result=[]
        while parents[i]>=0:result.append(moves[i]);i=parents[i]
        return tuple(reversed(result))
    def inverse(seq):return tuple(g.at[g.atoms[i].inverse(4)] for i in reversed(seq))
    def compose(seq):
        rows=[bytes(range(256))]*len(g.actions[0])
        for i in seq:rows=[row.translate(table) for row,table in zip(rows,g.actions[i])]
        return tuple(rows)
    catalogue={};full_checks=0
    # T is tracked forwards. Its inverse places the four affected octants at
    # the selected U face. All other octants cancel between T^-1 and T.
    for number,frames in enumerate(states):
        direct=word(number);setup=inverse(direct)
        quarter=setup+(g.at[Move(primary,0,1)],g.at[Move(primary,1,3)])+direct
        # Test corner owners first, before compiling the remaining units.
        allowed=True
        for p,corner in g.corners:
            pose=identity
            for i in quarter:
                pose=g.transitions[p][pose][i]
                if pose==255:allowed=False;break
            if not allowed:break
            assert pose==identity
        if not allowed:continue
        tables=compose(quarter)
        for amount in (1,2,3):
            seq=setup+(g.at[Move(primary,0,amount)],g.at[Move(primary,1,(-amount)%4)])+direct
            actual=compose(seq);key=g.signature(actual)
            if amount==1:powered=tables
            else:powered=tuple(row.translate(table) for row,table in zip(powered,tables))
            assert key==g.signature(powered)
            full_checks+=1
            old=catalogue.get(key)
            if old is None or len(seq)<len(old[0]):catalogue[key]=(seq,actual)
    # Positive R/F inner slices must also belong to this complete conjugacy
    # class. This checks that a single U-face projection suffices.
    for face in g.inner_faces:
        assert g.signature(compose((g.at[Move(face,0,1)],g.at[Move(face,1,3)]))) in catalogue
    records=sorted(catalogue.values(),key=lambda item:(len(item[0]),item[0]))
    from solver.camouflage_octants import fingerprint
    header=dict(version=1,geometry=fingerprint(kind),setups=len(states),macros=len(records),blocks=len(g.actions[0]),
                checked_powers=full_checks,positive_inner_axes=3)
    encoded=json.dumps(header,separators=(',',':')).encode();blob=bytearray()
    for seq,tables in records:
        blob.extend(bytes([len(seq)]));blob.extend(seq)
        for table in tables:blob.extend(table)
    destination=Path(__file__).resolve().parents[1]/f'solver/data/{kind}_octants.bin'
    destination.write_bytes(b'CO01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(blob,9))
    print(header,'bytes',destination.stat().st_size,'seconds',round(monotonic()-begun,3),flush=True)
    from sympy.combinatorics import Permutation,PermutationGroup
    from tools.weighted_group_builder import build
    from solver.camouflage_octants import corner_permutation
    pool={corner_permutation(g,half(root,i)):(i,) for i in halves}
    group=PermutationGroup([Permutation(list(p)) for p in pool]);group.schreier_sims()
    assert group.order()==3674160
    def compact(seq):
        out=[]
        for i in seq:
            if out and g.atoms[out[-1]].axis==g.atoms[i].axis:
                previous=out.pop();amount=(g.atoms[previous].amount+g.atoms[i].amount)%4
                if amount:out.append(g.at[Move(g.atoms[i].axis,1,amount)])
            else:out.append(i)
        return tuple(out)
    transversals=build(pool,group.base,group.basic_orbits,group.orbits(),compact,inverse)
    # Check every exported corner word independently on all eight owners.
    for orbit in transversals:
        for entry in orbit.values():
            state=root
            for index in entry['word']:state=half(state,index)
            assert corner_permutation(g,state)==tuple(entry['permutation'])
    data=dict(version=1,geometry=fingerprint(kind),order=str(group.order()),base=group.base,transversals=transversals)
    corner_file=destination.with_name(f'{kind}_corners.bin')
    corner_file.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('corner table',corner_file.stat().st_size,'bytes; total seconds',round(monotonic()-begun,3),flush=True)


if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'camouflage_3')
