from functools import lru_cache
from cube.edge_jumbling import layout
from renderer.twins_view import material_surfaces
from renderer.comet_view import CometView
from renderer.copter_view import CopterTwistView
from renderer.polyhedral_view import CUBE_PALETTE,PALETTE


class EdgeJumblingView(CometView):
    def _surfaces(self,cube):
        if getattr(self,'_edge_kind',None)!=cube.puzzle_kind:
            self._edge_kind=cube.puzzle_kind;self._placed_comet=None
        self.palette=CUBE_PALETTE if cube.color_count==6 else PALETTE
        if cube.puzzle_kind=='helicopter_14':
            from renderer.polyhedral_view import default_palette
            self.palette=default_palette(cube)
        if cube.puzzle_kind in ('clover','mf8_bauhinia_minx'):return placed_spheres(self,cube)
        self.home_surfaces=lambda:material_surfaces(profile(cube.puzzle_kind))
        return super()._surfaces(cube)


@lru_cache(maxsize=3)
def profile(kind):
    def factory():
        masks,solids,panels=layout(kind);return solids,panels
    return factory


class EdgeJumblingTwistView(EdgeJumblingView,CopterTwistView):pass


@lru_cache(maxsize=2)
def spherical_surfaces(kind):
    return spherical_skin(kind)[0]


@lru_cache(maxsize=2)
def spherical_skin(kind):
    from types import SimpleNamespace
    from cube.spherical_jumbling import layout,fingerprint
    from renderer.flower_copter_view import load_skin_data
    return load_skin_data(SimpleNamespace(fingerprint=lambda:fingerprint(kind),structure=lambda:layout(kind)),kind+'_jumbling_skin.bin')


@lru_cache(maxsize=4096)
def sphere_basis(kind,frame):
    from cube.curvy_copter import multiply
    from cube.appearance import ROTATIONS
    if kind=='clover':proper=ROTATIONS
    else:
        from cube.mirror_minx import frames
        proper=frames()
    key,q=min((tuple(round(v,8) for col in multiply(frame,p) for v in col),p) for p in proper)
    return key,tuple(tuple(q[j][i] for j in range(3)) for i in range(3))


@lru_cache(maxsize=128)
def sphere_action(kind,proper):
    from cube.spherical_jumbling import cuts
    from cube.appearance import transform_frame
    from cube.polyhedral import key
    cs=cuts(kind);lookup={key(c.centre):i for i,c in enumerate(cs)}
    return tuple(lookup[key(transform_frame(proper,c.centre))] for c in cs)


def placed_spheres(view,cube):
    from cube.appearance import transform_frame
    from cube.spherical_jumbling import cuts
    key=cube.frames,view._move.axis if view._move is not None else None
    cached=getattr(view,'_spheres_placed',None)
    if cached is None or cached[0]!=key:
        moving=set(cube.selection(view._move.axis)) if view._move is not None else set()
        placements=[];occupied=set();masks=set(cube.signatures)
        def transformed(mask,action):return sum(1<<a for i,a in enumerate(action) if mask&(1<<i))
        for h,f in enumerate(cube.frames):
            bucket,proper=sphere_basis(cube.puzzle_kind,f);bucket=bucket,h in moving
            action=sphere_action(cube.puzzle_kind,proper);placements.append((bucket,action))
            occupied.add((bucket,transformed(cube.signatures[h],action)))
        rows,ids=spherical_skin(cube.puzzle_kind);placed=[]
        for h,parts in enumerate(rows):
            bucket,action=placements[h];mask=cube.signatures[h]
            hidden={a for a in range(len(cuts(cube.puzzle_kind))) if mask^(1<<a) in masks
                    and (bucket,transformed(mask^(1<<a),action)) in occupied}
            for (tri,n,slot),axis in zip(parts,ids[h]):
                if slot<0 and axis in hidden:continue
                placed.append((tuple(transform_frame(cube.frames[h],p) for p in tri),transform_frame(cube.frames[h],n),slot,h))
        cached=key,tuple(placed);view._spheres_placed=cached
    return tuple((p,n,cube.paints[s] if s>=0 and cube.paints[s]>=0 else -2 if s>=0 else -1,
                  s if s>=0 else None,0,h,1) for p,n,s,h in cached[1] if view.piece_filter is None or h==view.piece_filter)


def build_spherical_surfaces(kind):
    from cube.spherical_jumbling import layout,cuts,normals
    from cube.polyhedral import triangulate
    from renderer.flower_copter_view import sphere_face
    masks,regions,panels=layout(kind);rows=[[] for _ in masks];ns=normals(kind)
    for i,(h,f,p) in enumerate(panels):rows[h].extend((t,ns[f],i,-1) for t in triangulate(p,ns[f]))
    for h,m in enumerate(masks):
        for axis in range(len(cuts(kind))):rows[h].extend((t,n,s,axis) for t,n,s in sphere_face(m,axis,cuts(kind),ns))
    return tuple(map(tuple,rows))
