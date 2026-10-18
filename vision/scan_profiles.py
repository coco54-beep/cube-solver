"""五阶以内、可按固定外表面取色的异形拍照模板。"""
from dataclasses import dataclass
import numpy as np

from cube.coordinates import FACE_NORMALS
from cube.polyhedral import CUBE, body_faces, geometry, mean, cross, unit
from renderer.mat4 import Mat4
from renderer.cube_orientation import CubeOrientation
from vision.colors import rgb_to_hsv
from vision import imageops

SUPPORTED = {
    'skewb': (3, 5), 'dino': (2, 4), 'clover': (3,), 'eight_petals': (3,),
    'ivy': (3,), 'void_cube': (3,), 'pandora': (3,),
    'pyraminx': (2, 3, 4, 5), 'fto': (2, 3, 4),
    'icosahedron': (2, 3, 4, 5),
    'megaminx': (2, 3, 4, 5), 'football': (3, 5), 'blossom': (3,),
    'moyu': (3, 4, 5), 'void_tower': (3,),
    'skewb_ultimate': (3,), 'void_minx': (3,), 'dino4': (2,),
}
DINO4_SCAN_PALETTE=((1,.85,0,1),(.9,.04,.05,1),(.06,.19,.9,1),(.98,.98,.98,1))
CUBE_CODES = ('W', 'R', 'G', 'Y', 'O', 'B')
DEFAULT_PALETTES = {
    6: ((.98,.98,.98,1),(.9,.04,.05,1),(.01,.65,.18,1),(1,.85,0,1),(1,.46,.01,1),(.06,.19,.9,1)),
    4: ((.91,.04,.04,1),(1,.85,0,1),(.06,.19,.9,1),(.01,.65,.18,1)),
    8: ((.98,.98,.98,1),(.02,.65,.18,1),(.9,.05,.06,1),(.51,.12,.73,1),
        (.97,.31,.61,1),(1,.47,.02,1),(.05,.2,.91,1),(.62,.86,.12,1)),
}
DEFAULT_PALETTES[20] = DEFAULT_PALETTES[8] + (
    (1,.85,.02,1),(.02,.73,.83,1),(.58,.6,.64,1),(.2,.08,.47,1),
    (.46,.22,.1,1),(.94,.63,.46,1),(.49,.78,.97,1),(.86,.55,.95,1),
    (.02,.35,.27,1),(.72,.08,.28,1),(.49,.49,.05,1),(.16,.31,.51,1))
DEFAULT_PALETTES[12] = DEFAULT_PALETTES[20][:12]
DEFAULT_PALETTES[32] = DEFAULT_PALETTES[20] + (
    (.95,.74,.85,1),(.31,.71,.46,1),(.91,.72,.38,1),(.46,.45,.8,1),
    (.72,.92,.8,1),(.55,.33,.42,1),(.81,.39,.12,1),(.26,.69,.71,1),
    (.92,.91,.63,1),(.55,.7,.21,1),(.65,.68,.84,1),(.87,.66,.97,1))


@dataclass(frozen=True)
class Surface:
    index: int
    face: int
    polygon: tuple
    patches: tuple
    cell: object = None


def _matrix(right, up, normal):
    return Mat4((right[0],up[0],normal[0],0, right[1],up[1],normal[1],0,
                 right[2],up[2],normal[2],0, 0,0,0,1))


def inside(points, polygon):
    p, poly = np.asarray(points), np.asarray(polygon)
    hit = np.zeros(len(p), dtype=bool)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        cross_y = (a[1] > p[:,1]) != (b[1] > p[:,1])
        if abs(b[1]-a[1]) > 1e-12:
            hit ^= cross_y & (p[:,0] < (b[0]-a[0])*(p[:,1]-a[1])/(b[1]-a[1])+a[0])
    return hit


