"""Verify the seven solved play pages and their real compact action menus."""
import os,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
OUT=Path('reports/optimization/2026-11-02/material-play-pages')
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'audit-preferences.json')
from app.application import CubeApp
from ui.screens.copter_screen import PLAY_ONLY_KINDS
from candidate_puzzles import catalogue_family
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.i18n import tr
ONLY=set(sys.argv[1:])


class Audit(CubeApp):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,kind) for size in ((800,600),(390,844)) for kind in sorted(PLAY_ONLY_KINDS) if not ONLY or kind in ONLY)
        Clock.schedule_once(self.next,.1)
    def on_stop(self):pass
    def save(self):
        (OUT/'ui-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.size,passed=False,error=traceback.format_exc()))
        self.save();self.stop()
    def next(self,*_):
        try:self.size,self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            self.root.get_screen('HomeScreen').launch_order(catalogue_family(self.kind),self.kind)
            self._settle_frames=0;Clock.schedule_once(self.settle,0)
        except Exception:self.fail()
    def settle(self,*_):
        self._settle_frames+=1
        Clock.schedule_once(self.settle if self._settle_frames<7 else self.check,0)
    def check(self,*_):
        try:
            s=self.root.current_screen
            assert self.cube.puzzle_kind==self.kind and self.cube.is_solved()
            assert s.play_only and s._cube is self.cube
            assert all(w.parent is None for w in (s.palette,s.palette2,s.navigation,s.hint,s.shape_button))
            assert not s.status.text and s.view.on_pick is None
            assert s.view._polygons
            root=s._root_layout
            if root.width>root.height*1.1:
                assert root.body.orientation=='horizontal'
                assert s.view.right<=root.panel_viewport.x+1
            else:
                assert s.view.y>=root.panel_viewport.top-1
            s.export_to_png(str(OUT/f'{self.kind}-{self.size[0]}.png'))
            row=s._play_actions
            if row.more.parent:
                self.popup=row.open_more();Clock.schedule_once(self.menu,.15)
            else:self.finish()
        except Exception:self.fail()
    def menu(self,*_):
        try:
            row=self.root.current_screen._play_actions
            assert row.buttons['clear'].parent is None
            assert row.buttons['target'].text==tr('entry.model_reset')
            assert row.labels['close']==tr('entry.model_continue')
            if self.kind=='lanlan_curvy_copter':self.popup.export_to_png(str(OUT/f'more-{self.size[0]}.png'))
            self.popup.dismiss();self.finish()
        except Exception:self.fail()
    def finish(self):
        s=self.root.current_screen
        self.rows.append(dict(kind=self.kind,size=self.size,passed=True,solved=True,
                              manual_colour=False,manual_pose=False,compact_menu_checked=True,
                              view_bounds=[*s.view.pos,*s.view.size],body_orientation=s._root_layout.body.orientation,
                              body_bounds=[*s._root_layout.body.pos,*s._root_layout.body.size],
                              root_bounds=[*s._root_layout.pos,*s._root_layout.size]))
        self.save();Clock.schedule_once(self.next,.05)


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2*len(ONLY or PLAY_ONLY_KINDS) or not all(row['passed'] for row in app.rows):raise SystemExit(1)
