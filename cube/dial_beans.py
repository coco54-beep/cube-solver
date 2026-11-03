"""Numbered Time Machine and double-sided three/five-petal bead spinners.

All slots are physical pieces. Decorative hubs never become input cells.
Time Machine has a 2x2 corner core plus six independent twelve-part rings.
Bean loops contain five beads in a reversible outer wing, three in the
independent central rotors and two fixed transition slots on each side.
"""
from functools import lru_cache
import math
from itertools import product

from cube.polyhedral import Spec,Sticker,CUBE,mean,dot,add,scale,cross
from cube.expanded_polyhedra import assemble

KINDS={'time_machine':2,'bean_6':6,'bean_10':10}
LOOP=10
INNER=(6,7,8)
FACES=('U','R','F','D','L','B')


def basis(face):
    from cube.coordinates import FACE_SPEC
    _,_,row,rs,col,cs=FACE_SPEC[FACES[face]]
    right=tuple(cs if a==col else 0 for a in range(3))
    up=tuple(-rs if a==row else 0 for a in range(3))
    return right,up


def face_point(face,x,y):
    right,up=basis(face)
    return tuple(CUBE[face][a]+x*right[a]+y*up[a] for a in range(3))


@lru_cache(maxsize=1)
def time_geometry():
    panels=[];pieces=[[] for _ in range(8)];centres=[]
    corners=list(product((-1,1),repeat=3))
    for face in range(6):
        for q in range(4):
            angles=[(q+j/4)*math.pi/2 for j in range(5)]
            poly=(face_point(face,0,0),)+tuple(face_point(face,.37*math.cos(t),.37*math.sin(t)) for t in angles)
            centre=mean(poly);home=tuple(1 if v>0 else -1 for v in centre)
            piece=corners.index(home);pieces[piece].append(len(panels))
            # The same corner face is exposed inside the dial and outside
            # its rim. Both surfaces have one colour and move as one piece.
            # Keep the small centre polygon as the state/permutation key so
            # existing entries and the corner solver retain their indices.
            outer=[]
            for j in range(12):
                a=(q+j/12)*math.pi/2;b=(q+(j+1)/12)*math.pi/2
                def point(angle,radius):
                    return face_point(face,radius*math.cos(angle),radius*math.sin(angle))
                ra=1/max(abs(math.cos(a)),abs(math.sin(a)))
                rb=1/max(abs(math.cos(b)),abs(math.sin(b)))
                outer.append((point(a,.965),point(a,ra),point(b,rb),point(b,.965)))
            panels.append(Sticker(piece,face,poly,(poly,)+tuple(outer)))
    for face in range(6):
        for number in range(12):
            start=math.radians(60-30*number)
            angles=[start+j*math.pi/36 for j in range(7)]
            poly=tuple(face_point(face,.45*math.cos(t),.45*math.sin(t)) for t in reversed(angles))+tuple(
                face_point(face,.94*math.cos(t),.94*math.sin(t)) for t in angles)
            p=len(pieces);pieces.append([len(panels)]);panels.append(Sticker(p,face,poly))
    pieces=tuple(tuple(v) for v in pieces)
    centres=tuple(mean(tuple(p for i in slots for p in panels[i].polygon)) for slots in pieces)
    selected=[(set(i for i,c in enumerate(centres) if dot(c,axis)>1e-7),) for axis in CUBE]
    selected.extend((set(range(8+face*12,8+(face+1)*12)),) for face in range(6))
    spec=Spec('time_machine',2,CUBE,CUBE+CUBE,(),12,axis_steps=(3,)*6+(1,)*6)
    return assemble(spec,panels,pieces,centres,selected)


def petals(kind):return 3 if kind=='bean_6' else 5


def bean_index(kind,side,petal,position):return (side*petals(kind)+petal)*LOOP+position


@lru_cache(maxsize=2)
def bean_geometry(kind):
    p=petals(kind);period=math.lcm(LOOP,2,p);panels=[];centres=[]
    radius=.82 if p==3 else 1.12;loop=.49 if p==3 else .43
    for side in range(2):
        for petal in range(p):
            phi=math.pi/2+2*math.pi*petal/p
            cx,cy=radius*math.cos(phi),radius*math.sin(phi)
            for pos in range(LOOP):
                theta=phi+(pos-2)*2*math.pi/LOOP
                centre=(cx+loop*math.cos(theta),cy+loop*math.sin(theta),.17 if side==0 else -.17)
                # A 30-gon closes exactly under 36/72/120/180-degree moves.
                poly=tuple((centre[0]+.105*math.cos(t*math.pi/15),centre[1]+.105*math.sin(t*math.pi/15),centre[2]) for t in range(30))
                i=len(panels);panels.append(Sticker(i,2 if side==0 else 5,poly));centres.append(centre)
    size=len(panels);permutations=[];layers=[];axes=[];steps=[]
    def keep(action,axis,step):
        assert sorted(action)==list(range(size))
        permutations.append((tuple(action),));layers.append((tuple(i for i,j in enumerate(action) if i!=j),))
        axes.append(axis);steps.append(step)
    for side in range(2):
        for petal in range(p):
            action=list(range(size))
            for pos in range(LOOP):action[bean_index(kind,side,petal,pos)]=bean_index(kind,side,petal,(pos+1)%LOOP)
            keep(action,(0.,0.,1.),period//LOOP)
    for petal in range(p):
        action=list(range(size));phi=math.pi/2+2*math.pi*petal/p
        for side in range(2):
            for pos in range(5):action[bean_index(kind,side,petal,pos)]=bean_index(kind,1-side,petal,4-pos)
        keep(action,(math.cos(phi),math.sin(phi),0.),period//2)
    for side in range(2):
        action=list(range(size))
        direction=1 if side==0 else -1
        for petal in range(p):
            for pos in INNER:action[bean_index(kind,side,petal,pos)]=bean_index(kind,side,(petal+direction)%p,pos)
        keep(action,(0.,0.,float(direction)),period//p)
    from cube.polyhedral import Geometry
    extent=radius+loop+.2
    spec=Spec(kind,KINDS[kind],CUBE,tuple(axes),(),period,axis_steps=tuple(steps),bounds=(extent,extent,.25,extent,extent,.25))
    return Geometry(spec,tuple(panels),tuple((i,) for i in range(size)),tuple(centres),tuple(permutations),tuple(layers))


def geometry(kind,n):
    if kind not in KINDS or n!=KINDS[kind]:raise ValueError('Unsupported dial or bean model')
    return time_geometry() if kind=='time_machine' else bean_geometry(kind)


def goal(kind):
    if kind=='time_machine':return tuple(72+face for face in range(6) for _ in range(4))+tuple(range(72))
    return tuple(color for color in range(KINDS[kind]) for _ in range(LOOP))


def beans_solved(kind,values):
    """Rings must be monochrome; their colour locations are unrestricted."""
    count=KINDS[kind]
    if len(values)!=count*LOOP:return False
    colors=[values[i] for i in range(0,len(values),LOOP)]
    return (set(colors)==set(range(count)) and
            all(all(v==color for v in values[i*LOOP:(i+1)*LOOP]) for i,color in enumerate(colors)))


def value_face(kind,value):return (value//12 if value<72 else value-72) if kind=='time_machine' else value


def move_origin(kind,move):
    if kind=='time_machine':return (0.,0.,0.)
    p=petals(kind)
    if move.axis<2*p:
        phi=math.pi/2+2*math.pi*(move.axis%p)/p;radius=.82 if p==3 else 1.12
        return radius*math.cos(phi),radius*math.sin(phi),0.
    return (0.,0.,0.)
