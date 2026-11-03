"""Hidden-window checks of actual entry, phase controls, undo and playback."""
import os,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from kivy.config import Config
Config.set('graphics','window','hidden')
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition
from cube.polyhedral import Move, dot
from cube.articulated_observation import ObservationDraft, centre2, face_world, polygon_key
from time import monotonic
from app.i18n import tr
from solver.tangram_geometry import geometry
from solver.articulated import solve_articulated
OUT=Path('reports/expansion/2026-11-01/tangram-extreme');OUT.mkdir(parents=True,exist_ok=True)


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.rows=[];self.sizes=iter(((800,600),(390,844)))
        Clock.schedule_once(self.next,.1)
    def on_stop(self):pass
    def fail(self):
        self.rows.append(dict(size=self.size,passed=False,error=traceback.format_exc()));self.save();self.stop()
    def save(self):(OUT/'ui-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
    def next(self,*_):
        try:self.size=next(self.sizes)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            self.new_articulated('tangram_extreme');self.root.current='ArticulatedEntryScreen'
            Clock.schedule_once(self.entry,.6)
        except Exception:self.fail()
    def entry(self,*_):
        try:
            s=self.root.current_screen
            self.entry_bounds=dict(view=list(s.view.pos)+list(s.view.size),
                                   scene=list(s._color_layout.scene.pos)+list(s._color_layout.scene.size),
                                   projection=list(s.view._proj[-3:]))
            self.root.current_screen.export_to_png(str(OUT/f'entry-{self.size[0]}.png'))
            self.card_target=max((p for p in ObservationDraft.from_cube(s._cube).views[s._ao_face] if len(p['piece_key'])==3),
                                 key=lambda p:sum(sum(v) for _,poly in p['piece_key'] for v in poly))
            world=face_world((centre2(self.card_target['outline']),),s._ao_face)[0]
            world=s.view.observation_world().transform(*(v*s.view._entry_scale for v in world))
            eye,right,up,factor,cx,cy=s.view._proj
            pos=(s.view.x+cx+dot(world,right)*factor,s.view.y+cy+dot(world,up)*factor)
            class Tap:
                def __init__(self,pos):self.pos=pos
                def grab(self,widget):pass
                def ungrab(self,widget):pass
            touch=Tap(pos);s.view.on_touch_down(touch);s.view.on_touch_up(touch)
            self.card_deadline=monotonic()+12
            Clock.schedule_once(self.card_ready,.1)
        except Exception:self.fail()
    def card_ready(self,*_):
        try:
            s=self.root.current_screen
            if s._job is not None:
                assert monotonic()<self.card_deadline,'Card query timed out'
                Clock.schedule_once(self.card_ready,.1);return
            shapes=s._color_layout.shapes
            group=next(i for i,choices in enumerate(shapes.groups)
                       if any(o.get('piece_key')==self.card_target['piece_key'] for o in choices))
            shapes.change_page(group//shapes.PAGE_SIZE-shapes.page)
            list(reversed(shapes.gallery.children))[group%shapes.PAGE_SIZE].dispatch('on_release')
            for _ in range(len(shapes.groups[group])):
                item=shapes.selected_item()
                if item and item.get('piece_key')==self.card_target['piece_key']:break
                s._color_layout.rotate_button.dispatch('on_release')
            assert {(p['color'],polygon_key(p['preview'])) for view in s._ao_state['views'] for p in view}==set(self.card_target['piece_key'])
            Clock.schedule_once(self.card_loaded,.4)
        except Exception:self.fail()
    def card_loaded(self,*_):
        try:
            s=self.root.current_screen
            assert len({item['color'] for view in s._ao_state['views'] for item in view})==3
            s.export_to_png(str(OUT/f'whole-piece-{self.size[0]}.png'))
            for _ in range(len(s._ao_undo)):s.undo()
            assert not any(s._ao_state['views'])
            self.before=self.cube.frames;self.root.current='PolyhedralTwistScreen'
            Clock.schedule_once(self.turn,.2)
        except Exception:self.fail()
    def turn(self,*_):
        try:
            s=self.root.current_screen
            assert s._extreme_axis_map==(0,1,2,6) and len(s.axis.values)==4
            assert tuple(s.axis.values)==tuple(tr('poly.axis',i=i+1) for i in range(4))
            s._select_control_axis(6);s.layer.text=s.layer.values[1]
            s.turn(1);Clock.schedule_once(self.turned,1.0)
        except Exception:self.fail()
    def turned(self,*_):
        try:
            s=self.root.current_screen
            assert s._extreme_axis_map==(3,4,5,6) and len(s.axis.values)==4
            assert s._cube.frames!=self.before
            s._select_control_axis(3);assert s._axis==3
            s._select_control_axis(6);assert s._axis==6
            s.export_to_png(str(OUT/f'middle-60-{self.size[0]}.png'))
            s.undo();Clock.schedule_once(self.undone,1.0)
        except Exception:self.fail()
    def undone(self,*_):
        try:
            s=self.root.current_screen
            assert s._cube.frames==self.before and s._extreme_axis_map==(0,1,2,6)
            import random
            rng=random.Random(719);model=geometry('tangram_extreme');c=self.cube.clone()
            for _ in range(100):c.frames,_=rng.choice(list(model.children(c.frames)))
            c.colors=c.frames;assert not c.history
            self.entered=c.clone();self.word=solve_articulated(c)
            self.polyhedral_solution=(c,self.word,tuple(s.view.palette))
            self.root.current='PolyhedralPlaybackScreen';Clock.schedule_once(self.play,.2)
        except Exception:self.fail()
    def play(self,*_):
        try:self.root.current_screen.seek(len(self.word));Clock.schedule_once(self.solved,.1)
        except Exception:self.fail()
    def solved(self,*_):
        try:
            s=self.root.current_screen
            if s._seek_job is not None:Clock.schedule_once(self.solved,.1);return
            assert s._work.is_solved()
            s.export_to_png(str(OUT/f'solved-{self.size[0]}.png'))
            s.seek(0);Clock.schedule_once(self.rewound,.1)
        except Exception:self.fail()
    def rewound(self,*_):
        try:
            s=self.root.current_screen
            if s._seek_job is not None:Clock.schedule_once(self.rewound,.1);return
            assert s._work.frames==self.entered.frames
            self.rows.append(dict(size=self.size,passed=True,phase_controls=4,history_free_moves=len(self.word),
                                  entry_bounds=self.entry_bounds,whole_piece_colors=3))
            self.save();Clock.schedule_once(self.next,.1)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
