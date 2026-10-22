"""Mixup surface constraints, real centre/edge exchange and bounded scrambles."""
import math
import random
from functools import lru_cache
from time import monotonic
from dataclasses import dataclass
from cube.articulated import ArticulatedCube,frame_key,MIXUP_MODELS,poses,proper_poses,solids
from cube.appearance import ROTATIONS,transform_frame
from cube.polyhedral import Move,add,scale,dot,cross,unit,mean,clip

EPS=1e-7
PROPER=frozenset(frame_key(f) for f in ROTATIONS)


@dataclass(frozen=True)
class MixupSliceMove(Move):
    """One simultaneous turn of adjacent layers, with only two cut planes."""
    layers:tuple=()

    def inverse(self,order):
        return MixupSliceMove(self.axis,self.layer,(-self.amount)%order,self.layers)

class MixupCube(ArticulatedCube):
    """Original physical pieces retain their own panels and rigid poses.

    No fixed-slot repainting or fallback colour is used when a centre enters
    an edge location. Renderer closing cuboids are not the real mechanism.
    """
    def __init__(self,kind='mixup_333',frames=None,history=(),pieces=None):
        if kind not in MIXUP_MODELS:raise ValueError('Unsupported Mixup model')
        super().__init__(kind,frames,history)
        if pieces is not None and tuple(pieces)!=self.solids:raise ValueError('mixup.legacy_entry')
    @property
    def pieces(self):return self.solids
    def reset(self):self.colors=(0,)*len(self.solids)
    def proposed(self,move,collisions=True,guard=None):
        layers=getattr(move,'layers',())
        if not layers:return super().proposed(move,collisions,guard)
        if guard:guard()
        if type(move.axis) is not int or not 0<=move.axis<3:raise ValueError('rigid.blocked')
        count=len(self.geometry.layers[move.axis]);layers=tuple(layers)
        if (not layers or any(type(l) is not int for l in layers) or layers!=tuple(range(layers[0],layers[-1]+1))
                or layers[0]<0 or layers[-1]>=count or move.layer!=layers[0]):raise ValueError('rigid.blocked')
        if (0 in layers or count-1 in layers) and move.amount%2:raise ValueError('rigid.blocked')
        selected={h for l in layers for h in self.geometry.layers[move.axis][l]}
        if not selected:raise ValueError('rigid.blocked')
        check_slice_clearance(self,move,selected,guard)
        from cube.articulated import turn_frame,multiply
        turn=turn_frame(self.geometry.spec.axes[move.axis],math.tau*move.amount/8)
        frames=list(self.frames)
        for home in selected:
            pose=self._pose_index.get(frame_key(multiply(turn,self.orientations[frames[home]])))
            if pose is None or not self.pose_allowed(home,pose):raise ValueError('rigid.blocked')
            frames[home]=pose
        return tuple(frames)

def _normal(poly):return unit(cross(add(poly[1],scale(poly[0],-1)),add(poly[2],scale(poly[0],-1))))
def _area(poly):
    if len(poly)<3:return 0.
    total=(0.,0.,0.)
    for p,q in zip(poly,poly[1:]+poly[:1]):total=add(total,cross(p,q))
    return math.sqrt(dot(total,total))/2

@lru_cache(maxsize=8)
def _panel_vertices(kind):
    return tuple(tuple(dict.fromkeys(p for points,color in solid.faces if color>=0 for p in points))
                 for solid in solids(kind))


@lru_cache(maxsize=8192)
def _panel_bounds(kind,home,pose):
    """Exact axial extents of the original coloured panels, with bounded RAM."""
    frame=poses('mixup')[pose]
    points=tuple(transform_frame(frame,p) for p in _panel_vertices(kind)[home])
    return tuple((min(p[a] for p in points),max(p[a] for p in points)) for a in range(3))