def project_controls(canonical, controls, points):
    """三角面用仿射映射，多边形用透视映射；框线与取色共用。"""
    src, dst, points = np.asarray(canonical), np.asarray(controls), np.asarray(points)
    if src.shape != dst.shape or src.ndim!=2 or src.shape[1]!=2 or len(src)<3:
        raise ValueError('invalid corners')
    edge = np.roll(dst,-1,axis=0)-dst
    turn = edge[:,0]*np.roll(edge[:,1],-1)-edge[:,1]*np.roll(edge[:,0],-1)
    if not np.isfinite(dst).all() or not np.all(turn > 1e-10):
        raise ValueError('invalid corners')
    if len(src)==3:
        transform = np.linalg.solve(np.column_stack((src,np.ones(3))),dst)
        return np.column_stack((points,np.ones(len(points)))) @ transform
    if len(src)==4:
        x,y = imageops.project_quad(dst,points[:,0],points[:,1])
        return np.column_stack((x,y))
    rows,values=[],[]
    for (u,v),(x,y) in zip(src,dst):
        rows.extend(((u,v,1,0,0,0,-x*u,-x*v),(0,0,0,u,v,1,-y*u,-y*v)))
        values.extend((x,y))
    solution,_,rank,_=np.linalg.lstsq(rows,values,rcond=None)
    if rank<8:raise ValueError('invalid corners')
    matrix=np.append(solution,1).reshape(3,3)
    mapped=np.column_stack((points,np.ones(len(points))))@matrix.T
    if np.any(abs(mapped[:,2])<1e-8):raise ValueError('invalid corners')
    return mapped[:,:2]/mapped[:,2,None]


class SurfaceOrientation:
    """Use the entry screen's adjacent-face walk and hinge rotations."""
    def __init__(self, profile):
        from renderer.polyhedral_orientation import PolyhedralOrientation
        self.profile=profile
        roll=180 if profile.kind in ('pyraminx','moyu','void_tower') and profile.normals[0][1]>0 else 0
        self._navigation=PolyhedralOrientation(profile.spec,roll)
        self.world=self._navigation.world
        self.index=self._navigation.sequence[0]

    def current_face(self): return self.profile.face_keys[self.index]
    def _target(self,direction):
        nav=self._navigation
        return self.profile.face_keys[nav.sequence[(nav.index+direction)%len(nav.sequence)]]
    def next_face(self): return self._target(1)
    def prev_face(self): return self._target(-1)
    def _delta(self,direction):
        _,angle,axis=self._navigation.transition(direction)
        return angle,axis
    def next_axis_deg(self): return self._delta(1)
    def prev_axis_deg(self): return self._delta(-1)
    def next_dir(self): return 'up'
    def prev_dir(self): return 'down'
    def _turn(self,direction):
        self.index=self._navigation.commit(*self._navigation.transition(direction))
        self.world=self._navigation.world
        return self.current_face()
    def turn_next(self): return self._turn(1)
    def turn_prev(self): return self._turn(-1)


