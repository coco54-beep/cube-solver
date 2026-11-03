"""Blanker entry selects true two-order corner shapes, not nine face cells."""
from ui.entry_feedback import validation_action
from app.i18n import tr
from cube.blanker import BlankerCube,normalize_entry
from cube.mastermorphix import MorphixInputError
from renderer.blanker_view import BlankerView
from ui.screens.mirror_screen import MirrorScreen
from kivy.uix.label import Label
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets import metrics as m


class BlankerScreen(MirrorScreen):
    cube_class=BlankerCube
    view_class=BlankerView

    @validation_action
    def check(self):
        if len(self._recorded)!=8:
            self.hint.text=tr('morphix.error.incomplete',total=8);return None
        try:return normalize_entry(self._cube)
        except MorphixInputError:
            self.hint.text=tr('mirror.duplicate');return None

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:self.reference_label.text=tr('blanker.hint')

    def open_help(self):
        if not self.entry_can_edit():return
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=10)
        view=self.view_class(size_hint_y=None,height=m.h(210))
        view.set_cube(self.cube_class.solved());content.add_widget(view)
        label=Label(text=tr('blanker.hint'),halign='left',valign='middle')
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size));content.add_widget(label)
        return self._popup(tr('directory.blanker'),content,(.9,.65))

    def open_demo(self):
        from demo.expanded_support import open_tutorial
        return open_tutorial(self)