def check_slice_clearance(cube,move,selected,guard=None):
    """Require the chosen slab to separate whole pieces before rotation.

    A centroid nominates a piece but cannot establish a clear cut. Tilted
    pieces and unsplit 334/344 pieces can bridge the two inner layers. Check
    original coloured panels, not artificial black display closures.
    Rotation preserves the axial coordinate, so this separation holds
    throughout a turn, including half turns with plausible end poses.
    """
    _,cuts=cube._bands();bounds=cuts[move.axis]
    layers=getattr(move,'layers',()) or (move.layer,)
    lower=bounds[min(layers)-1] if min(layers) else -math.inf
    upper=bounds[max(layers)] if max(layers)<len(bounds) else math.inf
    for home in range(len(cube.solids)):
        if guard:guard()
        # Mixup axes are x/y/z. Reuse the exact vertex extents across rejected
        # moves and clones; all original slab boundaries are still checked.
        lo,hi=_panel_bounds(cube.puzzle_kind,home,cube.frames[home])[move.axis]
        if any(lo<b-EPS and hi>b+EPS for b in (lower,upper)):
            raise ValueError('rigid.blocked')
        if home in selected:
            if lo<lower-EPS or hi>upper+EPS:raise ValueError('rigid.blocked')
        elif lo<upper-EPS and hi>lower+EPS:
            # A display anchor must never leave a piece inside a moving slab.
            raise ValueError('rigid.blocked')


def skins_cross(left,right):
    """Reject intersecting visible panels, allowing contact at shared edges.

    Artificial black closing faces of a display cuboid must not prevent a
    legal 45-degree centre/edge exchange in the bevelled real mechanism.
    """
    for a,ca in left:
        if ca<0:continue
        na=_normal(a)
        for b,cb in right:
            if cb<0:continue
            if any(max(p[i] for p in a)<min(p[i] for p in b)-EPS or max(p[i] for p in b)<min(p[i] for p in a)-EPS for i in range(3)):continue
            nb=_normal(b)
            if abs(dot(na,nb))>1-EPS:
                if abs(dot(na,add(a[0],scale(b[0],-1))))>EPS:continue
                part=a;centre=mean(b)
                for p,q in zip(b,b[1:]+b[:1]):
                    n=cross(add(q,scale(p,-1)),nb)
                    if dot(n,add(centre,scale(p,-1)))>0:n=scale(n,-1)
                    part=clip(part,n,dot(n,p))
                    if not part:break
                if _area(part)>1e-8:return True
            else:
                for source,target,n in ((a,b,nb),(b,a,na)):
                    centre=mean(target)
                    for p,q in zip(source,source[1:]+source[:1]):
                        dp=dot(n,add(p,scale(target[0],-1)));dq=dot(n,add(q,scale(target[0],-1)))
                        if dp*dq>=-EPS*EPS:continue
                        hit=add(p,scale(add(q,scale(p,-1)),dp/(dp-dq)))
                        inside=True
                        for u,v in zip(target,target[1:]+target[:1]):
                            edge_n=cross(add(v,scale(u,-1)),n)
                            if dot(edge_n,add(centre,scale(u,-1)))>0:edge_n=scale(edge_n,-1)
                            if dot(edge_n,add(hit,scale(u,-1)))>=-EPS:inside=False;break
                        if inside:return True
    return False

def exchange_counts(cube):
    """Original centres along edge diagonals, original edges along face axes."""
    centres=edges=0
    for solid,pose in zip(cube.solids,cube.frames):
        p=transform_frame(cube.orientations[pose],solid.anchor)
        a=sorted((abs(v) for v in p),reverse=True)
        if solid.role=='centre' and a[1]>.3 and abs(a[0]-a[1])<1e-6 and a[2]<1e-6:centres+=1
        if solid.role=='edge' and a[1]<1e-6 and a[0]>.7:edges+=1
    return centres,edges

def _has_centre_edge_exchange(cube):
    centres,edges=exchange_counts(cube)
    return centres>0 and edges>0

def _scramble_quality(cube):
    """Visual diversity heuristic, not a uniform random-state sampler."""
    proper=proper_poses('mixup')
    tilted=[p for p in cube.frames if p not in proper]
    displaced=sum(sum((a-b)**2 for a,b in zip(
        transform_frame(cube.orientations[p],solid.anchor),solid.anchor))>.01
        for solid,p in zip(cube.solids,cube.frames))
    return len(tilted),len(set(tilted)),displaced


class _ScrambleDeadline(TimeoutError):
    """A search budget is different from an illegal physical move."""


