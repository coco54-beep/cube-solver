"""Exercise production Copter entry, modal editing, turns and full playback.

Generated observations supply measured poses and colours, never a scramble
word. This automates the numeric pose controls; it is not a human usability or
physical-unit comparison test.
"""
import os,sys,json,math,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from kivy.uix.popup import Popup
from app.i18n import tr
COMET='--comet' in sys.argv
PHYSICAL='--physical' in sys.argv
TWINS='--twins' in sys.argv
SUN='--sun' in sys.argv
PISCES='--pisces' in sys.argv
HEXAGRAM='--hexagram' in sys.argv
FLOWER='--flower' in sys.argv
CLOVER='--clover-pyraminx' in sys.argv
if FLOWER:
    from cube.flower_copter_aligned import scrambled,observed_colors
    from cube.flower_copter import FlowerCopterCube as MaterialCube
elif CLOVER:
    from cube.clover_pyraminx_aligned import scrambled,observed_colors
    from cube.clover_pyraminx import CloverPyraminxCube as MaterialCube
elif HEXAGRAM:
    from cube.hexagram_aligned import scrambled,observed_colors
    from cube.hexagram import HexagramCube as MaterialCube
elif PISCES:
    from cube.pisces_aligned import scrambled,observed_colors
    from cube.pisces import PiscesCube as MaterialCube
elif TWINS:
    from cube.twins_aligned import scrambled,observed_colors
    from cube.twins_state import TwinsState as MaterialCube
elif SUN:
    from cube.suncube_aligned import scrambled,observed_colors
    from cube.suncube import SunCube as MaterialCube
elif PHYSICAL:
    from cube.lanlan_comet_aligned import scrambled
elif COMET:
    from cube.crazy_comet import scrambled
else:
    from cube.copter_input import scrambled
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
from candidate_puzzles import catalogue_family

KIND='lanlan_comet_physical' if PHYSICAL else 'planar_rhombic_12' if COMET else 'lanlan_curvy_copter'
ENTRY='LanlanCometInputScreen' if PHYSICAL else 'CometInputScreen' if COMET else 'CopterInputScreen'
TWIST='LanlanCometTwistScreen' if PHYSICAL else 'CometTwistScreen' if COMET else 'CopterTwistScreen'
if TWINS:KIND,ENTRY,TWIST='mf8_twins','TwinsInputScreen','TwinsTwistScreen'
if SUN:KIND,ENTRY,TWIST='mf8_suncube_2','SunCubeInputScreen','SunCubeTwistScreen'
if PISCES:KIND,ENTRY,TWIST='lanlan_pisces','PiscesInputScreen','PiscesTwistScreen'
if HEXAGRAM:KIND,ENTRY,TWIST='lanlan_hexagram','HexagramInputScreen','HexagramTwistScreen'
if FLOWER:KIND,ENTRY,TWIST='lanlan_flower_copter','FlowerCopterInputScreen','FlowerCopterTwistScreen'
if CLOVER:KIND,ENTRY,TWIST='lanlan_clover_pyraminx','CloverPyraminxInputScreen','CloverPyraminxTwistScreen'
OUT=(Path('reports/expansion/2026-10-28/lanlan-comet') if PHYSICAL else
     Path('reports/expansion/2026-10-27')/('crazy-comet' if COMET else 'curvy-copter'))/'visible'
if TWINS:OUT=Path('reports/expansion/2026-10-29/twins-dwg/visible')
if SUN:OUT=Path('reports/expansion/2026-10-28/suncube-ii/visible')
if PISCES:OUT=Path('reports/expansion/2026-10-28/pisces/visible')
if HEXAGRAM:OUT=Path('reports/expansion/2026-10-28/hexagram/visible')
if FLOWER:OUT=Path('reports/expansion/2026-10-29/flower-copter/visible')
if CLOVER:OUT=Path('reports/expansion/2026-10-29/clover-pyraminx/visible')
OUT.mkdir(parents=True,exist_ok=True)


