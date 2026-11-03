"""Exercise actual entry books, teaching models, next/back and route links."""
import os,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1');os.environ.setdefault('KIVY_NO_FILELOG','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.application import CubeApp
from candidate_puzzles import REQUESTED
from demo.expanded_support import entry_screen,make_cube,view_class
from demo.expanded_tutorials import lessons
from demo.solutions import state_signature
import ui.screens.demo_screen as ds

OUT=Path('reports/demo-audit/2026-10-24/ui')


def finish(screen,dt=100):
    if getattr(screen.view,'_anim',None) is not None:
        screen.view._anim_event.cancel();screen.view._anim_tick(dt)
    else:
        event=screen.view._event
        event.cancel();event.callback(dt)


def frames():
    for _ in range(5):EventLoop.idle()


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    app=CubeApp();app.simple_input=False;app.theme.apply(False)
    manager=app.root=app.build();manager.transition=NoTransition()
    Window.size=(800,600);Window.add_widget(manager);EventLoop.start();frames()
    ds.follow_turn=lambda _view,_target,begin:begin()
    screen=manager.get_screen('DemoScreen');menu=manager.get_screen('DemoMenuScreen')
    captures={'trajber','container','blanker','mirror_megaminx','l_cube','professor_pentagonal','rubik_cheese'}
    try:
        for entry in REQUESTED:
            row={'kind':entry.kind}
            try:
                manager.current='HomeScreen';app.cube=make_cube(entry.kind,entry.n)
                app.n=app.cube.n;app.puzzle_kind=entry.kind;app.polyhedral_solution=None
                manager.current=entry_screen(entry.kind);frames();source=manager.current_screen
                before=state_signature(app.cube)
                assert not source.demo_button.disabled
                source.demo_button.dispatch('on_release')
                assert manager.current=='DemoMenuScreen' and menu.mode==(entry.kind,entry.n)
                popup=menu.open_learning_route();assert menu.chapter_play_button
                old=menu.chapter_play_button;menu.chapter_next.dispatch('on_release');old.dispatch('on_release')
                assert manager.current==menu.name
                frames();popup.dismiss(animation=False)
                count=0
                for si,step in enumerate(lessons(entry.kind,entry.n)):
                    for ci,case in enumerate(step['cases']):
                        screen.enter_case((entry.kind,entry.n),si,ci);manager.current=screen.name
                        assert type(screen.view) is view_class(entry.kind)
                        snapshots=[state_signature(screen._work)]
                        expected=screen._work.clone()
                        for move in screen._moves:
                            expected.apply_move(move);screen.next_move();finish(screen)
                            assert not screen._busy and state_signature(screen._work)==state_signature(expected)
                            snapshots.append(state_signature(expected))
                        assert screen._work.is_solved()
                        for target in range(len(snapshots)-2,-1,-1):
                            screen.prev_move();finish(screen)
                            assert state_signature(screen._work)==snapshots[target]
                        screen.next_move();finish(screen,.05);screen._stop()
                        assert state_signature(screen._work)==snapshots[0]
                        count+=1
                assert state_signature(app.cube)==before
                if entry.kind in captures:
                    groups=lessons(entry.kind,entry.n)
                    selected=next(((si,ci) for si,step in enumerate(groups) for ci,case in enumerate(step['cases']) if case.get('original')),(0,2))
                    screen.enter_case((entry.kind,entry.n),*selected);frames()
                    manager.export_to_png(str(OUT/(entry.kind+'.png')))
                if entry.kind in ('container','trajber','mirror_megaminx'):
                    Window.size=(400,850);frames()
                    manager.export_to_png(str(OUT/(entry.kind+'-portrait.png')))
                    manager.current=menu.name;frames();popup=menu.open_learning_route();frames()
                    popup.export_to_png(str(OUT/(entry.kind+'-original-portrait.png')))
                    popup.dismiss(animation=False);Window.size=(800,600);frames()
                screen._stop();menu.go_home()
                assert manager.current==source.name
                row.update(status='pass',examples=count,input_preserved=True,book=True,route=True,next_prev_cancel=True)
            except Exception:row.update(status='fail',error=traceback.format_exc())
            rows.append(row);(OUT/'controller-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=True),flush=True)
    finally:
        screen._stop();EventLoop.stop()
    return 0 if len(rows)==len(REQUESTED) and all(r['status']=='pass' for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
