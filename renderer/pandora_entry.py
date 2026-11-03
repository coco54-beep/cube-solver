"""True Pandora panels with ordinary logical facelet identities for entry."""
from cube.shape_cube import pandora_faces
from cube.polyhedral import CUBE,dot
from cube.coordinates import FACE_NORMALS
from renderer.entry_style import UNENTERED,PLASTIC


def build_scene(cube,highlight=None):
    from renderer.scene import _RGB,_dim
    vertices=[];indices=[];infos=[]
    for pos,cubie in cube.cubies.items():
        for polygon,color in pandora_faces(pos):
            if color<0:
                color=next((i for i,n in enumerate(CUBE) if all(abs(dot(n,p)-1)<1e-8 for p in polygon)),-1)
                if color<0:continue
                rgba=PLASTIC
            else:
                code=cubie.stickers.get(CUBE[color],'')
                palette=getattr(cube,'pandora_entry_palette',{})
                rgba=palette.get(code,tuple(_RGB[code])+(1,) if code in _RGB else UNENTERED)
                if highlight and cubie.home not in highlight:rgba=_dim(rgba)
            face=next(f for f,n in FACE_NORMALS.items() if tuple(n)==CUBE[color])
            points=tuple(polygon) if len(polygon)==4 else tuple(polygon)+(polygon[0],)
            start=len(vertices)//7
            for point in points:vertices.extend((*point,*rgba))
            indices.extend((start,start+1,start+2,start,start+2,start+3))
            infos.append((pos,face,tuple(range(len(polygon)))))
    return vertices,indices,infos
