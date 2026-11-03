"""Keep entry instructions available to help without a permanent text row."""
from kivy.uix.label import Label


class EntryGuidance(Label):
    """Store guidance text; display only explicit inline failure feedback.

    Some entry families also use this label for validation messages. Shared
    show_feedback marks those messages, so hiding guidance cannot hide errors.
    """

    def __init__(self, **kwargs):
        kwargs.update(size_hint_y=None, height=0, opacity=0)
        super().__init__(**kwargs)
        self.bind(text=self._sync_visibility, height=self._sync_visibility,
                  opacity=self._sync_visibility)

    def _sync_visibility(self, *_):
        visible = (getattr(self, '_entry_feedback_text', None) is not None and
                   self.text == self._entry_feedback_text)
        self.opacity = int(visible)
        if not visible:
            self.height = 0
