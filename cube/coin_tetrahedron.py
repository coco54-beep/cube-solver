"""QiYi Coin Tetrahedron: four corner turns and four face-disc turns."""
import math
from cube.polyhedral import (TETRA, Spec, add, body, cross, dot, key, mean,
                             scale)


def coin_specification():
    return Spec('coin_tetrahedron',3,TETRA,
                TETRA+tuple(scale(n,-1) for n in TETRA),(0.,),3)


def _arc(centre,start,end,normal,steps=24):
    u=add(start,scale(centre,-1))
    v=add(end,scale(centre,-1))
    angle=math.atan2(dot(cross(u,v),normal),dot(u,v))
    tangent=cross(normal,u)
    return (start,)+tuple(add(centre,add(scale(u,math.cos(t)),scale(tangent,math.sin(t))))
                          for t in (angle*i/steps for i in range(1,steps)))+(end,)


def coin_skin(spec):
    """Shared exact incircles and corner-centred arcs, seven panels per face.

    A corner sphere through the two adjacent edge midpoints bounds each oval
    inside the disc. Its other boundary is the face incircle. No circular
    boundary is approximated by a straight triangle cut.
    """
    result=[]
    for face,vertices in enumerate(body(spec.normals)):
        centre=mean(vertices)
        inner_arcs=[]
        for i,vertex in enumerate(vertices):
            before=mean((vertices[i-1],vertex))
            after=mean((vertex,vertices[(i+1)%3]))
            outer=_arc(centre,before,after,spec.normals[face])
            inner=_arc(vertex,before,after,spec.normals[face])
            inner_arcs.append(inner)
            result.append((('corner',key(vertex)),face,(vertex,)+tuple(reversed(outer))))
            result.append((('leaf',face,key(vertex)),face,outer+tuple(reversed(inner))[1:-1]))
        result.append((('centre',face),face,tuple(p for arc in inner_arcs for p in arc[:-1])))
    return result


def moving_pieces(signatures,axis):
    if axis<4:
        return {i for i,s in enumerate(signatures) if s[0] in ('leaf','centre') and s[1]==axis}
    vertex=key(scale(coin_specification().axes[axis],3))
    return {i for i,s in enumerate(signatures)
            if (s[0]=='corner' and s[1]==vertex) or (s[0]=='leaf' and s[2]==vertex)}
