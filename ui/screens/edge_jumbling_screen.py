from functools import partial
from ui.screens.copter_screen import CopterInputScreen,CopterTwistScreen,_app
from cube.edge_jumbling import scrambled
from renderer.edge_jumbling_view import EdgeJumblingView


class EdgeJumblingInputScreen(CopterInputScreen):
    view_class=EdgeJumblingView
    entry_twist_screen='EdgeJumblingTwistScreen'

    def on_pre_enter(self,*args):
        self.make_scrambled=partial(scrambled,_app().cube.puzzle_kind)
        super().on_pre_enter(*args)

    @staticmethod
    def validate_aligned(cube):
        if cube.puzzle_kind=='helicopter_14':
            from solver.helicopter_14 import validate
            from cube.helicopter_14_aligned import observed_colors
            validate(observed_colors(cube));return
        from solver.expanded_polyhedra import validate_expanded
        if cube.puzzle_kind=='rua':validate_expanded(cube.regular_colours())


class EdgeJumblingTwistScreen(CopterTwistScreen):
    entry_screen_name='EdgeJumblingInputScreen'

    def _set_layers(self):
        if self._cube.puzzle_kind!='mf8_bauhinia_minx':return super()._set_layers()
        from cube.spherical_jumbling import BAU_JUMBLE
        self._angles=(120.,BAU_JUMBLE,120.-BAU_JUMBLE)
        self.layer.values=tuple(f'{a:g}°' for a in self._angles);self.layer.disabled=False;self._layer=0
        self.layer.text=self.layer.values[0];self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if getattr(self,'_cube',None) is not None and self._cube.puzzle_kind=='mf8_bauhinia_minx':
            if text in widget.values:self._angle=self._angles[widget.values.index(text)];self.view.turn_amount=self._angle
        else:super()._layer_selected(widget,text)
