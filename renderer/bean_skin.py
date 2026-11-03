"""Round bead caps with smooth per-vertex shading, independent of slot state."""
from functools import lru_cache
import math


@lru_cache(maxsize=2)
def skin(kind):
    from cube.dial_beans import bean_geometry
    result=[]
    for centre in bean_geometry(kind).centres:
        side=1 if centre[2]>0 else -1;patches=[]
        def vertex(level,t):
            phi=level*math.pi/6;theta=t*math.pi/15
            normal=(math.sin(phi)*math.cos(theta),math.sin(phi)*math.sin(theta),side*math.cos(phi))
            point=(centre[0]+.105*normal[0],centre[1]+.105*normal[1],centre[2]+.105*normal[2])
            return point,normal
        for level in range(3):
            for t in range(30):
                records=([vertex(0,0),vertex(1,t),vertex(1,t+1)] if level==0 else
                         [vertex(level,t),vertex(level+1,t),vertex(level+1,t+1),vertex(level,t+1)])
                polygon=tuple(p for p,n in records);normals=tuple(n for p,n in records)
                normal=tuple(sum(n[a] for n in normals)/len(normals) for a in range(3))
                patches.append((polygon,normal,normals))
        result.append(tuple(patches))
    return tuple(result)
