"""Piece and orientation input for Axis and other three-layer shape mods."""
from app.i18n import tr
from cube.mastermorphix import position_kind
from cube.shape_cube import AxisCube
from renderer.shape_cube_view import AxisView
from ui.screens.mirror_screen import MirrorScreen
from ui.screens.mastermorphix_screen import _app
from app.constants import COLOR_INFO


class ShapeCubeScreen(MirrorScreen):
    supports_palette_settings=True
    cube_class=AxisCube
    view_class=AxisView

    def _blank(self,palette):
        super()._blank(palette)
        if self._cube.puzzle_kind!='football':
            from app.prefs import get
            from cube.shape_cube import PALETTE
            saved=get('shape_palette_'+self._cube.puzzle_kind,None)
            colors=[COLOR_INFO[c][1] for c in PALETTE]
            if isinstance(saved,list) and len(saved)==6 and all(isinstance(c,list) and len(c)==4 and
                    all(isinstance(v,(int,float)) and 0<=v<=1 for v in c) for c in saved):
                colors=saved
        self._apply_shape_colors(colors,persist=False,refresh=False)

    def entry_center_preset(self):
        # 和粽子魔方一致：预置中心块颜色，方便对位（足球无此中心概念）。
        if self._cube is None or self._cube.n != 3 or self._cube.puzzle_kind=='football':
            return set()
        return {p for p in self._all_positions() if position_kind(p)=='center'}

    def _apply_shape_colors(self,colors,persist=True,refresh=True):
        from app.prefs import set
        keys=tuple(f'S_{self._cube.puzzle_kind}_{i}' for i in range(6))
        for i,key in enumerate(keys):
            COLOR_INFO[key]=(str(i+1),tuple(colors[i][:3])+(1,))
        self._cube.palette=keys
        for previous,recorded in self._history:
            previous.palette=keys
        if persist:
            set('shape_palette_'+self._cube.puzzle_kind,[list(COLOR_INFO[k][1]) for k in keys])
        if refresh:
            self._refresh()

    def open_color(self,index):
        self.open_palette_settings(index)

    def default_palette_colors(self):
        from cube.shape_cube import PALETTE
        return [COLOR_INFO[c][1] for c in PALETTE]

    def apply_palette_colors(self,colors):
        self._apply_shape_colors(colors)
        _app().solve_result=None

    def restore_preset(self):
        from cube.shape_cube import PALETTE
        self._apply_shape_colors([COLOR_INFO[c][1] for c in PALETTE])

    def on_pre_enter(self,*args):
        from cube.shape_cube import FootballCube,PandoraCube,WindmillCube,FisherCube
        from renderer.shape_cube_view import FootballView,PandoraView,WindmillView,FisherView
        kind=_app().puzzle_kind
        cube_class,view_class={'football':(FootballCube,FootballView),'pandora':(PandoraCube,PandoraView),
                              'windmill':(WindmillCube,WindmillView),'fisher':(FisherCube,FisherView)}.get(kind,(AxisCube,AxisView))
        if self.cube_class is not cube_class:
            self.reset_interaction()
            self.clear_widgets()
            self.cube_class,self.view_class=cube_class,view_class
            self._cube=None
            self.build_ui()
        super().on_pre_enter(*args)
        pending=getattr(_app(),'camera_shape_result',None)
        if pending is not None and pending.puzzle_kind==kind:
            from vision.scan_profiles import CUBE_CODES
            pending.palette=tuple(f'S_pandora_{CUBE_CODES.index(c)}' if c in CUBE_CODES else c for c in pending.palette)
            self._cube=pending
            self._recorded=set(pending.positions)
            self._history=[]
            self._preview=None
            from renderer.cube_orientation import CubeOrientation
            self._ori=CubeOrientation(self._cube.n)
            self._pos=self._cube.positions[0]
            self._group=position_kind(self._pos)
            _app().camera_shape_result=None
            self._refresh()

    def go_back(self):
        if getattr(_app(),'input_from_camera',False):
            self.manager.current='CameraScreen'
            return
        self.manager.current='HomeScreen'

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:
            self._refresh_palette_button()
            self.demo_button.disabled=self._cube.n>3
            self.demo_button.opacity=0 if self._cube.n>3 else 1
            self.reference_label.text=tr('football.pattern_hint' if self._cube.puzzle_kind=='football' else 'shape.reference')
            self.hint.text=tr('shape.hint')
            if self._cube.puzzle_kind=='pandora' and position_kind(self._pos)=='center':
                # A plain square centre looks identical in all four turns.
                self.rotate.disabled=True
                self.hint.text=tr('shape.pandora_center')
            elif self._cube.puzzle_kind in ('windmill','fisher'):
                self.reference_label.text=tr('shape.'+self._cube.puzzle_kind+'_reference')
                if self._cube.n == 3 and position_kind(self._pos)=='center' and self._pos[1]:
                    self.rotate.disabled=True
                    self.hint.text=tr('shape.pandora_center')
            if self._cube.n == 4:
                self.reference_label.text=tr('shape.four_reference')
                piece=self._cube.cubies[self._pos]
                self.rotate.disabled=self._pos not in self._recorded or len(self._placements(piece.home,self._pos))<=1

    def available_homes(self,pos):
        if self._cube.n == 4:
            from cube.high_shape import shape_groups
            groups,_=shape_groups(self._cube.puzzle_kind,self._cube.n)
            representatives={}
            for home in super().available_homes(pos):
                representatives.setdefault(groups[home],home)
            return list(representatives.values())
        if position_kind(pos)=='center':
            return [pos]
        return super().available_homes(pos)

    def _same_piece(self,left,right):
        if self._cube.n == 4:
            from cube.high_shape import shape_groups
            groups,_=shape_groups(self._cube.puzzle_kind,self._cube.n)
            return groups[left]==groups[right]
        return super()._same_piece(left,right)

    def choose_piece(self,home,frame=None):
        if not self.entry_can_edit():
            return
        if self._cube.n == 4:
            from cube.high_shape import equivalent_pieces
            frame=frame or self._placements(home,self._pos)[0]
            used={p.home for pos,p in self._cube.cubies.items() if pos in self._recorded and pos!=self._pos}
            options=equivalent_pieces(self._cube,home,frame,self._pos)
            home,frame=next(((h,f) for h,f in options if h not in used),(home,frame))
        return super().choose_piece(home,frame)

    def check(self):
        if self._cube.n == 4:
            if self._recorded != set(self._cube.positions):
                self.hint.text=tr('morphix.error.incomplete',total=len(self._cube.positions))
                return None
            from cube.high_shape import normalize_high_shape_input
            try:
                result=normalize_high_shape_input(self._cube)
                self.hint.text=tr('poly.valid')
                return result
            except ValueError as exc:
                self.hint.text=tr(str(exc))
                return None
        if self._cube.puzzle_kind=='football':
            if len(self._recorded)!=8:
                self.hint.text=tr('morphix.error.incomplete',total=8)
                return None
            from cube.shape_cube import normalize_football
            try:
                return normalize_football(self._cube)
            except ValueError as exc:
                self.hint.text=tr(str(exc))
                return None
        cube=super().check()
        if cube is None:
            return None
        if len({p.home for p in cube.cubies.values()})!=len(cube.positions):
            self.hint.text=tr('shape.error.duplicate')
            return None
        return cube
