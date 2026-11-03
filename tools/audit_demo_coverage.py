"""Audit every newly covered book and real playback controller."""
import os,sys,json,traceback,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.application import CubeApp
from demo.coverage import modes,make_cube,view_class,entry_screen,lessons,complete_lessons
from demo.solutions import state_signature
import ui.screens.demo_screen as ds

OUT=Path('reports/demo-coverage/2026-10-24/ui')

def finish(screen,dt=100):
    view=screen.view
    if getattr(view,'_anim',None) is not None:
        view._anim_event.cancel();view._anim_tick(dt)
    else:
        event=view._event;event.cancel();event.callback(dt)

def frames():
    for _ in range(3):EventLoop.idle()

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--kinds',nargs='*');args=parser.parse_args()
    if args.kinds:OUT=OUT.parent/'ui-recheck'
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    app=CubeApp();app.simple_input=False;app.theme.apply(False)
    manager=app.root=app.build();manager.transition=NoTransition()
    Window.size=(800,600);Window.add_widget(manager);EventLoop.start();frames()
    ds.follow_turn=lambda _view,_target,begin:begin()
    demo=manager.get_screen('DemoScreen');menu=manager.get_screen('DemoMenuScreen')
    captures={('mixup_plus_444',4),('pentacle',3),('ghost',1),('ghost',3),
              ('mirror_pyraminx',4),('circle_2',2),('cube',6),('ancient_coin',3)}
    try:
        for kind,n in modes():
            if args.kinds and kind not in args.kinds:continue
            row={'kind':kind,'n':n}
            try:
                manager.current='HomeScreen';frames()
                app.cube=make_cube(kind,n);app.n=app.cube.n;app.puzzle_kind=kind
                app.facelets_input=None;app.facelets_cache={};app.polyhedral_solution=None
                app.selection_series=None
                source_name=entry_screen(kind,n)
                manager.current=source_name;frames();source=manager.current_screen
                before=state_signature(app.cube)
                button=getattr(source,'demo_button',None) or getattr(source,'btn_demo',None)
                assert button is not None and not button.disabled,(kind,n,'book disabled')
                button.dispatch('on_release')
                mode=n if kind=='cube' else (kind,app.cube.n)
                assert manager.current=='DemoMenuScreen' and menu.mode==mode,(kind,n,menu.mode,manager.current)
                if (kind,n) in captures:
                    Window.size=(400,850);frames()
                    manager.export_to_png(str(OUT/f'menu-{kind}-{n}.png'))
                    Window.size=(800,600);frames()
                count=0
                groups=lessons(kind,n)+complete_lessons(kind,n)
                for si,step in enumerate(groups):
                    for ci,case in enumerate(step['cases']):
                        demo.enter_case(mode,si,ci,groups);manager.current=demo.name
                        assert type(demo.view) is view_class(demo._work)
                        snapshots=[state_signature(demo._work)];expected=demo._work.clone()
                        for move in demo._moves:
                            expected.apply_move(move);demo.next_move();finish(demo)
                            assert not demo._busy and state_signature(demo._work)==state_signature(expected),(kind,n,move)
                            snapshots.append(state_signature(expected))
                        assert demo._work.is_solved(),(kind,n,'not solved')
                        for target in range(len(snapshots)-2,-1,-1):
                            demo.prev_move();finish(demo)
                            assert state_signature(demo._work)==snapshots[target],(kind,n,'reverse')
                        demo.next_move();finish(demo,.05);demo._stop()
                        assert state_signature(demo._work)==snapshots[0]
                        count+=1
                assert state_signature(app.cube)==before,(kind,n,'input modified')
                demo._stop();manager.current=menu.name;menu.go_home();frames()
                assert manager.current==source_name,(kind,n,'wrong return')
                if (kind,n) in captures:
                    demo.enter_case(mode,2,0,groups);manager.current=demo.name;Window.size=(400,850);frames()
                    manager.export_to_png(str(OUT/f'{kind}-{n}.png'));Window.size=(800,600);frames()
                    demo.enter_case(mode,3,0,groups);Window.size=(400,850);frames()
                    manager.export_to_png(str(OUT/f'complete-{kind}-{n}.png'));Window.size=(800,600);frames()
                row.update(status='pass',cases=count,next_prev_stop=True,book=True,input_preserved=True)
            except Exception:row.update(status='fail',error=traceback.format_exc())
            rows.append(row);(OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
            print(json.dumps(row),flush=True)
    finally:
        demo._stop();EventLoop.stop()
    return int(any(row['status']!='pass' for row in rows))

if __name__=='__main__':raise SystemExit(main())
