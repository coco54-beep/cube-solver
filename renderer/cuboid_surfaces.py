"""Pure physical cuboid surface geometry shared by rendering and photo input."""
from cube.cuboid import layout,transform
from cube.polyhedral import scale
from renderer.entry_style import surface_panel

# Counter-clockwise, looking from outside each face.
QUADS=(
 ((0,1,0),((-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1))),
 ((1,0,0),((1,-1,-1),(1,1,-1),(1,1,1),(1,-1,1))),
 ((0,0,1),((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))),
 ((0,-1,0),((-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1))),
 ((-1,0,0),((-1,-1,1),(-1,1,1),(-1,1,-1),(-1,-1,-1))),
 ((0,0,-1),((1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1))),
)


def surfaces(cube):
 cache_key=(cube.frames,tuple(cube.colors),getattr(cube,'entry_pieces',None),
            tuple(sorted(getattr(cube,'entry_panel_colors',{}).items())),getattr(cube,'entry_preview',None))
 cached=getattr(cube,'_cuboid_surface_cache',None)
 if cached is not None and cached[0]==cache_key:return cached[1]
 cells,boxes,entries,lookup,_base=layout(cube.puzzle_kind)
 result=[];factor=2.4/getattr(cube,'shell_span',5 if cube.puzzle_kind=='camouflage_3' else max(cube.dimensions))
 for piece,(frame,box) in enumerate(zip(cube.frames,boxes)):
  if hasattr(cube,'entry_pieces') and piece not in cube.entry_pieces:continue
  for face,(normal,corners) in enumerate(QUADS):
   points=tuple(tuple(box[a][1 if p[a]>0 else 0] for a in range(3)) for p in corners)
   normalworld=transform(frame,normal)
   world=tuple(scale(transform(frame,p),factor) for p in points)
   # A sticker exists only on an original exterior face. The rigid cut wall
   # is still rendered and can be exposed after a quarter turn.
   axis,sign=next((a,v) for a,v in enumerate(normal) if v)
   anchored=getattr(cube,'panel_anchored',False)
   original=(piece,face) in lookup if anchored else any(p[axis]==sign*(cube.core_n-1) for p in cells[piece])
   index=-1;color=-1
   if original:
    if anchored:index=lookup[piece,face]
    else:
     home=next(p for p in cells[piece] if p[axis]==sign*(cube.core_n-1))
     index=lookup[piece,face] if cube.puzzle_kind=='cuboid_133' else lookup[transform(frame,home),normalworld]
    color=(cube.entry_panel_colors[piece,face] if hasattr(cube,'entry_panel_colors') else cube.colors[index])
    if piece==getattr(cube,'entry_preview',None):index=-3
    if color<0:color=-2
   # Keep the closed body; the full panel receives the common screen-space seam.
   result.append((world,normalworld,-1,-1,0,piece,1))
   if original:
    panel=surface_panel(world,normalworld)
    result.append((panel,normalworld,color,index,0,piece,1))
 result=tuple(result)
 cube._cuboid_surface_cache=(cache_key,result)
 return result


