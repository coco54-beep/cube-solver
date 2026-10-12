"""Piece and orientation input for Axis and other three-layer shape mods."""
from app.i18n import tr
from cube.mastermorphix import position_kind
from cube.shape_cube import AxisCube
from renderer.shape_cube_view import AxisView
from ui.screens.mirror_screen import MirrorScreen
from ui.screens.mastermorphix_screen import _app
from app.constants import COLOR_INFO
from ui.widgets import metrics as m


class ShapeCubeScreen(MirrorScreen):
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
        from kivy.uix.colorpicker import ColorPicker
        from ui.widgets.layouts import ResponsiveBoxLayout
        from ui.widgets.buttons import UIButton,PrimaryButton
        picker=ColorPicker(color=COLOR_INFO[self._cube.palette[index]][1])
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        content.add_widget(picker)
        actions=ResponsiveBoxLayout(height_px=44,gap_px=6)
        restore=UIButton(text=tr('poly.restore_colors'))
        done=PrimaryButton(icon_name='done')
        actions.add_widget(restore)
        actions.add_widget(done)
        content.add_widget(actions)
        popup=self._popup(tr('poly.palette'),content,(.9,.85))
        restore.bind(on_release=lambda *_:(self.restore_preset(),popup.dismiss()))
        def accept(*args):
            colors=[COLOR_INFO[c][1] for c in self._cube.palette]
            value=tuple(picker.color[:3])+(1,)
            for other,color in enumerate(colors):
                if other!=index and color[:3]==value[:3]:
                    colors[other]=colors[index]
                    break
            colors[index]=value
            self._apply_shape_colors(colors)
            popup.dismiss()
        done.bind(on_release=accept)

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

    def go_back(self):
        self.manager.current='IrregularDirectoryScreen' if self._cube.puzzle_kind=='football' else 'SpecialIrregularScreen'

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:
            from ui.screens.mastermorphix_screen import _Swatch
            visible=self._cube.puzzle_kind!='football'
            self.palette_row.height=m.h(44) if visible else 0
            self.palette_row._height_px=44 if visible else 0
            self.palette_row.opacity=1 if visible else 0
            self.palette_row.disabled=not visible
            self.palette_row.clear_widgets()
            if visible:
                for i,color in enumerate(self._cube.palette):
                    chip=_Swatch(COLOR_INFO[color][1],text=str(i+1))
                    chip.bind(on_release=lambda *_,slot=i:self.open_color(slot))
                    self.palette_row.add_widget(chip)
            self.demo_button.disabled=self._cube.n>5
            self.demo_button.opacity=0 if self._cube.n>5 else 1
            self.reference_label.text=tr('football.pattern_hint' if self._cube.puzzle_kind=='football' else 'shape.reference')
            self.hint.text=tr('shape.hint')
            if self._cube.puzzle_kind=='pandora' and position_kind(self._pos)=='center':
                # A plain square centre looks identical in all four turns.
                self.rotate.disabled=True
                self.hint.text=tr('shape.pandora_center')
            elif self._cube.puzzle_kind in ('windmill','fisher'):
                self.reference_label.text=tr('shape.'+self._cube.puzzle_kind+'_reference')
                if position_kind(self._pos)=='center' and self._pos[1]:
                    self.rotate.disabled=True
                    self.hint.text=tr('shape.pandora_center')

    def available_homes(self,pos):
        if position_kind(pos)=='center':
            return [pos]
        return super().available_homes(pos)

    def check(self):
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
