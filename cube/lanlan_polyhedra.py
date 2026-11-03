"""Fixed-cut LanLan shells, specified independently of their catalogue names.

Truncation caps use a shared gold colour, as on the physical puzzles. They
are real pieces carried by neighbouring turns, not additional turning axes.
"""
import math
from cube.polyhedral import CUBE,OCTA,TETRA,EDGE_AXES,Spec

KINDS=frozenset(('skewb_rhombic','jewel_fto','rua','helicopter_14'))


def specification(kind,n):
    if n!=3:raise ValueError('Unsupported LanLan mechanism order')
    if kind=='skewb_rhombic':
        return Spec(kind,n,EDGE_AXES,TETRA,(0.,),3)
    if kind=='jewel_fto':
        # FTO corners are flattened exactly at their shallow cut boundary.
        # Eight hexagons each retain six tiles; six square caps are whole.
        return Spec(kind,n,OCTA+CUBE,OCTA,(1/3,),3,
                    bounds=(1.,)*8+(2/math.sqrt(3),)*6)
    if kind=='rua':
        # Eight three-colour corners, six four-colour corners and 24 centres.
        # The twelve rhombi each show two quadrilaterals and four triangles.
        return Spec(kind,n,EDGE_AXES,EDGE_AXES,(.5,),2)
    if kind=='helicopter_14':
        # Truncate all eight Helicopter corners to a single gold triangle.
        # Only the twelve original edge axes turn, by 180 degrees.
        return Spec(kind,n,CUBE+OCTA,EDGE_AXES,(1/math.sqrt(2),),2,
                    bounds=(1.,)*6+(2/math.sqrt(3),)*8)
    raise ValueError('Unknown LanLan fixed-cut model')


def face_color(kind,face):
    if kind=='jewel_fto':return min(face,8)
    if kind=='helicopter_14':return min(face,6)
    return face
