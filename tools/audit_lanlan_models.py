"""Exercise native catalogue, entry, turning and playback at two viewport sizes."""
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
from candidate_puzzles import BY_KIND,catalogue_family
from demo.expanded_support import make_cube,scramble,signature
from renderer.mastermorphix_view import cube_view_class_for

KINDS=('rhombic_3','rhombic_4','rhombic_mask_4','caneball_4','skewb_rhombic','jewel_fto','rua','helicopter_14')
OUT=Path('reports/expansion/2026-10-26/lanlan-photos/visible')
OUT.mkdir(parents=True,exist_ok=True)


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.rows=[];self.index=0
        self.cases=[(k,size) for size in ((800,600),(390,844)) for k in KINDS]
        Clock.schedule_once(self.next,.1)

    def next(self,*_):
        if self.index==len(self.cases):self.stop();return
        self.kind,self.viewport=self.cases[self.index];self.index+=1
        try:
            Window.size=self.viewport;self.root.current='HomeScreen'
            self.root.get_screen('HomeScreen').select_order(SimpleNamespace(dismiss=lambda:None),catalogue_family(self.kind),self.kind)
            self.entry=self.root.current_screen
            assert self.entry._cube.puzzle_kind==self.kind
            Clock.schedule_once(self.input,.15)
        except Exception:self.fail()

    def input(self,*_):
        try:
            e=self.entry;self.shape=BY_KIND[self.kind].mechanism=='shape'
            assert e.hint.height==0 and e.hint.opacity==0
            if self.shape:assert e.reference_label.height==0 and e.reference_label.opacity==0
            e.export_to_png(str(OUT/f'{self.kind}-{self.viewport[0]}-blank.png'))
            source=scramble(make_cube(self.kind,BY_KIND[self.kind].n),20261026,30)
            if self.shape:
                assert e.check() is None and self.root.current==e.name
                # Test an actual card and its orientation control first.
                e.choose_piece(e.available_homes(e._pos)[0]);old=signature(e._cube)
                for _ in range(len(e._placements(e._cube.cubies[e._pos].home,e._pos))):e.rotate_piece()
                assert signature(e._cube)==old
                e._cube=source.clone();e._recorded=set(source.positions);e._history=[];e._refresh()
                assert e.check() is not None
            else:
                assert not e.validate() and self.root.current==e.name
                # Keep one selected colour while painting consecutive tiles.
                e.choose_color(2);e.paint(0);e.paint(1);assert e._cube.colors[:2]==[2,2]
                e.undo();assert e._cube.colors[1]==-1
                for color in range(source.color_count):
                    e.choose_color(color)
                    for i,c in enumerate(source.colors):
                        if c==color:e.paint(i)
                assert e._cube.colors==source.colors and e.validate()
            self.input_signature=signature(e._cube)
            Clock.schedule_once(self.open_turn,.12)
        except Exception:self.fail()

    def open_turn(self,*_):
        try:
            e=self.entry
            e.export_to_png(str(OUT/f'{self.kind}-{self.viewport[0]}-entry.png'))
            assert len(e.entry_action_buttons)==6
            e.open_twist();self.twist=self.root.current_screen
            assert self.root.current==('MorphixTwistScreen' if self.shape else 'PolyhedralTwistScreen')
            if self.shape:assert isinstance(self.twist.view,cube_view_class_for(e._cube))
            else:assert len(self.twist.axis.values)==len(e._cube.geometry.spec.axes)
            self.twist.turn(1);Clock.schedule_once(self.undo_turn,.8)
        except Exception:self.fail()

    def undo_turn(self,*_):
        try:
            work=self.twist._work if self.shape else self.twist._cube
            assert signature(work)!=self.input_signature
            self.twist.undo();Clock.schedule_once(self.back_to_input,.8)
        except Exception:self.fail()

    def back_to_input(self,*_):
        try:
            work=self.twist._work if self.shape else self.twist._cube
            assert signature(work)==self.input_signature
            self.twist.back();assert self.root.current==self.entry.name
            self.entry.start_solve() if self.shape else self.entry.solve()
            assert self.root.current=='SolvingScreen'
            self.await_solution(0)
        except Exception:self.fail()

    def await_solution(self,attempt):
        try:
            if self.root.current=='SolvingScreen':
                assert attempt<2000;Clock.schedule_once(lambda _:self.await_solution(attempt+1),.03);return
            assert self.root.current==('PlaybackScreen' if self.shape else 'PolyhedralPlaybackScreen'),self.root.current
            Clock.schedule_once(self.playback,.15)
        except Exception:self.fail()

    def playback(self,*_):
        try:
            p=self.root.current_screen
            assert p._work.puzzle_kind==self.kind
            if self.shape:assert isinstance(p.view,cube_view_class_for(p._work))
            p._do_to_end() if self.shape else p.seek(len(p._moves))
            Clock.schedule_once(lambda _:self.solved(0),.15)
        except Exception:self.fail()

    def solved(self,attempt):
        try:
            p=self.root.current_screen
            if not self.shape and p._seek_job is not None:
                assert attempt<500;Clock.schedule_once(lambda _:self.solved(attempt+1),.03);return
            assert p._work.is_solved()
            if self.shape:assert isinstance(p.view,cube_view_class_for(p._work))
            p.export_to_png(str(OUT/f'{self.kind}-{self.viewport[0]}-solved.png'))
            self.rows.append(dict(kind=self.kind,size=self.viewport,passed=True,moves=len(p._moves)))
            self.save();self.root.current='HomeScreen';Clock.schedule_once(self.next,.1)
        except Exception:self.fail()

    def save(self):(OUT/'results.json').write_text(json.dumps(self.rows,ensure_ascii=False,indent=2),encoding='utf-8')
    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.viewport,passed=False,error=traceback.format_exc()))
        self.save();self.stop()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2*len(KINDS) or not all(r['passed'] for r in app.rows):raise SystemExit(1)