def _seed_mixup(work,guard,remember):
    """Keep a legal mixed state before exploring cross-axis continuations."""
    kind=work.puzzle_kind
    choices=[(a,l) for a,bands in enumerate(work.geometry.layers) for l in range(1,len(bands)-1)]
    choices=[(a,l,p) for a,l in choices for p in (1,7)]
    random.shuffle(choices)
    # Prefer a complete middle layer in 334/344, while randomizing equivalent
    # choices. Split layers have more opportunities to be blocked.
    dimensions,_=MIXUP_MODELS[kind]
    choices.sort(key=lambda choice:dimensions[choice[0]]==4)
    fallback=None
    for axis,layer,amount in choices:
        guard();candidate=work.clone()
        try:candidate.apply_move(Move(axis,layer,amount),guard=guard)
        except ValueError:continue
        if remember(candidate):fallback=candidate
        faces=[Move(a,l,p) for a,bands in enumerate(candidate.geometry.layers) if a!=axis for l in (0,len(bands)-1) for p in (2,6)]
        random.shuffle(faces)
        for move in faces:
            guard();trial=candidate.clone()
            try:trial.apply_move(move,guard=guard)
            except ValueError:continue
            if not remember(trial):continue
            return trial
    return fallback


def scramble_mixup(kind='mixup_333',cancelled=None,seconds=6.):
    work=MixupCube(kind);started=monotonic();deadline=started+max(0.,seconds)
    best=None;quality=None
    def guard():
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()>deadline:raise _ScrambleDeadline()
    def remember(candidate):
        nonlocal best,quality
        if candidate is None:return False
        score=_scramble_quality(candidate)
        if not score[0] or (kind in ('mixup_333','mixup_plus_333') and not _has_centre_edge_exchange(candidate)):return False
        # Prefer a deeper colour scramble when geometric quality ties.
        score=score+(min(len(candidate.history),96),)
        if quality is None or score>quality:
            best=candidate.clone();quality=score
        return True
    try:
        # Establish a genuine mixed fallback BEFORE spending the budget on
        # colour depth. Later timeouts must never discard this valid state.
        seed=_seed_mixup(work,guard,remember)
        if best is None:raise ValueError('rigid.no_scramble')
        dimensions,plus=MIXUP_MODELS[kind];previous=None
        base_target=32+8*dimensions.count(4)+(8 if plus else 0)
        base_deadline=started+max(0.,seconds)*.35
        for _ in range(base_target):
            if monotonic()>base_deadline:break
            guard()
            choices=[(a,l) for a,bands in enumerate(work.geometry.layers)
                     if a!=previous for l in range(len(bands))]
            random.shuffle(choices)
            if random.random()<.6:
                choices.sort(key=lambda al:al[1] in (0,len(work.geometry.layers[al[0]])-1))
            for axis,layer in choices:
                try:work.apply_move(Move(axis,layer,random.choice((2,4,6))),guard=guard)
                except ValueError:continue
                previous=axis;break
            else:break
        # Keep the ordinary-colour prefix for the later 3x3/4x4 solve stage
        # whenever time and physical cuts allow a new mixed starting state.
        mixed=_seed_mixup(work,guard,remember) if work.history else seed
        if mixed is None:mixed=best.clone()
        remember(mixed)
        previous=(mixed.history[-1].axis,mixed.history[-1].layer)
        seen={mixed.frames};shape_target=40+8*dimensions.count(4)+(8 if plus else 0)
        for _ in range(shape_target):
            guard()
            atoms=[Move(base.axis,base.layer,amount) for base in mixed.moves()
                   for amount in ((1,2,3,5,6,7) if base.amount==1 else (2,4,6))]
            random.shuffle(atoms);atoms.sort(key=lambda m:m.axis==previous[0])
            for move in atoms:
                if (move.axis,move.layer)==previous:continue
                trial=mixed.clone()
                try:trial.apply_move(move,guard=guard)
                except ValueError:continue
                if trial.frames in seen:continue
                mixed=trial;seen.add(mixed.frames);previous=(move.axis,move.layer)
                remember(mixed);break
            else:break
    except _ScrambleDeadline:
        if best is None:raise ValueError('rigid.no_scramble') from None
    if cancelled and cancelled():raise InterruptedError()
    best.scramble_limited=len(best.history)<20
    return best

