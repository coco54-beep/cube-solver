"""Actual entry, palette, turn and playback routes at phone/desktop sizes."""
import json,os,sys,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.application import CubeApp
from cube.dial_beans import KINDS,goal
from solver.dial_beans import solve
from cube.polyhedral_scramble import scramble

OUT=Path('reports/expansion/2026-10-26/time-beans/visible');OUT.mkdir(parents=True,exist_ok=True)


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.rows=[];self.index=0
        self.cases=[(kind,size) for size in ((800,600),(390,844)) for kind in KINDS]
        Clock.schedule_once(self.next,.1)

    def next(self,*_):
        if self.index>=len(self.cases):self.stop();return
        kind,size=self.cases[self.index];self.index+=1;self.kind=kind;self.size_case=size
        self.bean_stage=0
        Window.size=size;self.root.current='HomeScreen'
        family='circle_family' if kind=='time_machine' else 'round_family'
        self.root.get_screen('HomeScreen').select_order(SimpleNamespace(dismiss=lambda:None),family,kind)
        Clock.schedule_once(self.entered,.15)

    def entered(self,*_):
        try:
            entry=self.root.current_screen;cube=self.cube;assert entry.name=='PolyhedralScreen' and cube.puzzle_kind==self.kind
            assert all(v==-1 for v in cube.colors)
            self.entry=entry
            if self.kind=='time_machine':
                assert len(entry._swatches)==6 and len(entry._number_buttons)==12
                entry.choose_color(2)
                assert len(entry.palette2.children)==6
                assert len(entry._extra_palette_rows[0].children)==6
                assert len(entry.navigation.children)==3
                entry._number_buttons[7].dispatch('on_release');entry.paint(24)
                assert cube.colors[24]==31 and entry._dial_number==8
                entry.undo();assert cube.colors[24]==-1 and entry._dial_number==7
                entry.paint(0);assert cube.colors[0]==74
                assert len(entry.palette_colors())==6
            else:
                entry.choose_color(2);entry.paint(0);entry.paint(1);assert cube.colors[:2]==[2,2]
            cube.colors=list(goal(self.kind));entry._refresh();assert entry.validate()
            Clock.schedule_once(self.entry_shot,.15)
        except Exception:self.fail()

    def entry_shot(self,*_):
        try:
            entry=self.entry;cube=self.cube
            if self.kind=='time_machine':
                entry.view._draw()
                labels=[v for v in entry.view._number_labels.values() if v.opacity]
                if len(labels)<12 or any(not v.texture or not v.texture_size[0] for v in labels):
                    self._label_wait=getattr(self,'_label_wait',0)+1
                    assert self._label_wait<100,'Number labels did not finish rendering'
                    Clock.schedule_once(self.entry_shot,.05);return
                self._label_wait=0
            assert entry.palette.opacity and entry.palette.height>0 and entry.palette.children
            assert all(button.width>0 and button.height>0 for button in entry._swatches)
            entry.export_to_png(str(OUT/f'{self.kind}-{self.size_case[0]}-entry.png'))
            if self.kind=='time_machine' and self.size_case[0]==390:
                action_row=entry.entry_action_buttons['solve'].parent
                assert action_row.width>300
                preview=OUT.parent.parent/'unified-dial-ui'/'actions.png'
                preview.parent.mkdir(parents=True,exist_ok=True)
                action_row.export_to_png(str(preview))
            if self.kind!='time_machine':
                entry.view.animate_whole_turn=lambda axis,angle,duration,on_done:on_done()
                entry.change_view(1);assert entry._face==5
                entry.change_view(-1);assert entry._face==2
            entry.open_twist();assert self.root.current=='PolyhedralTwistScreen'
            twist=self.root.current_screen;self.twist=twist
            assert len(twist.axis.values)==len(cube.geometry.spec.axes)
            if self.kind!='time_machine':
                from cube.dial_beans import petals
                twist.axis.text=twist.axis.values[3*petals(self.kind)]
            self.before=tuple(cube.colors);twist.turn(1)
            Clock.schedule_once(self.turned,.8)
        except Exception:self.fail()

    def turned(self,*_):
        try:
            assert tuple(self.cube.colors)!=self.before
            if self.kind!='time_machine':
                half=len(self.before)//2
                if self.bean_stage==0:
                    assert tuple(self.cube.colors[half:])==self.before[half:]
                    self.bean_stage=1;self.twist.change_view(1)
                    Clock.schedule_once(self.turn_back,.65);return
                assert tuple(self.cube.colors[:half])==self.before[:half]
            self.twist.export_to_png(str(OUT/f'{self.kind}-{self.size_case[0]}-twist.png'))
            self.root.current='PolyhedralScreen';self.cube.colors=list(goal(self.kind))
            scramble(self.cube,30,20261112);self.source_colours=tuple(self.cube.colors)
            self.entry.solve();assert self.root.current=='SolvingScreen'
            self.await_solution(0)
        except Exception:self.fail()

    def turn_back(self,*_):
        try:
            from cube.dial_beans import petals
            assert self.twist._axis==3*petals(self.kind)+1
            self.before=tuple(self.cube.colors);self.twist.turn(1)
            Clock.schedule_once(self.turned,.8)
        except Exception:self.fail()

    def await_solution(self,attempt):
        try:
            if self.root.current=='SolvingScreen':
                assert attempt<1000;Clock.schedule_once(lambda _:self.await_solution(attempt+1),.03);return
            assert self.root.current=='PolyhedralPlaybackScreen'
            assert tuple(self.cube.colors)==self.source_colours
            Clock.schedule_once(self.playback,.15)
        except Exception:self.fail()

    def playback(self,*_):
        try:
            playback=self.root.current_screen;playback.seek(len(playback._moves))
            self._await_playback(0)
        except Exception:self.fail()

    def _await_playback(self,attempt):
        try:
            playback=self.root.current_screen
            if playback._seek_job is not None:
                assert attempt<200;Clock.schedule_once(lambda _:self._await_playback(attempt+1),.03);return
            assert playback._work.is_solved()
            playback.export_to_png(str(OUT/f'{self.kind}-{self.size_case[0]}-solved.png'))
            self.rows.append(dict(kind=self.kind,size=self.size_case,passed=True,moves=len(playback._moves)))
            (OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf8')
            self.root.current='HomeScreen';Clock.schedule_once(self.next,.1)
        except Exception:self.fail()

    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.size_case,passed=False,error=traceback.format_exc()))
        (OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf8');self.stop()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=6 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
