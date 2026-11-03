"""Offline closed skins; no meshing on the phone's UI thread."""
import sys,json,struct,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.spherical_jumbling import fingerprint
from renderer.edge_jumbling_view import build_spherical_surfaces

for kind in ('clover','mf8_bauhinia_minx'):
    rows=build_spherical_surfaces(kind);points={};normals={};records=[]
    def index(pool,p):
        p=tuple(p)
        if p not in pool:pool[p]=len(pool)
        return pool[p]
    for row in rows:
        for tri,n,slot,axis in row:records.append((*[index(points,p) for p in tri],index(normals,n),slot,axis))
    meta=json.dumps(dict(version=3,source=fingerprint(kind),counts=list(map(len,rows)),points=len(points),normals=len(normals))).encode()
    payload=struct.pack('<I',len(meta))+meta
    payload+=b''.join(struct.pack('<3f',*p) for pool in (points,normals) for p in pool)
    payload+=b''.join(struct.pack('<IIIIii',*r) for r in records)
    path=Path('cube/data')/(kind+'_jumbling_skin.bin');path.write_bytes(zlib.compress(payload,9))
    print(kind,len(records),path.stat().st_size,flush=True)
