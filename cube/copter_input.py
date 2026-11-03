"""Editable observation state for the curved edge-turning cube.

Paint and pose remain separate. Shared playback checkpoints carry both; a
pose edit never changes another piece or discards any previously entered paint.
"""
from cube.curvy_copter import CopterState
from cube.polyhedral import CUBE,EDGE_AXES,Geometry,Spec,Sticker,mean,dot
from cube.appearance import transform_frame


class CopterCube(CopterState):
    puzzle_kind='lanlan_curvy_copter'
    n=3
    color_count=6
    geometry_profile='sphere-cut'

    @classmethod
    def solved(cls):return cls()
    entered=CopterState.clone

    @property
    def colors(self):
        return [(color,self.frames[home]) for color,(home,face,polygon) in zip(self.paints,self.panels)]

    @colors.setter
    def colors(self,values):
        try:
            if len(values)!=len(self.panels):raise ValueError('rigid.invalid')
            frames=list(self.frames);paints=[];seen={}
            for (home,face,poly),(color,frame) in zip(self.panels,values):
                frame=tuple(tuple(column) for column in frame)
                if home in seen and seen[home]!=frame:raise ValueError('rigid.invalid')
                seen[home]=frame;frames[home]=frame;paints.append(color)
            candidate=type(self)(frames,paints)
        except (ValueError,TypeError,OverflowError):raise ValueError('rigid.invalid') from None
        self.frames,self.paints=candidate.frames,candidate.paints

    def restore(self,cube):
        candidate=type(self)(cube.frames,cube.paints)
        self.frames,self.paints=candidate.frames,candidate.paints

    def apply_moves(self,moves):
        for move in moves:self.apply_move(move)
        return self

    def paint(self,slot,color):
        if type(slot) is not int or slot not in range(len(self.panels)):raise ValueError('rigid.invalid')
        if type(color) is not int or color not in range(-1,6):raise ValueError('rigid.invalid')
        paints=list(self.paints);paints[slot]=color;self.paints=tuple(paints)

    def set_piece_frame(self,home,frame):
        if type(home) is not int or home not in {p[0] for p in self.panels}:raise ValueError('rigid.invalid')
        frames=list(self.frames);frames[home]=frame
        candidate=type(self)(frames,self.paints)
        self.frames=candidate.frames

    def is_solved(self):
        from cube.copter_aligned import observed_colors,geometry
        try:return observed_colors(self)==tuple(s.face for s in geometry().stickers)
        except ValueError:return False

    @property
    def geometry(self):
        cached=getattr(self,'_entry_geometry',None)
        if cached is not None and cached[0]==self.frames:return cached[1]
        world=self.world_panels();stickers=[];pieces=[[] for _ in self.regions];centres=[]
        for slot,((home,face,poly),polygon) in enumerate(zip(self.panels,world)):
            normal=transform_frame(self.frames[home],CUBE[face])
            shown=max(range(6),key=lambda i:dot(normal,CUBE[i]))
            stickers.append(Sticker(home,shown,polygon));pieces[home].append(slot)
        for home,slots in enumerate(pieces):
            centres.append(mean(tuple(p for i in slots for p in world[i])) if slots else (0.,0.,0.))
        layers=[]
        for axis in range(12):
            try:layer=self.selection(axis)
            except ValueError:layer=()
            layers.append((tuple(layer),))
        g=Geometry(Spec(self.puzzle_kind,3,CUBE,EDGE_AXES,(),360,axis_steps=(180,)*12),
                   tuple(stickers),tuple(map(tuple,pieces)),tuple(centres),((),)*12,tuple(layers))
        self._entry_geometry=(self.frames,g)
        return g


def scrambled(seed=None,length=24,cancel=None):
    """Mix closed jumbling actions first, then leave a legal non-cubic shape."""
    from random import Random
    from cube.copter_aligned import generators
    from time import monotonic
    rng=Random(seed);cube=CopterCube();previous=None;deadline=monotonic()+12
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()>deadline:raise TimeoutError('copter.scramble_timeout')
    options=generators()
    for _ in range(length):
        guard();index=rng.choice([i for i in range(len(options)) if i!=previous])
        previous=index
        for move in options[index][1]:cube.apply_move(move,guard)
    for _ in range(6):
        choices=list(cube.moves());rng.shuffle(choices)
        for move in choices:
            guard()
            try:cube.apply_move(move,guard);break
            except ValueError:continue
    return cube
