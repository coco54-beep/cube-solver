"""Direct physical-brick drafts. No scramble reconstruction is required.

Frames enumerate the real mechanism's 24 rigid orientations. Drafts may be
incomplete; they never masquerade as a playable or solvable CuboidCube.
"""
from cube.appearance import ROTATIONS
from cube.cuboid import CuboidCube, IDENTITY, layout, transform
from cube.polyhedral import CUBE
from time import monotonic
from itertools import product


class CuboidEntry:
    def __init__(self, cube):
        self.puzzle_kind=cube.puzzle_kind
        self.dimensions,self.core_n=cube.dimensions,cube.core_n
        self.n=cube.n
        self.colors=list(cube.colors)
        self.frames=tuple(cube.frames)
        cells,boxes,entries,lookup,base=layout(self.puzzle_kind)
        visible=[p for p,group in enumerate(cells)
                 if any(any(abs(v)==self.core_n-1 for v in cell) for cell in group)]
        self.visible=tuple(sorted(visible,key=lambda p:-sum((lo+hi)/2 for lo,hi in boxes[p])))
        self.placed={}
        self.panel_colors={}
        for piece in self.visible:
            for face,normal in enumerate(CUBE):
                axis,sign=next((a,v) for a,v in enumerate(normal) if v)
                home=next((p for p in cells[piece] if p[axis]==sign*(self.core_n-1)),None)
                if home is None:continue
                index=(lookup[piece,face] if self.puzzle_kind=='cuboid_133' else
                       lookup[transform(cube.frames[piece],home),transform(cube.frames[piece],normal)])
                color=cube.colors[index]
                self.panel_colors[piece,face]=color if color>=0 else face
        self._options={}
        self._footprints={}
        self._bounds={}

    def options(self,piece):
        """Group orientations by destination, so direction never changes location."""
        if piece not in self._options:
            cells=layout(self.puzzle_kind)[0][piece]
            groups={}
            for frame in ROTATIONS:
                footprint=self.footprint(piece,frame)
                if self.puzzle_kind=='cuboid_133':
                    # The four edges and centre have fixed locations.
                    home=tuple(sum(p[a] for p in cells)/len(cells) for a in range(3))
                    if home==(0.,0.,0.) and frame!=IDENTITY:continue
                    if sum(v!=0 for v in home)<=1 and transform(frame,home)!=home:continue
                groups.setdefault((footprint,self.bounds(piece,frame)),[]).append(frame)
            self._options[piece]=tuple(tuple(v) for v in groups.values())
        return self._options[piece]

    def footprint(self,piece,frame):
        cached=self._footprints.get((piece,frame))
        if cached is not None:return cached
        if self.puzzle_kind=='cuboid_133':
            box=layout(self.puzzle_kind)[1][piece]
            centre=tuple((a+b)/2 for a,b in box)
            result=frozenset((transform(frame,centre),))
        else:result=frozenset(transform(frame,p) for p in layout(self.puzzle_kind)[0][piece])
        self._footprints[piece,frame]=result
        return result

    def bounds(self,piece,frame):
        """Physical extents also matter for Camouflage's asymmetric shell."""
        if (piece,frame) not in self._bounds:
            points=[transform(frame,p) for p in product(*layout(self.puzzle_kind)[1][piece])]
            self._bounds[piece,frame]=tuple((min(p[a] for p in points),max(p[a] for p in points)) for a in range(3))
        return self._bounds[piece,frame]

    def fits(self,piece,frame,placed=None):
        placed=self.placed if placed is None else placed
        target=self.footprint(piece,frame)
        box=self.bounds(piece,frame)
        for other,f in placed.items():
            if other==piece:continue
            if target.intersection(self.footprint(other,f)):return False
            otherbox=self.bounds(other,f)
            if all(min(a[1],b[1])-max(a[0],b[0])>1e-7 for a,b in zip(box,otherbox)):return False
        return True

    def place(self,piece,frame):
        if frame not in tuple(f for group in self.options(piece) for f in group):
            raise ValueError('cuboid.entry_invalid')
        if not self.fits(piece,frame):raise ValueError('cuboid.entry_overlap')
        self.placed[piece]=frame

    def preview(self,piece=None,frame=None):
        """A rendering adapter, deliberately not an entered CuboidCube."""
        from types import SimpleNamespace
        frames=list(self.frames)
        active=dict(self.placed)
        if piece is not None:active[piece]=frame
        for p,f in active.items():frames[p]=f
        return SimpleNamespace(puzzle_kind=self.puzzle_kind,dimensions=self.dimensions,n=self.n,
                               core_n=self.core_n,frames=tuple(frames),colors=self.colors,
                               entry_pieces=frozenset(active),entry_panel_colors=self.panel_colors,
                               entry_preview=piece)

    def to_cube(self):
        if any(p not in self.placed for p in self.visible):raise ValueError('cuboid.entry_incomplete')
        cells,boxes,entries,lookup,base=layout(self.puzzle_kind)
        frames=dict(self.placed)
        if any(not self.fits(p,f,frames) for p,f in frames.items()):
            raise ValueError('cuboid.entry_overlap')
        # Invisible pieces are mechanical supports, not user input. Fill the
        # remaining cells by a bounded exact cover, never on a worker's history.
        occupied=set().union(*(self.footprint(p,f) for p,f in frames.items()))
        remaining=[p for p in range(len(cells)) if p not in frames]
        candidates={p:tuple(group[0] for group in self.options(p)) for p in remaining}
        budget=[20000]
        deadline=monotonic()+.4
        def fill(todo,used):
            if not todo:return True
            budget[0]-=1
            if budget[0]<0 or monotonic()>deadline:return False
            choices={p:[f for f in candidates[p] if not used.intersection(self.footprint(p,f))
                        and self.fits(p,f,frames)] for p in todo}
            p=min(todo,key=lambda p:len(choices[p]))
            for frame in choices[p]:
                frames[p]=frame
                if fill([q for q in todo if q!=p],used|self.footprint(p,frame)):return True
                frames.pop(p,None)
            frames.pop(p,None)
            return False
        if not fill(remaining,occupied):
            raise ValueError('cuboid.entry_budget' if budget[0]<0 or monotonic()>deadline else 'cuboid.entry_invalid')
        colors=[-1]*len(entries)
        for (p,face),color in self.panel_colors.items():
            frame=frames[p];normal=CUBE[face]
            if self.puzzle_kind=='cuboid_133':colors[lookup[p,face]]=color;continue
            axis,sign=next((a,v) for a,v in enumerate(normal) if v)
            for home in cells[p]:
                if home[axis]==sign*(self.core_n-1):
                    colors[lookup[transform(frame,home),transform(frame,normal)]]=color
        entered=CuboidCube(self.puzzle_kind,colors,tuple(frames[p] for p in range(len(cells))))
        # This checks structural consistency, not general reachability.
        entered.geometry
        return entered
