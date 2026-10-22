"""Thumbnails let their enclosing selection button handle the whole card."""

class PassivePreview:
    def on_touch_down(self,touch):return False
    def on_touch_move(self,touch):return False
    def on_touch_up(self,touch):return False
