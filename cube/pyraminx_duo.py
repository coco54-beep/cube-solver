"""Pyraminx Duo: four fixed-position corners and four moving face centres."""
from cube.polyhedral import TETRA, Spec, add, body, key, mean, scale


def duo_specification():
    return Spec('pyraminx_duo', 3, TETRA,
                tuple(scale(n, -1) for n in TETRA), (0.,), 3)


def duo_skin(spec):
    """Pentagonal corner stickers surround a small inverted centre triangle.

    The joins at edge midpoints are shared across neighbouring faces. The
    centre size is an idealised proportion, rather than a plastic mould CAD.
    """
    result=[]
    for face, vertices in enumerate(body(spec.normals)):
        centre=mean(vertices)
        inner=tuple(add(centre,scale(add(v,scale(centre,-1)),-.34)) for v in vertices)
        result.append((('centre',face),face,inner))
        for i,vertex in enumerate(vertices):
            after=(i+1)%3
            before=(i-1)%3
            polygon=(vertex,mean((vertex,vertices[after])),inner[before],
                     inner[after],mean((vertices[before],vertex)))
            result.append((('corner',key(vertex)),face,polygon))
    return result
