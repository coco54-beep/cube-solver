"""Ancient Coin Cube: eight independent corners and six four-leaf discs."""
import math
from cube.polyhedral import CUBE,OCTA,Spec,body,mean,key,scale
from cube.coin_tetrahedron import _arc


def specification():
    return Spec('ancient_coin',3,CUBE,CUBE+OCTA,(),12,axis_steps=(3,)*6+(4,)*8)


def skin(spec):
    fragments=[]
    for face,vertices in enumerate(body(CUBE)):
        centre=mean(vertices);inner=[]
        for i,vertex in enumerate(vertices):
            before=mean((vertices[i-1],vertex));after=mean((vertex,vertices[(i+1)%4]))
            outer_arc=_arc(centre,before,after,CUBE[face])
            inner_arc=_arc(vertex,before,after,CUBE[face])
            inner.append(inner_arc)
            fragments.append((('corner',key(vertex)),face,(vertex,)+tuple(reversed(outer_arc))))
            fragments.append((('leaf',face,key(vertex)),face,outer_arc+tuple(reversed(inner_arc))[1:-1]))
        fragments.append((('centre',face),face,tuple(p for arc in inner for p in arc[:-1])))
    return fragments


def moving_pieces(signatures,axis):
    if axis<6:return {i for i,s in enumerate(signatures) if s[0] in ('leaf','centre') and s[1]==axis}
    vertex=key(scale(specification().axes[axis],math.sqrt(3)))
    return {i for i,s in enumerate(signatures) if s[0]=='corner' and s[1]==vertex or s[0]=='leaf' and s[2]==vertex}
