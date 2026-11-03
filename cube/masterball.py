"""Rainbow Masterball: eight longitudes, four latitudes, half-ball flips."""
from functools import lru_cache
import math
from cube.polyhedral import Spec,Geometry,Sticker,mean,unit

SEGMENTS=8
LAYERS=4
# Horizontal planes in Masterball Rainbow: D = K * .55.
LATITUDES=(-math.pi/2,-math.asin(.55),0.,math.asin(.55),math.pi/2)


def point(theta,latitude):
    return (math.cos(latitude)*math.sin(theta),math.sin(latitude),
            math.cos(latitude)*math.cos(theta))


@lru_cache(maxsize=1)
def masterball_geometry():
    normals=tuple(point((i+.5)*math.pi/4,0.) for i in range(8))+((0.,1.,0.),(0.,-1.,0.))
    axes=((0.,1.,0.),)+tuple(point((i+2)*math.pi/4,0.) for i in range(8))
    spec=Spec('masterball',4,normals,axes,(),8,axis_steps=(1,)+(4,)*8)
    panels=[];centres=[]
    for layer in range(4):
        lo,hi=LATITUDES[layer:layer+2]
        for sector in range(8):
            a=sector*math.pi/4;b=a+math.pi/4
            boundary=tuple(point(a+(b-a)*j/6,lo) for j in range(7))
            boundary+=tuple(point(b,lo+(hi-lo)*j/6) for j in range(1,7))
            boundary+=tuple(point(b-(b-a)*j/6,hi) for j in range(1,7))
            boundary+=tuple(point(a,hi-(hi-lo)*j/6) for j in range(1,6))
            clean=[]
            for p in boundary:
                if not clean or sum((x-y)**2 for x,y in zip(p,clean[-1]))>1e-12:clean.append(p)
            if sum((x-y)**2 for x,y in zip(clean[0],clean[-1]))<1e-12:clean.pop()
            patches=[]
            for v in range(6):
                for u in range(6):
                    corners=(point(a+(b-a)*u/6,lo+(hi-lo)*v/6),
                             point(a+(b-a)*(u+1)/6,lo+(hi-lo)*v/6),
                             point(a+(b-a)*(u+1)/6,lo+(hi-lo)*(v+1)/6),
                             point(a+(b-a)*u/6,lo+(hi-lo)*(v+1)/6))
                    poly=[]
                    for p in corners:
                        if not poly or sum((x-y)**2 for x,y in zip(p,poly[-1]))>1e-12:poly.append(p)
                    if sum((x-y)**2 for x,y in zip(poly[0],poly[-1]))<1e-12:poly.pop()
                    if len(poly)>=3:patches.append(tuple(poly))
            i=layer*8+sector
            panels.append(Sticker(i,sector,tuple(clean),tuple(patches)))
            centres.append(point((a+b)/2,(lo+hi)/2))
    identity=tuple(range(32));perms=[];bands=[]
    rows=[];layers=[]
    for layer in range(4):
        band=tuple(range(layer*8,(layer+1)*8));row=list(identity)
        for i in band:row[i]=layer*8+(i%8+1)%8
        rows.append(tuple(row));layers.append(band)
    perms.append(tuple(rows));bands.append(tuple(layers))
    for boundary in range(8):
        moving={layer*8+sector for layer in range(4) for sector in range(8)
                if math.sin((sector+.5-boundary)*math.pi/4)>1e-7}
        row=list(identity)
        for i in moving:
            layer,sector=divmod(i,8)
            row[i]=(3-layer)*8+(2*boundary+3-sector)%8
        perms.append((tuple(row),));bands.append((tuple(sorted(moving)),))
    return Geometry(spec,tuple(panels),tuple((i,) for i in range(32)),tuple(centres),tuple(perms),tuple(bands))


@lru_cache(maxsize=1)
def skin():
    return tuple(tuple((patch,unit(mean(patch)),tuple(unit(p) for p in patch))
                       for patch in s.patches) for s in masterball_geometry().stickers)
