"""Exercise the real demo controller and capture representative page renders."""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('KIVY_NO_ARGS','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager,NoTransition
from app.application import CubeApp,_KV_PATH
from demo.solutions import state_signature
import ui.screens.demo_screen as ds
from ui.screens.demo_menu import DemoMenuScreen
from ui.screens.irregular_directory_screen import IMPLEMENTED_ORDERS,SPECIAL_PUZZLES


def finish(screen,dt=100):
    if getattr(screen.view,'_anim',None) is not None:
        screen.view._anim_event.cancel()
        screen.view._anim_tick(dt)
    else:
        event=screen.view._event
        event.cancel()
        event.callback(dt)


def main():
    destination=Path('reports/demo-audit/2026-10-12/ui')
    destination.mkdir(parents=True,exist_ok=True)
    app=CubeApp()
    Builder.load_file(_KV_PATH)
    manager=ScreenManager(transition=NoTransition(),size=(800,600))
    app.root=manager
    screen=ds.DemoScreen(name='DemoScreen')
    menu=DemoMenuScreen(name='DemoMenuScreen')
    manager.add_widget(screen);manager.add_widget(menu)
    Window.size=(800,600)
    Window.add_widget(manager)
    EventLoop.start()
    # Run the actual animation completion callbacks without waiting on wall
    # clock camera easing; the camera-follow control itself stays unchanged.
    ds.follow_turn=lambda _v,_t,begin:begin()
    modes=[2,3,4,5]+[(k,max(n for n in ns if n<=5)) for k,ns in IMPLEMENTED_ORDERS.items()]
    modes += [(k,3) for k in SPECIAL_PUZZLES if k not in IMPLEMENTED_ORDERS]
    rows=[]
    for mode in modes:
        steps=ds._steps_for(mode)
        si=len(steps)-1;ci=len(steps[si]['cases'])-1
        screen.enter_case(mode,si,ci)
        initial=state_signature(screen._work)
        expected=screen._work.clone()
        snapshots=[initial]
        for move in screen._moves:
            expected.apply_move(move)
            screen.next_move();finish(screen)
            assert not screen._busy
            assert state_signature(screen._work)==state_signature(expected),(mode,move)
            snapshots.append(state_signature(expected))
        assert screen._work.is_solved(),mode
        for target in range(len(snapshots)-2,-1,-1):
            screen.prev_move();finish(screen)
            assert state_signature(screen._work)==snapshots[target],mode
        screen.next_move();finish(screen,.1);screen._stop()
        assert state_signature(screen._work)==initial,mode
        rows.append({'mode':mode,'moves':len(screen._moves),'next_prev_cancel':'pass'})
    for mode,si,ci,name in [(3,3,2,'three-dot'),(4,3,1,'four-oll'),
                            (('football',5),0,2,'football-hexagon'),
                            (('square1',3),1,0,'square1'),(('mirror_tower',3),0,1,'mirror-tower')]:
        manager.current=screen.name
        screen.enter_case(mode,si,ci)
        for _ in range(6):EventLoop.idle()
        manager.export_to_png(str(destination/(name+'.png')))
    menu.set_mode(3);manager.current=menu.name
    for _ in range(6):EventLoop.idle()
    manager.export_to_png(str(destination/'menu.png'))
    draft=state_signature(app.cube)
    menu.start_complete_demo()
    deadline=time.monotonic()+15
    while menu._job is not None and time.monotonic()<deadline:
        EventLoop.idle()
    assert menu._job is None and manager.current==screen.name
    assert 'initial' in screen._case()
    assert state_signature(app.cube)==draft
    for _ in range(6):EventLoop.idle()
    manager.export_to_png(str(destination/'complete-demo.png'))
    Window.size=(480,800)
    screen.enter_case(3,3,2)
    for _ in range(6):EventLoop.idle()
    manager.export_to_png(str(destination/'portrait-demo.png'))
    (destination/'controller-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'{len(rows)} controller configurations passed; renders in {destination}',flush=True)
    EventLoop.stop()


if __name__=='__main__':main()
