"""Event-driven ownership of input tasks, independent of button layouts."""
from contextlib import contextmanager
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ObjectProperty, OptionProperty


class EntryTaskState(EventDispatcher):
    phase=OptionProperty('idle',options=('idle','working','scrambling','matching','preparing','solving'))
    token=ObjectProperty(None,allownone=True)
    active=BooleanProperty(True)
    locked=BooleanProperty(False)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.requested_phase='working'
        self.bind(token=self._update,active=self._update)

    def _update(self,*_):self.locked=not self.active or self.token is not None

    def begin(self,phase='working',token=None):
        token=object() if token is None else token
        self.phase=phase;self.token=token
        return token

    def finish(self,token):
        if token is None or self.token is not token:return False
        self.phase='idle';self.token=None
        return True

    def cancel(self):
        self.phase='idle';self.token=None

    @contextmanager
    def requesting(self,phase):
        previous=self.requested_phase;self.requested_phase=phase
        try:yield
        finally:self.requested_phase=previous


def lock_controls(state,widget):
    """Parent locking preserves each child's own undo/redo/selection flags."""
    import weakref
    reference=weakref.ref(widget)
    def update(_state,locked):
        control=reference()
        if control is not None:control.disabled=locked
    uid=state.fbind('locked',update)
    weakref.finalize(widget,state.unbind_uid,'locked',uid)
    update(state,state.locked)
