"""Offline CAD polygonisation and analytic whole-volume certificate builder."""
import sys,json,zlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.twins_cad_material import *
from cube.spherical_cells import Arrangement
from tools.cad_face_regions import curves_from_entities,face_regions,with_central_radius
from tools.preview_twins_cad import face_point


def main():
    started=time.monotonic();source=json.loads(Path('tests/data/twins_face_curves.json').read_text())
    if source['source_sha256']!=CAD_SHA256:raise ValueError('Unexpected CAD reference')
    curves=with_central_radius(curves_from_entities(source['entities']),CENTRAL_RADIUS*5)
    regions,paths=face_regions(curves)
    if len(regions)!=32:raise ValueError('Radius changes the face topology')
    groups=[];panels=[]
    for f,n in enumerate(CUBE):
        for poly in regions:
            label=poly.representative_point();g=point_group(face_point(n,(label.x,label.y)))
            if g not in groups:groups.append(g)
            panels.append((groups.index(g),f,tuple(face_point(n,p) for p in list(poly.exterior.coords)[:-1])))
    print('visible',len(groups),'fields',len(panels),flush=True)
    arrangement=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    print('analytic vertices',len(arrangement.vertices),flush=True)
    masks=arrangement.positive_masks();all_groups={group(m) for m in masks}
    if not set(groups)<=all_groups:raise ValueError('Visible CAD field lacks a positive volume')
    groups+=sorted(all_groups-set(groups))
    # Whole-cell membership, including hidden material, is a certificate that
    # the 24 proper cube symmetries preserve the declared CSG partition.
    from cube.appearance import ROTATIONS
    for frame in ROTATIONS:
        targets={transform_group(g,frame_action(frame)) for g in groups}
        if targets!=set(groups):raise ValueError('CSG group is not symmetry closed')
    payload=dict(version=1,source=fingerprint(),groups=groups,atoms=masks,panels=panels,
                 provenance='Drawing3 face; provisional symmetric CSG extension; regular turns only')
    out=Path('cube/data/twins_cad_regular.bin');out.write_bytes(zlib.compress(json.dumps(payload,separators=(',',':')).encode(),9))
    print(dict(groups=len(groups),atoms=len(masks),bytes=out.stat().st_size,seconds=time.monotonic()-started),flush=True)


if __name__=='__main__':main()
