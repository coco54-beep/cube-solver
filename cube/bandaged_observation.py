"""Six visible face colours and seams for the six fixed bandage presets."""
from cube.cuboid_observation import SixViewDraft,MatchResult,UNKNOWN,EMPTY,PLASTIC
from cube.cuboid import FACES
from cube.bandaged_cube import BandagedCube,KINDS
from cube.bandaged_entry import plates,reconstruct
from cube.conversion import cubies_to_facelets

COLOR_CODES=('W','R','G','Y','O','B')


def state_key(cube):
    return (cube.puzzle_kind,tuple(sorted((p,c.home,c.appearance_frame,tuple(sorted(c.stickers.items())))
                                         for p,c in cube.cubies.items())))


class BandagedSixViewDraft(SixViewDraft):
    def __init__(self,kind,state=None):
        n=KINDS[kind];self.kind=kind;self.version=3
        self.model=dict(kind=kind,shapes=((n,n),)*6,levels=((n-1,),)*6)
        self.views=[[(UNKNOWN,0,None) for _ in range(n*n)] for _ in range(6)]
        if state is not None:
            if (state.get('version')!=self.version or state.get('kind')!=kind or
                    len(state.get('views',()))!=6 or any(len(v)!=n*n for v in state['views'])):
                raise ValueError('six.model_mismatch')
            for face,view in enumerate(state['views']):
                for index,(color,group,depth) in enumerate(view):
                    if color not in (UNKNOWN,EMPTY,PLASTIC,0,1,2,3,4,5) or type(group) is not int or group<0:
                        raise ValueError('six.model_mismatch')
                    if depth is not None and depth!=n-1:raise ValueError('six.model_mismatch')
                    self.views[face][index]=(color,group,depth)

    @classmethod
    def from_facelets(cls,kind,data,connections=()):
        draft=cls(kind);n=KINDS[kind]
        for face,key in enumerate(FACES):
            grid=data.get(key,[]) if isinstance(data,dict) else []
            for r in range(n):
                for c in range(n):
                    color=grid[r][c] if r<len(grid) and isinstance(grid[r],(tuple,list)) and c<len(grid[r]) else ''
                    value=COLOR_CODES.index(color) if color in COLOR_CODES else UNKNOWN
                    draft.views[face][r*n+c]=(value,0,None)
        for group,(face,cells) in enumerate(connections,1):
            if face not in FACES:continue
            index=FACES.index(face)
            for r,c in cells:
                if 0<=r<n and 0<=c<n:
                    color,_,depth=draft.views[index][r*n+c]
                    draft.views[index][r*n+c]=(color,group,depth)
        return draft

    @classmethod
    def from_cube(cls,cube):
        return cls.from_facelets(cube.puzzle_kind,cubies_to_facelets(cube.cubies,cube.n),
                                ((p.face,p.cells) for p in plates(cube)))

    def paint(self,face,indices,color,depth=None):
        indices=tuple(indices)
        # A tap repaints the whole existing plate. Dragging records a new plate,
        # including its seam against an equally coloured neighbouring plate.
        if len(indices)==1:
            group=self.views[face][indices[0]][1]
            if group>0:
                if color not in (UNKNOWN,EMPTY,PLASTIC,0,1,2,3,4,5):raise ValueError('six.model_mismatch')
                for i,value in enumerate(self.views[face]):
                    if value[1]==group:self.views[face][i]=(color,group if color not in (UNKNOWN,EMPTY) else 0,depth)
                return
        return super().paint(face,indices,color,depth)

    def facelets(self):
        n=KINDS[self.kind]
        return {key:[[COLOR_CODES[self.views[f][r*n+c][0]] if self.views[f][r*n+c][0]>=0 else ''
                      for c in range(n)] for r in range(n)] for f,key in enumerate(FACES)}

    def connections(self):
        n=KINDS[self.kind];result=[]
        for f,key in enumerate(FACES):
            groups={}
            for i,(color,group,depth) in enumerate(self.views[f]):
                groups.setdefault(('plate',group) if group else ('single',i),[]).append(divmod(i,n))
            result.extend((key,tuple(cells)) for cells in groups.values())
        return set(result)

    def match(self,seconds=6.,cancel=None,node_limit=80000):
        if cancel is not None and cancel.is_set():return MatchResult('cancelled')
        missing=self.missing()
        if missing:return MatchResult('incomplete',face=missing[0],cell=missing[1])
        for f,view in enumerate(self.views):
            for i,(color,group,depth) in enumerate(view):
                if color<0:return MatchResult('conflict',face=f,cell=i)
        try:
            cube=reconstruct(self.kind,self.facelets(),self.connections(),seconds=seconds,cancel=cancel)
        except InterruptedError:return MatchResult('cancelled')
        except ValueError as error:
            return MatchResult('budget' if str(error)=='bandage.entry_budget' else 'conflict')
        return MatchResult('ok',cube=cube)