class ScanProfile:
    def __init__(self, kind, n, palette=None):
        if n not in SUPPORTED.get(kind, ()) or n>5:
            raise ValueError('Unsupported photo scan')
        self.kind,self.n=kind,n
        if kind=='pandora':
            from cube.shape_cube import PandoraCube,pandora_faces
            from cube.coordinates import rc_from_pos
            self.normals=CUBE
            from cube.polyhedral import body
            self.body=body(CUBE)
            surfaces=[]
            for home in PandoraCube.solved().positions:
                for polygon,color in pandora_faces(home):
                    if color < 0: continue
                    face=next(f for f,v in FACE_NORMALS.items() if tuple(v)==CUBE[color])
                    r,c=rc_from_pos(3,face,home)
                    surfaces.append(Surface(len(surfaces),color,polygon,(polygon,),(face,r,c)))
            self.surfaces=tuple(surfaces)
        else:
            g=geometry(kind,n)
            self.spec=g.spec
            self.normals=g.spec.normals
            self.body=body_faces(g.spec)
            self.surfaces=tuple(Surface(i,s.face,s.polygon,s.patches or (s.polygon,)) for i,s in enumerate(g.stickers))
        self.cubic=len(self.normals)==6 and tuple(self.normals)==CUBE
        self.face_keys=tuple(next(f for f,v in FACE_NORMALS.items() if tuple(v)==normal) for normal in self.normals) if self.cubic else tuple(str(i+1) for i in range(len(self.normals)))
        default=DINO4_SCAN_PALETTE if kind=='dino4' else DEFAULT_PALETTES[len(self.normals)]
        self.palette=tuple(tuple(c) for c in (palette or default))
        self._templates={}

    def new_orientation(self):
        return CubeOrientation(self.n) if self.cubic else SurfaceOrientation(self)

    def face_world(self,face):
        index=self.face_keys.index(face)
        normal=self.normals[index]
        centre=mean(self.body[index])
        tip=max(self.body[index],key=lambda p:(round(p[1],6),round(p[2],6),round(p[0],6)))
        up=unit(tuple(a-b for a,b in zip(tip,centre)))
        right=unit(cross(up,normal))
        return _matrix(right,up,normal)

    def face_aspect(self,face,world):
        xy=np.array([world.transform(*p)[:2] for p in self.body[self.face_keys.index(face)]])
        extent=np.ptp(xy,axis=0)
        return float(extent[1]/max(extent[0],1e-9))

    def templates(self, face, world):
        cache_key=(face,tuple(round(v,6) for v in world.m))
        if cache_key in self._templates: return self._templates[cache_key]
        fi=self.face_keys.index(face)
        border=np.array([world.transform(*p)[:2] for p in self.body[fi]])
        lo,hi=border.min(axis=0),border.max(axis=0)
        def uv(points):
            xy=np.array([world.transform(*p)[:2] for p in points])
            q=(xy-lo)/np.maximum(hi-lo,1e-9)
            q[:,1]=1-q[:,1]
            return q
        outline=uv(self.body[fi])
        if len(outline)==4:
            controls=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
        else:
            outline=outline[np.argsort(np.arctan2(outline[:,1]-.5,outline[:,0]-.5))]
            controls=np.roll(outline,-np.argmin(outline[:,1]),axis=0)
        result=[]
        for surface in self.surfaces:
            if surface.face!=fi: continue
            polygon=uv(surface.polygon)
            patches=tuple(uv(patch) for patch in surface.patches)
            result.append((surface.index,polygon,patches,_interior(polygon,patches)))
        self._templates[cache_key]=(controls,result)
        return controls,result

    def blank(self):
        return {f:{s.index:-1 for s in self.surfaces if s.face==i} for i,f in enumerate(self.face_keys)}

    def from_cube(self,cube,recorded=None):
        data=self.blank()
        if self.kind!='pandora':
            for s in self.surfaces:data[self.face_keys[s.face]][s.index]=int(cube.colors[s.index])
        elif recorded:
            from cube.shape_cube import pandora_faces
            from cube.mastermorphix import transform
            from cube.coordinates import rc_from_pos
            by_cell={s.cell:s.index for s in self.surfaces}
            for pos in recorded:
                piece=cube.cubies[pos]
                for _,color in pandora_faces(piece.home):
                    if color<0:continue
                    normal=transform(piece.frame,CUBE[color])
                    face=next(f for f,v in FACE_NORMALS.items() if tuple(v)==normal)
                    r,c=rc_from_pos(3,face,pos)
                    key=cube.palette[color]
                    value=int(key.rsplit('_',1)[1]) if str(key).startswith('S_pandora_') else CUBE_CODES.index(key)
                    data[face][by_cell[(face,r,c)]]=value
        return data

    def complete(self, data, face):
        values=data.get(face,{})
        return (len(values)==sum(s.face==self.face_keys.index(face) for s in self.surfaces)
                and all(0<=v<len(self.palette) for v in values.values()))

    def apply(self,data,cube):
        if self.kind!='pandora':
            colors=[data.get(self.face_keys[s.face],{}).get(s.index,-1) for s in self.surfaces]
            if any(v < -1 or v >= len(self.palette) for v in colors):raise ValueError('camera.invalid_input')
            result=cube.clone()
            result.colors=colors
            return result
        if not all(self.complete(data,f) for f in self.face_keys):
            raise ValueError('camera.complete_first')
        from vision.assemble import empty_grid
        facelets={f:empty_grid(3) for f in FACE_NORMALS}
        for s in self.surfaces:
            f,r,c=s.cell
            facelets[f][r][c]=CUBE_CODES[data[f][s.index]]
        # Centres define the holding orientation. Build virtual face colors
        # relative to them, and carry the physical palette in the same order.
        centres=[facelets[f][1][1] for f in self.face_keys]
        if len(set(centres))!=6:raise ValueError('camera.invalid_input')
        reference=dict(zip(centres,CUBE_CODES))
        facelets={f:[[reference[c] for c in row] for row in grid] for f,grid in facelets.items()}
        from solver.solver3 import verify_3x3
        if not verify_3x3(facelets)[0]:raise ValueError('camera.invalid_input')
        from cube.conversion import facelets_to_cubies
        from cube.cube3 import Cube3
        from cube.mastermorphix import make_piece,placements
        from cube.shape_cube import PandoraCube
        homes=Cube3.solved().cubies
        pieces={}
        for pos,entered in facelets_to_cubies(facelets,3).items():
            options=[home for home,p in homes.items() if set(p.stickers.values())==set(entered.stickers.values())]
            for home in options:
                for frame in placements(home,pos):
                    candidate=make_piece(home,pos,frame,3)
                    if candidate.stickers==entered.stickers:
                        pieces[pos]=candidate
                        break
                if pos in pieces:break
            if pos not in pieces:raise ValueError('camera.invalid_input')
        base_palette=(tuple(f'S_pandora_{i}' for i in range(6)) if any(str(c).startswith('S_pandora_') for c in cube.palette)
                      else CUBE_CODES)
        palette=tuple(base_palette[CUBE_CODES.index(c)] for c in centres)
        return PandoraCube(pieces,palette=palette)