def measured_euler(frame):
    # Rz(z) Ry(y) Rx(x), calculated from the observed matrix, no move log.
    r=tuple(tuple(frame[j][i] for j in range(3)) for i in range(3))
    y=math.atan2(-r[2][0],math.hypot(r[0][0],r[1][0]))
    if abs(math.cos(y))<1e-8:
        x=0.;z=math.atan2(-r[0][1],r[1][1])
    else:x=math.atan2(r[2][1],r[2][2]);z=math.atan2(r[1][0],r[0][0])
    return tuple(math.degrees(v) for v in (x,y,z))


class Audit(CubeApp):
    def build(self):
        root=super().build()
        if CLOVER:
            # The prototype adds neither public cards nor startup widgets.
            from app.application import _screen
            for name in (ENTRY,TWIST):
                screen=_screen(name);screen.name=name;root.add_widget(screen)
        return root

    def on_start(self):
        self.root.transition=NoTransition();self.rows=[];self.index=0
        Clock.schedule_once(self.next,.1)

    def next(self,*args):
        if self.index==2:self.stop();return
        self.viewport=((800,600),(390,844))[self.index];self.index+=1
        try:
            Window.size=self.viewport;self.root.current='HomeScreen'
            if CLOVER:
                # Research workflow only: this prototype failed the photo
                # comparison and deliberately has no public directory card.
                self.new_clover_pyraminx();self.root.current=ENTRY
            elif FLOWER:
                # Include the real picker: a callable direct route alone
                # did not catch the old seven-model menu hiding this card.
                self.root.get_screen('HomeScreen')._open_series(catalogue_family(KIND))
                Clock.schedule_once(self.choose_flower_card,.2);return
            else:
                self.root.get_screen('HomeScreen').select_order(SimpleNamespace(dismiss=lambda:None),
                    catalogue_family(KIND),KIND)
            self.entry=self.root.current_screen;assert self.entry.name==ENTRY
            Clock.schedule_once(self.entry_ready,.3)
        except Exception:self.fail()

    def choose_flower_card(self,*args):
        try:
            from ui.widgets.cards import HomeCard
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open
                       and w.title==tr('directory.edge_family'))
            card=next(w for w in popup.content.walk() if isinstance(w,HomeCard)
                      and w._title.text==tr('directory.lanlan_flower_copter'))
            touch=SimpleNamespace(pos=card.center)
            assert card.on_touch_down(touch) and card.on_touch_up(touch)
            self.entry=self.root.current_screen;assert self.entry.name==ENTRY
            Clock.schedule_once(self.entry_ready,.3)
        except Exception:self.fail()

    def entry_ready(self,*args):
        try:
            e=self.entry;e.view._draw();self.before=e._cube.signature()
            assert e.hint.height==0 and len(e.entry_action_buttons)==6 and len(e._swatches)==e._cube.color_count
            assert not e.validate() and self.root.current==e.name
            assert e._entry_notice['category']=='incomplete' and len(e._entry_notice['locations'])==len(e._cube.panels)
            colour=min(4,e._cube.color_count-1)
            e.choose_color(colour);e.view._draw();clicked=set()
            for triangle,slot in e.view._polygons:
                if slot is None or slot in clicked:continue
                x=sum(p[0] for p in triangle)/len(triangle)+e.view.x
                y=sum(p[1] for p in triangle)/len(triangle)+e.view.y
                if e.view.pick(x,y)!=slot:continue
                touch=SimpleNamespace(pos=(x,y),grab=lambda _:None,ungrab=lambda _:None)
                assert e.view.on_touch_down(touch) and e.view.on_touch_up(touch)
                clicked.add(slot)
                if len(clicked)==2:break
            assert len(clicked)==2 and all(e._cube.paints[i]==colour for i in clicked)
            e.undo();e.undo();assert e._cube.signature()==self.before
            e.open_shape_entry();self.home=e._pose_home;self.edit_initial=e._cube.clone()
            e.rotate_pose(1)
            assert e._cube.signature()==self.edit_initial.signature()
            changed=[i for i,(a,b) in enumerate(zip(e._pose_work.frames,e._cube.frames)) if a!=b]
            assert changed==[self.home] and e._pose_work.paints==e._cube.paints
            e.confirm_pose();assert e._cube.signature()!=self.edit_initial.signature()
            e.undo();assert e._cube.signature()==self.edit_initial.signature()
            e.open_shape_entry();e.rotate_pose(1);e._pose_popup.dismiss()
            assert e._cube.signature()==self.edit_initial.signature()
            # Assemble the observation through the actual pose and paint APIs.
            # On these two new profiles test independently re-entered world
            # colours. Hidden material poses are not observable in a photo;
            # this does not certify human entry of a complex jumbled shape.
            source=(scrambled(20261027,30,jumble=False) if TWINS else
                    MaterialCube(paints=observed_colors(scrambled(20261027,30,jumble=False)))
                    if SUN else scrambled(20261027,30 if PISCES or HEXAGRAM or CLOVER or FLOWER else 24))
            e.open_shape_entry()
            for home,frame in enumerate(source.frames):
                slots=[i for i,p in enumerate(source.panels) if p[0]==home]
                if not slots:continue
                e._pose_pick(slots[0]);e.pose_step.text=e.pose_step.values[-1]
                for axis,angle in zip(('X','Y','Z'),measured_euler(frame)):
                    e.pose_axis.text=axis;e.pose_angle.text=repr(angle);e.rotate_pose(1)
            e.confirm_pose()
            visible={h for h,f,p in source.panels}
            assert max(abs(a-b) for h,(x,y) in enumerate(zip(source.frames,e._cube.frames)) if h in visible
                       for u,v in zip(x,y) for a,b in zip(u,v))<1e-8
            for color in range(e._cube.color_count):
                e.choose_color(color)
                for i,c in enumerate(source.paints):
                    if c==color:e.paint(i)
            assert e._cube.paints==source.paints and e.validate()
            if PISCES or HEXAGRAM or CLOVER:
                snapshot=e._cube.clone();core=next(h for h,s in enumerate(e._cube.geometry.pieces) if len(s)==e._cube.color_count)
                from cube.appearance import ROTATIONS,IDENTITY_FRAME
                e._cube.set_piece_frame(core,next(f for f in ROTATIONS if f!=IDENTITY_FRAME))
                bad_pose=e._cube.signature()
                assert not e.validate() and self.root.current==ENTRY
                assert e._cube.signature()==bad_pose and e._entry_notice['category']=='illegal'
                assert len(e._entry_notice['locations'])==e._cube.color_count
                e._cube.restore(snapshot);assert e.validate()
            self.observation=e._cube.signature()
            e.clear()
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open and w.title==tr('poly.clear'))
            next(w for w in popup.content.walk() if getattr(w,'text',None)==tr('poly.cancel')).dispatch('on_release')
            assert e._cube.signature()==self.observation
            entered_frames=e._cube.frames
            e.clear()
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open and w.title==tr('poly.clear'))
            next(w for w in popup.content.walk() if getattr(w,'text',None)==tr('poly.confirm')).dispatch('on_release')
            assert all(c==-1 for c in e._cube.paints) and e._cube.frames==entered_frames
            e.undo();assert e._cube.signature()==self.observation
            Clock.schedule_once(self.open_turn,.15)
        except Exception:self.fail()

    def open_turn(self,*args):
        try:
            self.entry.export_to_png(str(OUT/f'entry-{self.viewport[0]}.png'))
            self.entry.open_twist();self.twist=self.root.current_screen
            assert self.twist.name==TWIST
            move=next(m for m in self.twist._cube.moves() if self.twist._cube.can_apply(m))
            if FLOWER or TWINS:
                self.twist.axis.text=self.twist.axis.values[12]
                assert self.twist._angle==120. and self.twist.layer.disabled
                move=Move(12,0,120.)
            bad=next((Move(a,0,180.) for a in range(12) if not self.twist._cube.can_apply(Move(a,0,180.))),None)
            if FLOWER or TWINS:bad=Move(12,0,60.)
            if bad is not None:
                before=self.twist._cube.signature();self.twist.twist(bad)
                assert self.twist._cube.signature()==before and not self.twist._history
            self.twist.twist(move);self._turn_waits=0;Clock.schedule_once(self.undo_turn,.1)
        except Exception:self.fail()

    def undo_turn(self,*args):
        try:
            if self.twist.view._move is not None or self.twist.view.camera_busy or self.twist.panel.disabled:
                self._turn_waits+=1;assert self._turn_waits<200
                Clock.schedule_once(self.undo_turn,.05);return
            assert self.twist._cube.signature()!=self.observation
            self.twist.undo();self._turn_waits=0;Clock.schedule_once(self.back,.1)
        except Exception:self.fail()

    def back(self,*args):
        try:
            if self.twist.view._move is not None or self.twist.view.camera_busy or self.twist.panel.disabled:
                self._turn_waits+=1;assert self._turn_waits<200
                Clock.schedule_once(self.back,.05);return
            assert self.twist._cube.signature()==self.observation
            self.twist.back();assert self.root.current==ENTRY
            self.entry.solve();assert self.root.current=='SolvingScreen'
            self.await_solution(0)
        except Exception:self.fail()

    def await_solution(self,attempt):
        try:
            if self.root.current=='SolvingScreen':
                assert attempt<1500;Clock.schedule_once(lambda _:self.await_solution(attempt+1),.04);return
            assert self.root.current=='PolyhedralPlaybackScreen'
            self.playback=self.root.current_screen;self.playback.seek(len(self.playback._moves))
            Clock.schedule_once(self.finished,.4)
        except Exception:self.fail()

    def finished(self,*args):
        try:
            p=self.playback
            if p._seek_job is not None:Clock.schedule_once(self.finished,.1);return
            assert p._work.is_solved() and self.entry._cube.signature()==self.observation
            p.seek(0);Clock.schedule_once(self.rewound,.2)
        except Exception:self.fail()

    def rewound(self,*args):
        try:
            assert not self.playback._work.is_solved()
            assert self.playback._work.signature()==self.observation
            self.playback.seek(len(self.playback._moves));Clock.schedule_once(self.save_finished,.4)
        except Exception:self.fail()

    def save_finished(self,*args):
        try:
            p=self.playback
            if p._seek_job is not None:Clock.schedule_once(self.save_finished,.1);return
            assert p._work.is_solved()
            p._refresh();p.view._draw()
            Clock.schedule_once(self.capture_finished,.2)
        except Exception:self.fail()

    def capture_finished(self,*args):
        try:
            p=self.playback
            assert p._work.is_solved() and p._index==len(p._moves)
            p.export_to_png(str(OUT/f'solved-{self.viewport[0]}.png'))
            self.root.current=ENTRY;self.entry.randomize()
            assert self.entry._job is not None
            Clock.schedule_once(lambda _:self.random_finished(0),.1)
        except Exception:self.fail()

    def random_finished(self,attempt):
        try:
            if self.entry._job is not None:
                assert attempt<250;Clock.schedule_once(lambda _:self.random_finished(attempt+1),.05);return
            assert self.entry._cube.signature()!=self.observation
            self.entry.undo();assert self.entry._cube.signature()==self.observation
            self.entry.randomize();self.entry._cancel_solve()
            Clock.schedule_once(self.cancelled_random,.8)
        except Exception:self.fail()

    def cancelled_random(self,*args):
        try:
            assert self.entry._cube.signature()==self.observation and self.entry.entry_can_edit()
            self.rows.append(dict(size=self.viewport,passed=True,moves=len(self.playback._moves),
                                  randomize_undo=True,cancel_keeps_input=True))
            self.save();Clock.schedule_once(self.next,.1)
        except Exception:self.fail()

    def save(self):(OUT/'results.json').write_text(json.dumps(self.rows,ensure_ascii=False,indent=2),encoding='utf-8')
    def fail(self):
        self.rows.append(dict(size=self.viewport,passed=False,error=traceback.format_exc()));self.save();self.stop()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
