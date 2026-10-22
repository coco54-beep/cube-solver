"""Polygon observations for Mixup/Tangram, independent of piece numbering.

The entry records projected panel outlines and colours. Candidate identities
are inferred from the model; remembered scrambles are never used for matching.
"""
from collections import OrderedDict,defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
import math
from time import monotonic

from cube.articulated import ArticulatedCube,frame_key
from cube.appearance import ROTATIONS,transform_frame
from cube.coordinates import FACE_SPEC
from cube.polyhedral import CUBE,dot,cross,add,scale,unit,clip

FACES=('U','R','F','D','L','B')
FACE_ORDER=(2,1,5,4,0,3)
EPS=1e-6
_CACHE=OrderedDict()
_PROPER=frozenset(frame_key(f) for f in ROTATIONS)


def new_cube(kind):
    if kind.startswith('mixup_'):
        from cube.mixup import MixupCube
        return MixupCube(kind)
    return ArticulatedCube(kind)


def polygon_key(points):
    # Winding and cyclic start are irrelevant; convex model panels have a
    # unique boundary once their vertex set is known.
    return tuple(sorted(tuple(round(v,6) for v in p) for p in points))


def project(points,face):
    axis,sign,ra,rs,ca,cs=FACE_SPEC[FACES[face]]
    return tuple((p[ca]*cs,-p[ra]*rs) for p in points)


