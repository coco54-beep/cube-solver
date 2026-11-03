"""Exercise the real shared catalogue, entry, twist and playback screens."""
import os,sys,json,traceback
from time import monotonic
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from kivy.config import Config
Config.set('graphics','window','hidden')
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from app.i18n import tr
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import NoTransition
from ui.widgets.cards import HomeCard
from ui.screens.irregular_directory_screen import picker_label
from cube.polyhedral import PolyhedralPuzzle
BUTTER='--butterflower' in sys.argv
MASTER='--master-clover' in sys.argv
RIGID=BUTTER or MASTER
KIND='lanlan_master_clover' if MASTER else 'lanlan_butterflower' if BUTTER else 'kairis_star_finder'
FAMILY='edge_family' if RIGID else 'football'
ENTRY='MasterCloverInputScreen' if MASTER else 'ButterflowerInputScreen' if BUTTER else 'PolyhedralScreen'
TWIST='MasterCloverTwistScreen' if MASTER else 'ButterflowerTwistScreen' if BUTTER else 'PolyhedralTwistScreen'
if MASTER:
    from cube.master_clover import MasterCloverCube
    from cube.master_clover_aligned import observed_colors
    from solver.master_clover import solve
elif BUTTER:
    from cube.butterflower import ButterflowerCube
    from cube.butterflower_aligned import observed_colors
    from solver.butterflower import solve
else:from solver.star_finder import solve

OUT=Path('reports/expansion/2026-10-29')/('master-clover' if MASTER else 'butterflower' if BUTTER else 'star-finder');OUT.mkdir(parents=True,exist_ok=True)


