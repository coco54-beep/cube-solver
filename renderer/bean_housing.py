"""Rounded, double-sided shell for the three/five-petal bead mechanisms.

Housing faces carry a material and a mechanical owner, never an input slot.
Owner -1 is fixed, -2/-3 follow front/back rotors, and 0..p-1 are wing halves.
All decorative surfaces are cached; bead state remains in cube.dial_beans.
"""
import math
from functools import lru_cache

from cube.polyhedral import cross, unit, mean

SHELL=(.30,.66,.83,1.)
EDGE=(.20,.51,.70,1.)
HIGHLIGHT=(.43,.75,.89,1.)
TRACK=(.075,.17,.22,1.)
RECESS=(.20,.49,.65,1.)
SEGMENTS=60  # Closes under both 120/72-degree rotors and all wing reflections.


def dimensions(kind):
    from cube.dial_beans import petals
    p=petals(kind)
    return p, .82 if p==3 else 1.12, .49 if p==3 else .43, .735 if p==3 else .675


def radius(kind):
    _,r,_,outer=dimensions(kind)
    return math.hypot(r+outer,.22)


def owner_moves(kind,owner,axis):
    from cube.dial_beans import petals
    p=petals(kind)
    return (owner==-2 and axis==3*p) or (owner==-3 and axis==3*p+1) or (0<=owner<p and axis==2*p+owner)