def contains(points,point):
    signs=[(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
           for a,b in zip(points,points[1:]+points[:1])]
    return bool(signs) and (min(signs)>=-EPS or max(signs)<=EPS)


def normal(points):
    value=(0.,0.,0.)
    for a,b in zip(points,points[1:]+points[:1]):value=add(value,cross(a,b))
    return unit(value)


def shape_key(points):
    """Group translated/rotated outlines without exposing home identities."""
    return len(points),tuple(sorted(round(sum((a-b)**2 for a,b in zip(p,q)),5)
                                   for p,q in combinations(points,2)))


def centre2(points):return tuple(sum(p[a] for p in points)/len(points) for a in range(2))


def face_world(outline,face):
    axis,sign,ra,rs,ca,cs=FACE_SPEC[FACES[face]]
    result=[]
    for u,v in outline:
        point=[0.,0.,0.];point[axis]=sign;point[ca]=u*cs;point[ra]=-v*rs;result.append(tuple(point))
    return tuple(result)


@lru_cache(maxsize=1)
def color_templates():
    """A fixed fine partition for Tangram's colour-only entry.

    Overlay the model's possible cut lines. Every candidate panel is a union
    of these cells, so painting colours never asks for a piece orientation.
    Cells are observation areas, not additional physical pieces.
    """
    cube=new_cube('tangram');result=[]
    for face in range(6):
        lines=set()
        for home in range(len(cube.solids)):
            for pose in range(len(cube.orientations)):
                for panel in _panels(cube,home,pose,face):
                    for a,b in zip(panel.outline,panel.outline[1:]+panel.outline[:1]):
                        nx,ny=b[1]-a[1],a[0]-b[0];length=math.hypot(nx,ny)
                        if length<EPS:continue
                        nx/=length;ny/=length;bound=nx*a[0]+ny*a[1]
                        if nx<-EPS or (abs(nx)<EPS and ny<0):nx,ny,bound=-nx,-ny,-bound
                        if abs(bound)<abs(nx)+abs(ny)-EPS:lines.add((round(nx,7),round(ny,7),round(bound,7)))
        cells=[((-1.,-1.,0.),(1.,-1.,0.),(1.,1.,0.),(-1.,1.,0.))]
        for nx,ny,bound in sorted(lines):
            parts=[]
            for cell in cells:
                values=[nx*p[0]+ny*p[1]-bound for p in cell]
                if min(values)<-EPS and max(values)>EPS:
                    parts.extend((clip(cell,(nx,ny,0.),bound),clip(cell,(-nx,-ny,0.),-bound)))
                else:parts.append(cell)
            cells=parts
        result.append(tuple(tuple((p[0],p[1]) for p in cell) for cell in cells))
    return tuple(result)


@dataclass(frozen=True)
class Panel:
    home:int
    pose:int
    color:int
    world:tuple
    outline:tuple
    depth:float
    n:tuple


def _panels(cube,home,pose,face,color=None):
    frame=cube.orientations[pose];axis,sign,*_=FACE_SPEC[FACES[face]]
    for points,c in cube.solids[home].faces:
        if c<0 or (color is not None and color!=c):continue
        n=transform_frame(frame,CUBE[c])
        if n[axis]*sign<=EPS:continue
        world=tuple(transform_frame(frame,p) for p in points)
        yield Panel(home,pose,c,world,project(world,face),
                    round(sum(p[axis]*sign for p in world)/len(world),6),n)


def catalog(kind,face,color,guard):
    cache_key=(kind,face,color)
    if cache_key in _CACHE:
        result=_CACHE[cache_key];_CACHE.move_to_end(cache_key);return result
    cube=new_cube(kind);result=[]
    for home,solid in enumerate(cube.solids):
        # None requests every coloured panel (the shape-and-colour gallery).
        # It is not a colour that a solid must carry.
        if color is not None and not any(c==color for _,c in solid.faces):continue
        for pose,frame in enumerate(cube.orientations):
            guard()
            if cube.family=='mixup' and solid.role=='corner' and frame_key(frame) not in _PROPER:continue
            result.extend(_panels(cube,home,pose,face,color))
    result=tuple(result);_CACHE[cache_key]=result
    while len(_CACHE)>2:_CACHE.popitem(last=False)
    return result


def outlines_at(kind,face,color,point,cancelled=None,seconds=5.):
    deadline=monotonic()+seconds
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline:raise ValueError('observe.timeout')
    groups=defaultdict(list)
    for panel in catalog(kind,face,color,guard):
        guard()
        if contains(panel.outline,point):groups[polygon_key(panel.outline)].append(panel)
    result=[]
    for panels in groups.values():
        outline=panels[0].outline
        centre=tuple(sum(p[a] for p in outline)/len(outline) for a in range(2))
        result.append({'outline':outline,'panels':tuple(panels),'shape':shape_key(outline),
                       'distance':sum((a-b)**2 for a,b in zip(centre,point))})
    return sorted(result,key=lambda item:item['distance'])


def colored_outlines_at(kind,face,point,cancelled=None,seconds=5.):
    """All colour/shape choices at an observed point, without six cache scans."""
    deadline=monotonic()+seconds
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline:raise ValueError('observe.timeout')
    groups=defaultdict(list)
    for panel in catalog(kind,face,None,guard):
        guard()
        if contains(panel.outline,point):groups[panel.color,polygon_key(panel.outline)].append(panel)
    choices=[]
    for (color,_),panels in groups.items():
        outline=panels[0].outline;centre=centre2(outline)
        choices.append({'outline':outline,'panels':tuple(panels),'color':color,
                        'shape':shape_key(outline),
                        'distance':sum((a-b)**2 for a,b in zip(centre,point))})
    return sorted(choices,key=lambda option:(option['distance'],option['color'],polygon_key(option['outline'])))


def colored_outlines_on_ray(kind, face, ray, cancelled=None, seconds=5.):
    """Physical panels under the same screen ray, keeping their actual depth."""
    deadline = monotonic() + seconds
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic() > deadline:raise ValueError('observe.timeout')
    origin, direction = ray
    groups = defaultdict(list)
    distances = {}
    cube = new_cube(kind)
    bodies = {}
    for panel in catalog(kind, face, None, guard):
        guard()
        denominator = dot(panel.n, direction)
        if abs(denominator) < EPS:continue
        t = (dot(panel.n, panel.world[0]) - dot(panel.n, origin)) / denominator
        if t < 0:continue
        point = add(origin, scale(direction, t))
        if not contains(panel.outline, project((point,), face)[0]):continue
        identity = panel.home, panel.pose
        if identity not in bodies:
            from cube.articulated import vertices
            faces = cube.placed_faces(*identity)
            bodies[identity] = (tuple(sorted(polygon_key(p) for p, _ in faces)), shape_key(vertices(faces)))
        body, body_shape = bodies[identity]
        key = panel.color, polygon_key(panel.world), body
        groups[key].append(panel)
        distances[key] = min(distances.get(key, t), t)
    return sorted(({'outline': panels[0].outline, 'panels': tuple(panels), 'color': key[0],
                    'shape': (shape_key(panels[0].world), bodies[panels[0].home, panels[0].pose][1]),
                    'distance': distances[key], 'physical': True}
                   for key, panels in groups.items()), key=lambda p: (p['distance'], p['color'], polygon_key(p['outline'])))


@lru_cache(maxsize=16384)
def _tangram_panel_pair_fits(kind, left, right, face, other_face):
    # Shared projections can be legitimate on a deformed puzzle. Check the
    # solid volumes and visible skins instead of banning all 2D overlap.
    if polygon_key(left.world) == polygon_key(right.world):return face != other_face
    cube = new_cube(kind)
    lf = cube.placed_faces(left.home, left.pose)
    rf = cube.placed_faces(right.home, right.pose)
    same_body = tuple(sorted(polygon_key(p) for p, _ in lf)) == tuple(sorted(polygon_key(p) for p, _ in rf))
    if not same_body:
        from cube.articulated import overlap
        if overlap(lf, rf):return False
    if dot(right.n, CUBE[face]) > EPS:
        projected = Panel(right.home, right.pose, right.color, right.world, project(right.world, face), right.depth, right.n)
        if not _visible(left, (left, projected), face):return False
    if dot(left.n, CUBE[other_face]) > EPS:
        projected = Panel(left.home, left.pose, left.color, left.world, project(left.world, other_face), left.depth, left.n)
        if not _visible(right, (right, projected), other_face):return False
    return True


@lru_cache(maxsize=2048)
def panels_for_outline(kind, face, key):
    return tuple(p for p in catalog(kind, face, None, lambda: None) if polygon_key(p.outline) == key)


@lru_cache(maxsize=1024)
def observation_body_key(kind, home, pose):
    return tuple(sorted(polygon_key(p) for p, _ in new_cube(kind).placed_faces(home, pose)))


def fitting_tangram_panel(kind, face, option, items, replaced_key=None, views=None):
    """Reject local geometric collisions without requiring colours to be solved.

    Colours may be temporarily inconsistent while the user edits other faces.
    Global piece identities and cross-view consistency remain matcher checks.
    """
    observations = enumerate(views) if views is not None else ((face, items),)
    neighbors = [(f, item) for f, group in observations for item in group
                 if f != face or polygon_key(item['outline']) != replaced_key]
    if not neighbors:return next(iter(option['panels']), None)
    choices = []
    for other_face, item in neighbors:
        key = polygon_key(item['outline'])
        choices.append((other_face, [p for p in panels_for_outline(kind, other_face, key)
                        if (item.get('depth') is None or abs(p.depth - item['depth']) < EPS)
                        and (not item.get('world_fixed') or polygon_key(p.world) == polygon_key(item['preview']))
                        and (not item.get('body_key') or observation_body_key(kind, p.home, p.pose) == item['body_key'])]))
    return next((panel for panel in option['panels']
                 if all(any(_tangram_panel_pair_fits(kind, panel, other, face, f) for other in group)
                        for f, group in choices)), None)


def tangram_panel_fits(kind, face, option, items, replaced_key=None, views=None):
    return fitting_tangram_panel(kind, face, option, items, replaced_key, views) is not None


class ObservationDraft:
    def __init__(self,kind,state=None):
        self.kind=kind;self.views=[[] for _ in range(6)];self.complete=[False]*6;self.regions=[]
        if state is None:return
        if state.get('kind')!=kind or state.get('version')!=1:raise ValueError('observe.invalid')
        views=state['views'];complete=state['complete']
        if len(views)!=6 or len(complete)!=6:raise ValueError('observe.invalid')
        for face,items in enumerate(views):
            if len(items)>512:raise ValueError('observe.invalid')
            for item in items:
                points=tuple(tuple(float(v) for v in p) for p in item['outline'])
                if not 3<=len(points)<=16 or any(len(p)!=2 or any(not math.isfinite(v) or abs(v)>3 for v in p) for p in points):raise ValueError('observe.invalid')
                color=item['color'];depth=item.get('depth')
                if type(color) is not int or not 0<=color<6:raise ValueError('observe.invalid')
                if depth is not None and (not math.isfinite(depth) or abs(depth)>3):raise ValueError('observe.invalid')
                preview=tuple(tuple(float(v) for v in p) for p in item.get('preview',()))
                if len(preview)!=len(points) or any(len(p)!=3 or any(not math.isfinite(v) or abs(v)>3 for v in p) for p in preview):raise ValueError('observe.invalid')
                roles=item.get('roles')
                if roles is not None and (not isinstance(roles,(list,tuple)) or not roles or
                    any(role not in ('centre','edge','inner_edge','corner','cap','band') for role in roles)):
                    raise ValueError('observe.invalid')
                self.views[face].append({'outline':points,'color':color,'depth':depth,'preview':preview,'region':int(item.get('region',0)),
                    'sample':bool(item.get('sample',False)),'world_fixed':bool(item.get('world_fixed',False)),
                    'roles':tuple(roles) if roles is not None else None,
                    'body_key':tuple(tuple(tuple(float(v) for v in p) for p in poly) for poly in item['body_key']) if item.get('body_key') else None})
        self.complete=[bool(v) for v in complete]
        for region in state.get('regions',()):
            face=int(region['face']);count=int(region['count']);bounds=tuple(float(v) for v in region['bounds'])
            if not 0<=face<6 or not 1<=count<=12 or len(bounds)!=4 or any(not math.isfinite(v) or abs(v)>3 for v in bounds) or bounds[0]>=bounds[2] or bounds[1]>=bounds[3]:raise ValueError('observe.invalid')
            self.regions.append({'face':face,'count':count,'bounds':bounds,'complete':bool(region['complete'])})
        for face,view in enumerate(self.views):
            if any(not 0<=p['region']<=len(self.regions) or (p['region'] and self.regions[p['region']-1]['face']!=face) for p in view):raise ValueError('observe.invalid')
        # Tangram variants no longer expose regional count entry. Preserve
        # colours when migrating an older draft, rather than clearing it.
        if kind.startswith('tangram'):
            self.regions=[]
            for view in self.views:
                for p in view:p['region']=0
        if kind=='tangram':
            for face,old in enumerate(self.views):
                items=[]
                for outline in color_templates()[face]:
                    colors={p['color'] for p in old if contains(p['outline'],centre2(outline))}
                    if len(colors)==1:items.append({'outline':outline,'color':next(iter(colors)),
                        'depth':None,'preview':face_world(outline,face),'region':0,'sample':True})
                self.views[face]=items
                self.complete[face]=self.complete[face] and len(items)==len(color_templates()[face])

    def state(self):
        return {'version':1,'kind':self.kind,'views':[[dict(p) for p in view] for view in self.views],
                'complete':list(self.complete),'regions':[dict(r) for r in self.regions]}

    def record(self,face,option,color,depth=None,region=0):
        panels=[p for p in option['panels'] if depth is None or abs(p.depth-depth)<EPS]
        if not panels:raise ValueError('observe.invalid')
        item={'outline':option['outline'],'color':color,'depth':depth,'preview':panels[0].world,'region':region}
        signature=polygon_key(item['outline'])
        for index,old in enumerate(self.views[face]):
            if polygon_key(old['outline'])==signature:
                self.views[face][index]=item;break
        else:self.views[face].append(item)
        self.complete[face]=False

    def paint_samples(self,face,indices,color):
        if self.kind!='tangram' or not 0<=color<6:raise ValueError('observe.invalid')
        templates=color_templates()[face]
        for index in indices:
            outline=templates[index];signature=polygon_key(outline)
            self.views[face]=[p for p in self.views[face] if polygon_key(p['outline'])!=signature]
            self.views[face].append({'outline':outline,'color':color,'depth':None,
                'preview':face_world(outline,face),'region':0,'sample':True})
        self.complete[face]=len(self.views[face])==len(templates)

    @classmethod
    def from_cube(cls,cube):
        draft=cls(cube.puzzle_kind)
        panels=[list(p for h,pose in enumerate(cube.frames) for p in _panels(cube,h,pose,f)) for f in range(6)]
        for face,view in enumerate(panels):
            if cube.puzzle_kind=='tangram':
                for outline in color_templates()[face]:
                    point=centre2(outline);cover=[p for p in view if contains(p.outline,point)]
                    if not cover:continue
                    panel=max(cover,key=lambda p:_depth(p,point,face))
                    draft.views[face].append({'outline':outline,'color':panel.color,'depth':None,
                        'preview':face_world(outline,face),'region':0,'sample':True})
                continue
            for p in view:
                if _visible(p,view,face):
                    draft.views[face].append({'outline':p.outline,'color':p.color,'depth':p.depth,'preview':p.world})
        draft.complete=[len(draft.views[f])==len(color_templates()[f]) if cube.puzzle_kind=='tangram' else True for f in range(6)]
        return draft


def _depth(panel,point,face):
    axis,sign,ra,rs,ca,cs=FACE_SPEC[FACES[face]]
    n=panel.n;p=panel.world[0]
    return sign*(dot(n,p)-n[ca]*point[0]*cs+n[ra]*point[1]*rs)/n[axis]


def _visible(panel,view,face):
    centre=tuple(sum(p[a] for p in panel.outline)/len(panel.outline) for a in range(2))
    # Visibility at interior witnesses; a partially occluded panel can be
    # recorded by its model outline, with hidden continuation left implicit.
    samples=[centre]+[tuple(.8*v+.2*c for v,c in zip(p,centre)) for p in panel.outline]
    for point in samples:
        depth=_depth(panel,point,face)
        if all(other is panel or not contains(other.outline,point) or
               _depth(other,point,face)<=depth+EPS for other in view):return True
    return False


@dataclass
class ObservationMatch:
    status:str
    cube:object=None
    face:int=None


def match_observations(draft,cancelled=None,seconds=8.,node_limit=10000):
    """Bounded exact cover of observed panels and rigid model pieces.

    A unique model assembly is not a proof of reachability or solvability.
    Unknown pieces never inherit the solved pose or a remembered scramble.
    """
    deadline=monotonic()+seconds;nodes=0;cube=new_cube(draft.kind)
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline or nodes>=node_limit:raise TimeoutError()
    observations=[(f,p) for f,view in enumerate(draft.views) for p in view]
    if not observations:return ObservationMatch('incomplete')
    for index,region in enumerate(draft.regions,1):
        if not region['complete'] or sum(p.get('region',0)==index for p in draft.views[region['face']])!=region['count']:
            return ObservationMatch('incomplete',face=region['face'])
    placements={};by_home=defaultdict(set);by_obs=[set() for _ in observations];body_cache={}
    try:
        queries=defaultdict(lambda:defaultdict(list))
        for index,(face,item) in enumerate(observations):
            queries[face,item['color']][polygon_key(item['outline'])].append(index)
        for (face,color),outlines in queries.items():
            for panel in catalog(draft.kind,face,color,guard):
                guard()
                indices=([index for values in outlines.values() for index in values
                          if contains(panel.outline,centre2(observations[index][1]['outline']))]
                         if draft.kind=='tangram' else outlines.get(polygon_key(panel.outline),()))
                for index in indices:
                    item=observations[index][1]
                    if item['depth'] is not None and abs(panel.depth-item['depth'])>EPS:continue
                    if item.get('roles') is not None and cube.solids[panel.home].role not in item['roles']:continue
                    if item.get('world_fixed') and polygon_key(panel.world)!=polygon_key(item['preview']):continue
                    if item.get('body_key') is not None:
                        identity=(panel.home,panel.pose)
                        if identity not in body_cache:
                            body_cache[identity]=tuple(sorted(polygon_key(poly) for poly,color in cube.placed_faces(*identity)))
                        if body_cache[identity]!=item['body_key']:continue
                    k=(panel.home,panel.pose);placements[k]=placements.get(k,0)|(1<<index)
                    by_home[panel.home].add(k);by_obs[index].add(k)
        for index,options in enumerate(by_obs):
            if not options:return ObservationMatch('conflict',face=observations[index][0])
        if len(by_home)<len(cube.solids):return ObservationMatch('incomplete')
        signatures={};faces_cache={}
        for k in placements:
            guard();home,pose=k;faces=cube.placed_faces(home,pose);faces_cache[k]=faces
            signatures[k]=(cube.solids[home].role,
                tuple(round(v,6) for v in transform_frame(cube.orientations[pose],cube.solids[home].anchor)),
                tuple(sorted((c,polygon_key(poly)) for poly,c in faces)))
        unique={};redundant=set()
        for k,mask in placements.items():
            signature=k[0],signatures[k],mask
            if signature in unique:redundant.add(k)
            else:unique[signature]=k
        for k in redundant:
            del placements[k];by_home[k[0]].discard(k)
        for options in by_obs:options.difference_update(redundant)
        # Equivalent homes have the same candidate geometry AND observation
        # coverage. Canonical assignment avoids factorial duplicate searches.
        groups=defaultdict(list)
        for home,options in by_home.items():
            groups[tuple(sorted((signatures[k],placements[k]) for k in options))].append(home)
        equivalent={h:tuple(sorted(homes)) for homes in groups.values() for h in homes}
        target=(1<<len(observations))-1;solutions=[];first=None
        from cube.mixup import skins_cross
        intersects=skins_cross
        if cube.family!='mixup':
            from cube.articulated import overlap
            intersects=overlap
        def valid_complete(chosen):
            for face in range(6):
                guard()
                view=[p for home,pose in chosen for p in _panels(cube,home,pose,face)]
                if draft.kind=='tangram':
                    if draft.complete[face] and len(draft.views[face])!=len(color_templates()[face]):return False
                    for item in draft.views[face]:
                        point=centre2(item['outline']);cover=[p for p in view if contains(p.outline,point)]
                        if not cover or max(cover,key=lambda p:_depth(p,point,face)).color!=item['color']:return False
                    continue
                recorded={(p['color'],polygon_key(p['outline'])) for p in draft.views[face]}
                if draft.complete[face] and any((p.color,polygon_key(p.outline)) not in recorded and _visible(p,view,face) for p in view):return False
                for item in draft.views[face]:
                    if not any(p.color==item['color'] and polygon_key(p.outline)==polygon_key(item['outline']) and
                               (item['depth'] is None or abs(p.depth-item['depth'])<EPS) and _visible(p,view,face) for p in view):return False
            return True
        def visit(covered,chosen,homes):
            nonlocal nodes,first
            guard();nodes+=1
            if covered==target:
                if len(homes)!=len(cube.solids) or not valid_complete(chosen):return
                signature=tuple(sorted(signatures[k] for k in chosen))
                if signature not in solutions:
                    solutions.append(signature)
                    if first is None:first=tuple(chosen)
                return
            candidates=None
            for index,options in enumerate(by_obs):
                if covered>>index&1:continue
                available=[k for k in options if k[0] not in homes and not placements[k]&covered and
                           all(h in homes or h>=k[0] for h in equivalent[k[0]])]
                if not available:return
                if candidates is None or len(available)<len(candidates):candidates=available
            for k in sorted(candidates):
                guard()
                if any(intersects(faces_cache[k],faces_cache[old]) for old in chosen):continue
                visit(covered|placements[k],chosen+(k,),homes|{k[0]})
                if len(solutions)>1:return
        visit(0,(),set())
        if len(solutions)>1:return ObservationMatch('ambiguous')
        if not solutions:return ObservationMatch('conflict')
        frames=[None]*len(cube.solids)
        for home,pose in first:frames[home]=pose
        cube.colors=frames
        return ObservationMatch('matched',cube)
    except TimeoutError:return ObservationMatch('timeout')
