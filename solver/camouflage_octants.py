"""Offline-compiled conjugates and projected Camouflage macro distances."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
import zlib


@lru_cache(maxsize=1)
def fingerprint(kind='camouflage_3'):
    from solver.cuboid_search import search_model
    from cube.cuboid import layout
    return hashlib.sha256(repr((search_model(kind),layout(kind)[:2])).encode()).hexdigest()


def corner_permutation(g,poses):
    from cube.cuboid import transform
    from cube.appearance import ROTATIONS
    atoms=[]
    for p,corner in g.corners:
        for axis,v in enumerate(corner):
            atoms.append((corner,tuple((1 if v>0 else -1) if a==axis else 0 for a in range(3))))
    slots={item:i for i,item in enumerate(atoms)};result=[]
    for i,pose in enumerate(poses):
        for point,normal in atoms[i*3:i*3+3]:
            result.append(slots[transform(ROTATIONS[pose],point),transform(ROTATIONS[pose],normal)])
    return tuple(result)


@lru_cache(maxsize=1)
def corner_table(kind='camouflage_3'):
    data=json.loads(zlib.decompress((Path(__file__).parent/f'data/{kind}_corners.bin').read_bytes()))
    if data.get('version')!=1 or data.get('geometry')!=fingerprint(kind) or data.get('order')!='3674160':
        raise ValueError('cuboid.identity_unreachable')
    return data


@lru_cache(maxsize=1)
def quotient_patterns(kind='camouflage_3'):
    raw=(Path(__file__).parent/f'data/{kind}_quotient_patterns.bin').read_bytes()
    size=struct.unpack_from('<I',raw,4)[0];header=json.loads(raw[8:8+size]);blob=zlib.decompress(raw[8+size:])
    if raw[:4]!=b'CQ01' or header.get('version')!=1 or header.get('geometry')!=fingerprint(kind):
        raise ValueError('cuboid.identity_unreachable')
    rows=[];offset=0
    for record in header['patterns']:
        positions=[];count=1
        for p,poses in zip(record['pieces'],record['poses']):
            lookup=[255]*256
            for i,pose in enumerate(poses):lookup[(p%8)*24+pose]=i
            positions.append((p,len(poses),bytes(lookup)));count*=len(poses)
        if count!=record['size']:raise ValueError('cuboid.identity_unreachable')
        rows.append((tuple(positions),memoryview(blob)[offset:offset+count]));offset+=count
    if offset!=len(blob):raise ValueError('cuboid.identity_unreachable')
    return tuple(rows)


@lru_cache(maxsize=1)
def catalogue(kind='camouflage_3'):
    raw=(Path(__file__).parent/f'data/{kind}_octants.bin').read_bytes()
    size=struct.unpack_from('<I',raw,4)[0];header=json.loads(raw[8:8+size]);blob=zlib.decompress(raw[8+size:])
    if (raw[:4]!=b'CO01' or header.get('version')!=1 or header.get('geometry')!=fingerprint(kind)
            or header.get('setups')!=68040 or header.get('positive_inner_axes')!=3):
        raise ValueError('cuboid.identity_unreachable')
    words=[];actions=[];offset=0;blocks=header['blocks']
    for _ in range(header['macros']):
        count=blob[offset];offset+=1;words.append(tuple(blob[offset:offset+count]));offset+=count
        actions.append(tuple(blob[offset+i*256:offset+(i+1)*256] for i in range(blocks)));offset+=blocks*256
    if offset!=len(blob):raise ValueError('cuboid.identity_unreachable')
    from solver.camouflage_reduction import model
    g=model(kind);masks=[]
    for p,poses in enumerate(g.feasible):
        row=[0]*256
        for pose in poses:
            value=(p%8)*24+pose
            row[value]=sum(1<<i for i,tables in enumerate(actions) if tables[p//8][value]!=255)
        masks.append(tuple(row))
    return tuple(words),tuple(actions),tuple(masks),header
