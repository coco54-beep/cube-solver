from types import SimpleNamespace

import pytest

pytest.importorskip('kivy')


@pytest.mark.parametrize('transition_active',[False,True])
def test_resume_refresh_crosses_frame_boundary_and_preserves_canvas_order(monkeypatch,transition_active):
    from app.application import CubeApp
    from kivy.clock import Clock
    import kivy.core.window
    class Canvas:
        def __init__(self,children=()):
            self.children=list(children); self.removed=0; self.updated=0
        def remove(self,item): self.children.remove(item); self.removed+=1
        def insert(self,index,item): self.children.insert(index,item)
        def ask_update(self): self.updated+=1
    screen=SimpleNamespace(canvas=Canvas())
    before,after=object(),object()
    root=SimpleNamespace(current_screen=screen,transition=SimpleNamespace(is_active=transition_active),
        canvas=Canvas((before,screen.canvas,after)),has_screen=lambda name:False)
    window=SimpleNamespace(canvas=Canvas())
    monkeypatch.setattr(kivy.core.window,'Window',window)
    pending=[]
    monkeypatch.setattr(Clock,'schedule_once',lambda callback,delay:pending.append((callback,delay)))
    app=SimpleNamespace(root=root,_reset_input_interaction=lambda:None)
    CubeApp.on_resume(app)
    pending.pop(0)[0](.3)
    assert root.canvas.removed==0 and root.canvas.updated==0
    callback,delay=pending.pop(0)
    assert delay==0
    callback(0)
    assert root.canvas.children==[before,screen.canvas,after]
    assert root.canvas.removed==(0 if transition_active else 1)
    assert root.canvas.updated==window.canvas.updated==1
