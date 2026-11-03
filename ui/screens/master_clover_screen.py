"""Regular double-layer entry, on the same controls as other curved puzzles."""
from app.i18n import tr
from cube.polyhedral import Move
from cube.master_clover_aligned import scrambled,observed_colors
from renderer.master_clover_view import MasterCloverView
from ui.screens.copter_screen import CopterInputScreen,CopterTwistScreen


class MasterCloverInputScreen(CopterInputScreen):
    view_class=MasterCloverView
    entry_twist_screen='MasterCloverTwistScreen'
    make_scrambled=staticmethod(scrambled)

    def _refresh(self):
        super()._refresh()
        self.shape_button.height=0;self.shape_button.opacity=0;self.shape_button.disabled=True

    @staticmethod
    def validate_aligned(cube):
        from solver.master_clover import validate
        validate(observed_colors(cube))


class MasterCloverTwistScreen(CopterTwistScreen):
    entry_screen_name='MasterCloverInputScreen'

    def _set_layers(self):
        self.layer.values=(tr('master_clover.deep'),tr('master_clover.shallow'));self.layer.disabled=False
        if self.layer.text not in self.layer.values:self.layer.text=self.layer.values[0]
        self._layer_selected(self.layer,self.layer.text)

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._layer=widget.values.index(text);self._angle=180.
            self.view.turn_layer=self._layer;self.view.turn_amount=180.

    def turn(self,direction):self.twist(Move(self._axis,self._layer,180.*direction))

    def twist(self,move):
        if self.view._move is not None or self.view.camera_busy:return
        self._layer=move.layer;self.layer.text=self.layer.values[move.layer]
        super().twist(move)
