"""Cached curved Drawing3 skins, with the shared entry seams and controls."""
import json,zlib,struct
from pathlib import Path
from functools import lru_cache
from cube.twins_cad_material import structure,fingerprint
from cube.appearance import transform_frame
from cube.polyhedral import CUBE,triangulate
from renderer.comet_view import CometView
from renderer.copter_view import CopterTwistView
from renderer.polyhedral_view import CUBE_PALETTE


@lru_cache(maxsize=1)
def skin_data():
    payload=zlib.decompress((Path(__file__).resolve().parents[1]/'cube/data/twins_cad_skin.bin').read_bytes())
    size=struct.unpack_from('<I',payload)[0];d=json.loads(payload[4:4+size]);offset=4+size
    if d['version']!=3 or d['source']!=fingerprint() or len(d['counts'])!=len(structure()[0]):raise ValueError('Stale Twins CAD skin')
    pools=[]
    for count in (d['points'],d['normals']):
        end=offset+12*count;pools.append(tuple(struct.iter_unpack('<3f',payload[offset:end])));offset=end
    if len(payload)-offset!=24*sum(d['counts']):raise ValueError('Invalid Twins CAD skin length')
    points,normals=pools;records=iter(struct.iter_unpack('<IIIIii',payload[offset:]));rows=[];axes=[];panels=structure()[2]
    for h,count in enumerate(d['counts']):
        row=[];ids=[]
        for _ in range(count):
            a,b,c,n,slot,axis=next(records)
            if slot<-1 or slot>=len(panels) or slot>=0 and panels[slot][0]!=h:raise ValueError('Invalid Twins field owner')
            if (slot>=0 and axis!=-1) or (slot<0 and axis not in range(20)):raise ValueError('Invalid Twins cut index')
            row.append(((points[a],points[b],points[c]),normals[n],slot));ids.append(axis)
        rows.append(tuple(row));axes.append(tuple(ids))
    return tuple(rows),tuple(axes)


@lru_cache(maxsize=1)
def outer_surfaces():
    groups,regions,panels=structure();rows=[[] for _ in groups]
    for slot,(h,f,p) in enumerate(panels):rows[h].extend((t,CUBE[f],slot) for t in triangulate(p,CUBE[f]))
    return tuple(map(tuple,rows))


class TwinsCADView(CometView):
    def set_cube(self,cube):
        super().set_cube(cube);self.palette=CUBE_PALETTE

    def _surfaces(self,cube):
        shell_only=self._move is None and self.piece_filter is None
        turn_axis=self._move.axis if self._move is not None and self.piece_filter is None else None
        try:cube.aligned_permutation()
        except ValueError:
            shell_only=False;turn_axis=None
        cache_key=cube.frames,shell_only,self._move.axis if self._move is not None else None
        cached=getattr(self,'_twins_cad_placed',None)
        if cached is None or cached[0]!=cache_key:
            placed=[];rows=outer_surfaces() if shell_only else skin_data()[0]
            if not hasattr(cube,'frames') or len(cube.frames) < len(rows):
                return ()
            from renderer.cad_copter_visibility import visible_cuts
            moving=cube.selection(self._move.axis) if self._move is not None else ()
            exposed=visible_cuts(cube,'twins',moving) if not shell_only else None
            for h,parts in enumerate(rows):
                frame=cube.frames[h]
                for i,(tri,n,slot) in enumerate(parts):
                    if slot<0 and exposed is not None and skin_data()[1][h][i] not in exposed[h]:continue
                    placed.append((tuple(transform_frame(frame,p) for p in tri),transform_frame(frame,n),slot,h))
            self._twins_cad_placed=cache_key,tuple(placed)
        return tuple((p,n,cube.paints[s] if s>=0 and cube.paints[s]>=0 else -2 if s>=0 else -1,
                      s if s>=0 else None,0,h,1) for p,n,s,h in self._twins_cad_placed[1] if self.piece_filter is None or h==self.piece_filter)


class TwinsCADTwistView(TwinsCADView,CopterTwistView):
    edge_amount=180.
    corner_amount=120.
    def amount_for_axis(self,axis):return self.edge_amount if axis<12 else self.corner_amount