def _interior(polygon,patches):
    lo,hi=polygon.min(axis=0),polygon.max(axis=0)
    x,y=np.meshgrid(np.linspace(lo[0],hi[0],19),np.linspace(lo[1],hi[1],19))
    points=np.column_stack((x.flat,y.flat))
    keep=np.zeros(len(points),dtype=bool)
    for patch in patches:keep |= inside(points,patch)
    points=points[keep]
    if not len(points):return np.array([polygon.mean(axis=0)])
    distance=np.full(len(points),np.inf)
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        edge=b-a
        t=np.clip(((points-a)@edge)/max(edge@edge,1e-12),0,1)
        distance=np.minimum(distance,np.linalg.norm(points-a-t[:,None]*edge,axis=1))
    points=points[distance>=max(distance.max()*.45,1e-8)]
    return points[::max(1,len(points)//60)]


def _read_color(rgb,palette):
    h,s,v=rgb_to_hsv(np.asarray(rgb).reshape(-1,1,3))
    refs=rgb_to_hsv(np.array(palette)[:,:3].reshape(-1,1,3))
    h,s,v=h.ravel(),s.ravel(),v.ravel()
    rh,rs,rv=(a.ravel() for a in refs)
    dh=np.abs(h[:,None]-rh[None,:]);dh=np.minimum(dh,180-dh)/90
    distances=4*dh**2+.15*((s[:,None]-rs[None,:])/255)**2+.10*((v[:,None]-rv[None,:])/255)**2
    # Pastel stickers in 20/32-colour puzzles still carry useful hue. Only
    # genuinely neutral references should lose their hue distance.
    white=rs<=25
    if np.any(white):
        distances[:,white]=.6*((s[:,None]-rs[None,white])/255)**2+((v[:,None]-rv[None,white])/255)**2
    distances[:,~white]+=np.where(s[:,None]<np.maximum(20,rs[None,~white]*.45),2.,0.)
    distances[:,white]+=np.where(s[:,None]>np.maximum(35,rs[None,white]+20),2.,0.)
    ranked=np.sort(distances,axis=1)
    nearest=np.argmin(distances,axis=1)
    neutral=white[nearest]&(v>=np.maximum(60,rv[nearest]*.7))
    chromatic=s>=np.maximum(30,rs[nearest]*.65)
    # Dense palettes contain close shades. A near-exact calibrated match is
    # usable when its error is much smaller than the runner-up's, even if
    # their absolute gap is small. Equal/ambiguous matches still get rejected.
    separated=((ranked[:,1]-ranked[:,0])>.004)|((ranked[:,0]<.01)&(ranked[:,0]<ranked[:,1]*.35))
    valid=(v>=60)&(chromatic|neutral)&(ranked[:,0]<.5)&separated
    votes=nearest[valid]
    if len(votes)<max(1,len(rgb)*.45):return -1
    counts=np.bincount(votes,minlength=len(palette))
    return int(np.argmax(counts)) if counts.max()/len(votes)>=.72 else -1


@dataclass
class SurfaceDetection:
    values: dict
    image_quad: object
    ok: bool
    samples: object = None


def _read_surface(image,profile,face,world,controls):
    canonical,templates=profile.templates(face,world)
    lengths=[len(samples) for _,_,_,samples in templates]
    xy=project_controls(canonical,controls,np.concatenate([samples for _,_,_,samples in templates]))
    rgb=imageops.sample_points(image,xy[:,0],xy[:,1])
    values={}
    samples={}
    start=0
    for (index,_,_,_),length in zip(templates,lengths):
        values[index]=_read_color(rgb[start:start+length],profile.palette)
        samples[index]=np.clip(np.rint(rgb[start:start+length]),0,255).astype(np.uint8)
        start+=length
    return SurfaceDetection(values,np.asarray(controls).tolist(),all(v>=0 for v in values.values()),samples)


def _boundary_score(image,profile,face,world,controls):
    canonical,templates=profile.templates(face,world)
    probes=[]
    for _,polygon,_,_ in templates:
        for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
            edge=b-a;length=np.linalg.norm(edge)
            if length<.025:continue
            normal=np.array([-edge[1],edge[0]])/length*.012
            mid=(a+b)/2
            if not inside(np.array([mid-normal*3,mid+normal*3]),canonical).all():continue
            probes.extend((mid-normal,mid,mid+normal))
    if not probes:return 0.
    xy=project_controls(canonical,controls,np.asarray(probes))
    rgb=imageops.sample_points(image,xy[:,0],xy[:,1]).reshape(-1,3,3)
    jump=np.linalg.norm(rgb[:,0]-rgb[:,2],axis=1)
    dark=(rgb[:,0].max(axis=1)+rgb[:,2].max(axis=1))/2-rgb[:,1].max(axis=1)
    return float(np.mean((jump>40)|(dark>22)))


def detect_surface(image,profile,face,world,controls=None,progress=None):
    image=imageops.as_uint8_rgb(image)
    canonical,templates=profile.templates(face,world)
    blank={index:-1 for index,_,_,_ in templates}
    if controls is not None:
        try:
            controls=np.asarray(controls,float)
            if np.any(controls<0) or np.any(controls[:,0]>image.shape[1]-1) or np.any(controls[:,1]>image.shape[0]-1):raise ValueError()
            if progress: progress("camera.reading",0,1)
            result=_read_surface(image,profile,face,world,controls)
            if progress: progress("camera.reading",1,1)
            return result
        except (ValueError,np.linalg.LinAlgError):return SurfaceDetection(blank,None,False)
    from vision.detect import _foreground_mask
    from vision.params import DEFAULT
    work,_=imageops.fit_max_dim(image,420)
    mask=_foreground_mask(*rgb_to_hsv(work),DEFAULT)
    clean=imageops.erode(mask,1)
    scale=np.array([(image.shape[1]-1)/max(work.shape[1]-1,1),(image.shape[0]-1)/max(work.shape[0]-1,1)])
    seen=set();best=None
    expanded, previous_radius = clean, 0
    for pass_index,radius in enumerate((2,5,9,15,22)):
        if progress: progress("camera.locating",pass_index,5)
        expanded = imageops.dilate(expanded, radius-previous_radius)
        previous_radius = radius
        candidates=[]
        for component in imageops.component_masks(expanded,limit=5):
            ys,xs=np.nonzero(component&mask)
            if len(xs)<100:continue
            signature=(int(xs.min()),int(xs.max()),int(ys.min()),int(ys.max()),len(xs))
            if signature in seen:continue
            seen.add(signature)
            hull=imageops.convex_hull(imageops.row_extrema_points(xs,ys))
            while len(hull)>len(canonical):
                a=np.roll(hull,1,axis=0)-hull;b=np.roll(hull,-1,axis=0)-hull
                hull=np.delete(hull,np.argmin(abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])),axis=0)
            if len(hull)!=len(canonical):continue
            if len(hull)==4:
                rect=imageops.min_area_rect(hull)
                w,h=rect['size']
                if min(w,h)<24 or abs(w-h)/max(w,h)>.3:continue
                start=np.argmin(np.sum(hull,axis=1))
            else:
                start=np.argmin(hull[:,1])
            hull=np.roll(hull,-start,axis=0)
            area=abs(np.sum(hull[:,0]*np.roll(hull[:,1],-1)-hull[:,1]*np.roll(hull[:,0],-1)))/2
            if area<400 or len(xs)/max(area,1)<.4:continue
            try:
                boundary=_boundary_score(work,profile,face,world,hull)
                if boundary<.12:continue
                found=_read_surface(image,profile,face,world,hull*scale)
            except (ValueError,np.linalg.LinAlgError):continue
            known=sum(v>=0 for v in found.values.values())/len(found.values)
            candidates.append((known,area,found))
        if candidates:
            candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
            candidate=candidates[0]
            if candidate[0]==1:return candidate[2]
            if best is None or candidate[0]>best[0]:best=candidate
    return best[2] if best else SurfaceDetection(blank,None,False)
