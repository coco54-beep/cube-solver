"""Enter actual Fisher Skewb pieces by both colour and shape."""
from cube.fisher_skewb import FisherSkewbCube, appearance
from cube.mirror_tower import Piece
from renderer.fisher_skewb_view import FisherSkewbView
from ui.screens.mirror_skewb_screen import MirrorSkewbScreen
from ui.screens.mirror_tower_screen import MirrorTowerScreen
import math
from cube.fisher_skewb import SHELL_NORMALS


class FisherSkewbScreen(MirrorSkewbScreen):
    cube_class=FisherSkewbCube
    view_class=FisherSkewbView
    hint_key='fisher_skewb.hint'

    def on_pre_enter(self,*args):
        super().on_pre_enter(*args)
        self._poly_orientation=self._view_orientation=None
        self._set_face_camera(self._face)
        self._refresh()

    def _face_camera(self,index):
        x,y,z=SHELL_NORMALS[index]
        return math.degrees(math.atan2(x,z)),math.degrees(math.atan2(y,math.hypot(x,z)))

    def _placements(self,home,position):
        # White/yellow square centres have two visually identical directions.
        # Present one; the solver resolves the unobservable orientation.
        result=[]
        seen=set()
        for frame in super()._placements(home,position):
            signature=appearance(home,frame)
            if signature not in seen:
                seen.add(signature)
                result.append(frame)
        return tuple(result)

    def customize(self):
        if not self.entry_can_edit() or self._position not in self._recorded:
            return
        piece=self._cube.pieces[self._position]
        options=self._placements(piece.home,self._position)
        if len(options)<2: return
        current=appearance(piece.home,piece.frame)
        index=next(i for i,f in enumerate(options) if appearance(piece.home,f)==current)
        self._remember()
        self._cube.pieces[self._position]=Piece(piece.home,options[(index+1)%len(options)])
        self._refresh()

    def _refresh(self):
        MirrorTowerScreen._refresh(self)
