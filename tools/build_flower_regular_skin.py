"""Precompute display-only cut surfaces so entering a model cannot mesh it."""
import sys,json,zlib,os,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from cube.flower_material import fingerprint
from renderer.flower_copter_view import build_surfaces

if __name__=='__main__':
    butter='--butterflower' in sys.argv
    if butter:
        from cube import butterflower_material as material
        fingerprint=material.fingerprint
        rows=build_surfaces(material)
    else:rows=build_surfaces()
    target=Path('cube/data')/('butterflower_regular_skin.bin' if butter else 'flower_regular_skin.bin')
    points={};normals={};records=[]
    def index(pool,p,precision):
        p=tuple(round(v,precision) for v in p)
        if p not in pool:pool[p]=len(pool)
        return pool[p]
    for row in rows:
        for triangle,n,slot,axis in row:
            records.append(tuple(index(points,p,7) for p in triangle)+(index(normals,n,6),slot,axis))
    data=dict(version=3,source=fingerprint(),counts=list(map(len,rows)),points=len(points),normals=len(normals))
    header=json.dumps(data,separators=(',',':')).encode()
    payload=bytearray(struct.pack('<I',len(header))+header)
    for pool in (points,normals):
        for p in pool:payload.extend(struct.pack('<3f',*p))
    for row in records:payload.extend(struct.pack('<IIIIii',*row))
    target.write_bytes(zlib.compress(payload,9))
    print('triangles',sum(map(len,rows)),'bytes',target.stat().st_size)