@lru_cache(maxsize=2)
def housing(kind):
    p,rad,loop,outer=dimensions(kind);result=[]

    def emit(points,normals,color,owner):
        if owner!=-2:
            result.append((tuple(points),tuple(normals),color,owner));return
        def clip(records,side,threshold):
            out=[]
            for (a,na),(b,nb) in zip(records,records[1:]+records[:1]):
                inside=side*a[2]>=threshold;other=side*b[2]>=threshold
                if inside:out.append((a,na))
                if inside!=other:
                    t=(side*threshold-a[2])/(b[2]-a[2])
                    point=tuple(x+t*(y-x) for x,y in zip(a,b))
                    normal=unit(tuple(x+t*(y-x) for x,y in zip(na,nb)))
                    out.append((point,normal))
            return out
        records=list(zip(points,normals))
        for side,role in ((1,-2),(-1,-3)):
            half=clip(records,side,.006)
            if len(half)>=3:
                result.append((tuple(p for p,n in half),tuple(n for p,n in half),color,role))
        # A narrow fixed bearing separates the two independent half-shells.
        middle=clip(clip(records,1,-.004),-1,-.004)
        if len(middle)>=3:
            result.append((tuple(p for p,n in middle),tuple(n for p,n in middle),TRACK,-1))

    def flat(points,color,owner,normal=None):
        if normal is None:
            normal=unit(cross(tuple(b-a for a,b in zip(points[0],points[1])),
                              tuple(b-a for a,b in zip(points[0],points[2]))))
        emit(points,[normal]*len(points),color,owner)

    def ring(cx,cy,phi,profile,color,owners):
        # A swept cross section provides rounded lips and real sidewalls.
        directions=[unit((-(z1-z0),r1-r0,0)) for (r0,z0),(r1,z1) in zip(profile,profile[1:])]
        smooth=[unit(tuple(a+b for a,b in zip(directions[j-1],directions[j])))
                for j in range(len(directions))]
        for i in range(SEGMENTS):
            a=phi+math.tau*i/SEGMENTS;b=phi+math.tau*(i+1)/SEGMENTS
            owner=owners(i)
            for j,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
                def vertex(r,z,t):return cx+r*math.cos(t),cy+r*math.sin(t),z
                points=(vertex(r0,z0,a),vertex(r1,z1,a),vertex(r1,z1,b),vertex(r0,z0,b))
                normals=[(smooth[k][0]*math.cos(t),smooth[k][0]*math.sin(t),smooth[k][1])
                         for k,t in ((j,a),((j+1)%len(smooth),a),((j+1)%len(smooth),b),(j,b))]
                emit(points,normals,EDGE if j in (3,7) else color,owner)
        for degree in (90,126,234,270):
            i=degree*SEGMENTS//360
            t=phi+math.tau*i/SEGMENTS
            for segment,sign in (((i-1)%SEGMENTS,1),(i,-1)):
                owner=owners(segment);normal=(-sign*math.sin(t),sign*math.cos(t),0)
                centre=mean(tuple((cx+r*math.cos(t),cy+r*math.sin(t),z) for r,z in profile[:-1]))
                for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
                    flat((centre,(cx+r0*math.cos(t),cy+r0*math.sin(t),z0),
                          (cx+r1*math.cos(t),cy+r1*math.sin(t),z1)),EDGE,owner,normal)

    def cap(cx,cy,r,z,side,color,owners):
        profile=((r*.88,side*(z+.016)),(r*.98,side*z),(r,side*(z-.022)))
        # Front and back are independent visible surfaces of one solid knob.
        for i in range(SEGMENTS//2):
            a=math.tau*2*i/SEGMENTS;b=math.tau*2*(i+1)/SEGMENTS;owner=owners(2*i)
            flat(((cx,cy,side*(z+.016)),
                  (cx+profile[0][0]*math.cos(a),cy+profile[0][0]*math.sin(a),profile[0][1]),
                  (cx+profile[0][0]*math.cos(b),cy+profile[0][0]*math.sin(b),profile[0][1])),color,owner,(0,0,side))
            for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
                points=((cx+r0*math.cos(a),cy+r0*math.sin(a),z0),
                        (cx+r1*math.cos(a),cy+r1*math.sin(a),z1),
                        (cx+r1*math.cos(b),cy+r1*math.sin(b),z1),
                        (cx+r0*math.cos(b),cy+r0*math.sin(b),z0))
                normals=[unit((.65*math.cos(t),.65*math.sin(t),side*.76)) for t in (a,a,b,b)]
                emit(points,normals,color,owner)

    def part(i,petal):
        angle=(i+.5)*360/SEGMENTS
        return petal if angle<90 or angle>270 else -2 if 126<angle<234 else -1

    outline=[]
    for petal in range(p):
        phi=math.pi/2+math.tau*petal/p;cx,cy=rad*math.cos(phi),rad*math.sin(phi)
        # The inner-facing arcs form a scalloped central web and keep the
        # bead tracks open rather than covering them with a solid plate.
        for k in range(7):
            t=phi+math.radians(234-18*k)
            outline.append((cx+(loop+.135)*math.cos(t),cy+(loop+.135)*math.sin(t)))
        profile=((loop+.112,.075),(loop+.135,.185),(outer-.050,.185),(outer,.085),
                 (outer,-.085),(outer-.050,-.185),(loop+.135,-.185),(loop+.112,-.075),
                 (loop+.112,.075))
        ring(cx,cy,phi,profile,SHELL,lambda i,j=petal:part(i,j))
        for i in range(SEGMENTS//2):
            a=math.tau*2*i/SEGMENTS;b=math.tau*2*(i+1)/SEGMENTS
            owner=petal if math.cos((a+b)/2-phi)>0 else -2
            points=tuple((cx+.302*math.cos(t),cy+.302*math.sin(t),z)
                         for t,z in ((a,.169),(a,-.169),(b,-.169),(b,.169)))
            emit(points,[(math.cos(t),math.sin(t),0) for t in (a,a,b,b)],EDGE,owner)
        # Dark recessed channel and a raised inner guide lip, on both sides.
        for side in (1,-1):
            for i in range(SEGMENTS):
                a=phi+math.tau*i/SEGMENTS;b=phi+math.tau*(i+1)/SEGMENTS
                owner=part(i,petal)
                def v(r,t,z):return cx+r*math.cos(t),cy+r*math.sin(t),side*z
                flat((v(loop-.128,a,.089),v(loop+.113,a,.089),
                      v(loop+.113,b,.089),v(loop-.128,b,.089)),TRACK,owner,(0,0,side))
                flat((v(.275,a,.170),v(loop-.128,a,.170),
                      v(loop-.128,b,.170),v(.275,b,.170)),RECESS,owner,(0,0,side))
            # Knobs split across the same diameter as the real outer wing.
            def knob_owner(i,j=petal):
                t=math.tau*(i+.5)/SEGMENTS
                return j if math.cos(t-phi)>0 else -2
            cap(cx,cy,.302,.191,side,HIGHLIGHT,knob_owner)
            tangent=(-math.sin(phi),math.cos(phi));out=(math.cos(phi),math.sin(phi))
            # A recessed diameter and two small hexagonal grip halves.
            for half,owner in ((1,petal),(-1,-2)):
                for sign in (-1,1):
                    points=tuple((cx+t*tangent[0]+v*out[0],cy+t*tangent[1]+v*out[1],side*.209)
                                 for t,v in ((0,0),(.295*sign,0),(.295*sign,.008*half),(0,.008*half)))
                    flat(points,RECESS,owner,(0,0,side))
                # Half of a hexagon stays on its corresponding knob half.
                hexagon=[(cx+.105*math.cos(phi+math.pi/6+k*math.pi/3),
                          cy+.105*math.sin(phi+math.pi/6+k*math.pi/3),side*.214)
                         for k in range(6)]
                for a,b in zip(hexagon,hexagon[1:]+hexagon[:1]):
                    if ((a[0]+b[0])/2-cx)*out[0]+((a[1]+b[1])/2-cy)*out[1]<0:
                        own=-2
                    else:own=petal
                    if own==owner:
                        middle=mean((a,b));delta=(middle[0]-cx,middle[1]-cy)
                        inner_a=(a[0]-.07*delta[0],a[1]-.07*delta[1],a[2])
                        inner_b=(b[0]-.07*delta[0],b[1]-.07*delta[1],b[2])
                        flat((a,b,inner_b,inner_a),RECESS,owner,(0,0,side))
            # Short raised arcs provide a visible grip on the outer petals.
            for start,end in ((-72,-36),(-18,18),(36,72)):
                for k in range(4):
                    a=phi+math.radians(start+(end-start)*k/4)
                    b=phi+math.radians(start+(end-start)*(k+1)/4)
                    flat((v(outer-.072,a,.194),v(outer-.038,a,.194),
                          v(outer-.038,b,.194),v(outer-.072,b,.194)),HIGHLIGHT,petal,(0,0,side))

    # Rounded central web: both face plates, bevel and the actual edge band.
    for i,a in enumerate(outline):
        b=outline[(i+1)%len(outline)]
        for side in (1,-1):
            flat(((0,0,side*.160),(a[0]*.975,a[1]*.975,side*.160),
                  (b[0]*.975,b[1]*.975,side*.160)),SHELL,-2,(0,0,side))
            bevel=((a[0]*.975,a[1]*.975,side*.160),(a[0],a[1],side*.125),
                   (b[0],b[1],side*.125),(b[0]*.975,b[1]*.975,side*.160))
            flat(bevel if side==1 else tuple(reversed(bevel)),EDGE,-2)
        flat(((a[0],a[1],.125),(a[0],a[1],-.125),
              (b[0],b[1],-.125),(b[0],b[1],.125)),EDGE,-2)
    for side in (1,-1):cap(0,0,.235 if p==3 else .36,.189,side,HIGHLIGHT,lambda i:-2)
    return tuple(result)
