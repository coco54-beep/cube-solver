"""Paged, real-shape Minx entry with distinct visible orientations only."""
from kivy.uix.label import Label
from app.i18n import tr
from cube.mirror_minx import MirrorMinxCube,placements,appearance
from renderer.mirror_minx_view import MirrorMinxView
from ui.screens.mirror_tower_screen import MirrorTowerScreen
from ui.screens.polyhedral_screen import _app


class MirrorMinxScreen(MirrorTowerScreen):
    cube_class=MirrorMinxCube
    view_class=MirrorMinxView
    hint_key='mirror_minx.hint'

    def on_pre_enter(self,*args):
        fresh=self._cube is not _app().cube
        super().on_pre_enter(*args)
        if fresh and self._poly_orientation is not None:
            # The face is already aligned by the observation matrix. Applying
            # its world-space camera angle again hides the selected centre.
            self.view.yaw=self.view.pitch=self.view.roll=0
            self._refresh()

    def _card_camera(self,preview):
        # A face-on centre hides its distinguishing height. Keep the selected
        # face orientation, then look slightly across the rigid cut walls.
        preview.set_whole_world(self.view._whole_world)
        preview.yaw=self.view.yaw+25
        preview.pitch=max(-75,min(75,self.view.pitch+18))
        preview.roll=self.view.roll

    def _placements(self,home,position):
        result=[];seen=set()
        for frame in placements(self._cube.n,home,position):
            signature=appearance(self._cube.n,home,frame)
            if signature not in seen:seen.add(signature);result.append(frame)
        return tuple(result)

    def entry_center_preset(self):return set()

    def open_demo(self):
        from demo.expanded_support import open_tutorial
        return open_tutorial(self)

    def customize(self):
        if not self.entry_can_edit() or self._position not in self._recorded:return
        from cube.mirror_tower import Piece
        piece=self._cube.pieces[self._position];options=self._placements(piece.home,self._position)
        if len(options)<2:return
        target=appearance(self._cube.n,piece.home,piece.frame)
        index=next(i for i,f in enumerate(options) if appearance(self._cube.n,piece.home,f)==target)
        self._remember();self._cube.pieces[self._position]=Piece(piece.home,options[(index+1)%len(options)])
        self._refresh()