def paints(cube):return tuple(cube.paints if RIGID else cube.colors)


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.rows=[];self.sizes=iter(((800,600),(390,844)))
        Clock.schedule_once(self.next,.1)

    def on_stop(self):pass # The audit must never overwrite the user's session.

    def next(self,*_):
        try:self.size=next(self.sizes)
        except StopIteration:self.stop();return
        try:
            Window.size=self.size;self.root.current='HomeScreen'
            self.root.current_screen._open_series(FAMILY)
            Clock.schedule_once(self.pick,.2)
        except Exception:self.fail()

    def pick(self,*_):
        try:
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open)
            card=next(w for w in popup.content.walk() if isinstance(w,HomeCard)
                      and w._title.text==picker_label(FAMILY,KIND)[0])
            from kivy.uix.scrollview import ScrollView
            scroll=next(w for w in popup.content.walk() if isinstance(w,ScrollView))
            scroll.scroll_to(card,padding=8,animate=False)
            touch=SimpleNamespace(pos=card.center)
            assert card.on_touch_down(touch) and card.on_touch_up(touch)
            Clock.schedule_once(self.entry,.25)
        except Exception:self.fail()

    def entry(self,*_):
        try:
            assert self.root.current==ENTRY
            s=self.root.current_screen;self.input=s
            assert s._cube.puzzle_kind==KIND and len(s._swatches)==(6 if RIGID else 32)
            assert all(c==-1 for c in paints(s._cube))
            color=2 if RIGID else 7;s.choose_color(color);s.paint(0);s.paint(1)
            assert paints(s._cube)[:2]==(color,color) and s._color==color
            s.undo();assert paints(s._cube)[:2]==(color,-1)
            if BUTTER:assert s.shape_button.height>0 and not s.shape_button.disabled
            if BUTTER:
                snapshot=s._cube.signature();s.open_shape_entry()
                s.rotate_pose(1);assert s._pose_work.signature()!=snapshot
                s._pose_popup.dismiss();assert s._cube.signature()==snapshot
            before=paints(s._cube);s.change_view(1)
            assert s._view_busy
            self.before=before;self.wait_started=monotonic();Clock.schedule_once(self.after_face,.1)
        except Exception:self.fail()

    def after_face(self,*_):
        try:
            s=self.input
            if s._view_busy:
                assert monotonic()-self.wait_started<8
                Clock.schedule_once(self.after_face,.1);return
            assert paints(s._cube)==self.before
            assert not s.panel.disabled and not s.status.disabled
            s.export_to_png(str(OUT/f'entry-{self.size[0]}.png'))
            s.randomize();self.wait_started=monotonic();self.scrambles=1
            Clock.schedule_once(self.shuffled,.05)
        except Exception:self.fail()

    def shuffled(self,*_):
        try:
            s=self.input
            if s._job is not None:
                assert monotonic()-self.wait_started<20
                Clock.schedule_once(self.shuffled,.05);return
            if self.scrambles==1:
                self.scrambles=2;s.randomize();Clock.schedule_once(self.shuffled,.05);return
            assert s.validate() is True
            self.entered=(MasterCloverCube(paints=observed_colors(s._cube)) if MASTER else
                          ButterflowerCube(frames=s._cube.frames,paints=s._cube.paints) if BUTTER else
                          PolyhedralPuzzle(KIND,3,list(s._cube.colors)))
            assert getattr(self.entered,'scramble_history',None) is None
            self.word=solve(self.entered);assert self.word
            s.open_twist();Clock.schedule_once(self.twist,.2)
        except Exception:self.fail()

    def twist(self,*_):
        try:
            assert self.root.current==TWIST
            s=self.root.current_screen;labels=s._axis_labels()
            assert len(labels)==(12 if MASTER else 20)
            if MASTER:
                s._axis=0;s._set_layers();assert s._angle==180. and len(s.layer.values)==2
                s.layer.text=s.layer.values[1];assert s._layer==1 and s.view.turn_layer==1
            elif BUTTER:
                s._axis=0;s._set_layers();assert s._angle==180.
                s.layer.text=s.layer.values[1];assert abs(s._angle-70.5287793655)<1e-7
                s._axis=12;s._set_layers();assert s._angle==120.
            else:assert '13' in labels[0] and '32' in labels[-1]
            s.export_to_png(str(OUT/f'twist-{self.size[0]}.png'))
            if RIGID:
                from cube.polyhedral import Move
                self.turn_before=s._cube.signature()
                self.turn_move=(Move(0,1,180.) if MASTER else
                    next(m for m in s._cube.moves() if m.axis<12 and 0<abs(m.amount)<100 and s._cube.can_apply(m)))
                s.twist(self.turn_move);self.wait_started=monotonic()
                Clock.schedule_once(self.after_turn,.05);return
            self.start_playback()
        except Exception:self.fail()

    def after_turn(self,*_):
        try:
            s=self.root.current_screen
            if s.view._move is not None:
                assert monotonic()-self.wait_started<12
                Clock.schedule_once(self.after_turn,.05);return
            assert s._cube.signature()!=self.turn_before
            from cube.polyhedral import Move
            move=self.turn_move;s.twist(Move(move.axis,move.layer,-move.amount));self.wait_started=monotonic()
            Clock.schedule_once(self.after_reverse,.05)
        except Exception:self.fail()

    def after_reverse(self,*_):
        try:
            s=self.root.current_screen
            if s.view._move is not None:
                assert monotonic()-self.wait_started<12
                Clock.schedule_once(self.after_reverse,.05);return
            assert s._cube.signature()==self.turn_before
            self.start_playback()
        except Exception:self.fail()

    def start_playback(self):
        try:
            s=self.root.current_screen
            self.polyhedral_solution=(self.entered,self.word,tuple(s.view.palette))
            self.root.current='PolyhedralPlaybackScreen'
            Clock.schedule_once(self.playback,.2)
        except Exception:self.fail()

    def playback(self,*_):
        try:
            self.root.current_screen.seek(len(self.word));self.wait_started=monotonic()
            Clock.schedule_once(self.solved,.05)
        except Exception:self.fail()

    def solved(self,*_):
        try:
            s=self.root.current_screen
            if s._seek_job is not None:
                assert monotonic()-self.wait_started<20
                Clock.schedule_once(self.solved,.05);return
            assert s._work.is_solved()
            s.export_to_png(str(OUT/f'solved-{self.size[0]}.png'))
            s.seek(0);Clock.schedule_once(self.rewound,.05)
        except Exception:self.fail()

    def rewound(self,*_):
        try:
            s=self.root.current_screen
            if s._seek_job is not None:
                assert monotonic()-self.wait_started<20
                Clock.schedule_once(self.rewound,.05);return
            assert paints(s._work)==paints(self.entered)
            self.rows.append(dict(size=self.size,passed=True,continuous_paint=True,undo=True,
                animated_face_switch=True,double_scramble=True,validation=True,
                manual_reentry=True,twist_axes=12 if MASTER else 20,playback_moves=len(self.word),rewind=True))
            self.save();Clock.schedule_once(self.next,.1)
        except Exception:self.fail()

    def save(self):(OUT/'ui-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf8')
    def fail(self):
        self.rows.append(dict(size=self.size,passed=False,error=traceback.format_exc()));self.save();self.stop()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
