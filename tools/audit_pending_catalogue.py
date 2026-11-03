"""Open all pending cards and search routes in the real shared app menus."""
import os,sys,json,traceback
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
from candidate_puzzles import PENDING_KINDS,catalogue_family
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from ui.widgets.cards import HomeCard
from ui.widgets.buttons import UIButton
from cube.cube3 import Cube3

OUT=Path('reports/expansion/2026-10-29/pending-catalogue')


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.rows=[]
        self.steps=iter([(800,600,kind) for kind in sorted(PENDING_KINDS)]+[(390,844,kind) for kind in sorted(PENDING_KINDS)])
        self.new_cube(3);self.cube.apply_moves(('R','U'));self.source=self.cube;self.before=tuple(self.cube.colors) if hasattr(self.cube,'colors') else repr(self.cube.cubies)
        Clock.schedule_once(self.next,.1)

    def next(self,*_):
        try:self.width,self.height,self.kind=next(self.steps)
        except StopIteration:self.stop();return
        try:
            Window.size=(self.width,self.height);self.root.current='HomeScreen';self.home=self.root.current_screen
            self.home._open_series(catalogue_family(self.kind));Clock.schedule_once(self.pick,.1)
        except Exception:self.fail()

    def pick(self,*_):
        try:
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open)
            card=next(w for w in popup.content.walk() if isinstance(w,HomeCard) and getattr(w,'puzzle_kind',None)==self.kind)
            assert card.pending_label.text==tr('expanded.pending_short')
            scroll=next(w for w in popup.content.walk() if isinstance(w,ScrollView));scroll.scroll_to(card,padding=10,animate=False)
            self.picker,self.card,self.scroll=popup,card,scroll
            Clock.schedule_once(self.pick_visible,.12)
        except Exception:self.fail()

    def pick_visible(self,*_):
        try:
            popup,card,scroll=self.picker,self.card,self.scroll
            window=card.to_window(*card.center)
            assert scroll.collide_point(*scroll.parent.to_widget(*window))
            assert 0<window[0]<Window.width and 0<window[1]<Window.height
            if self.kind=='lanlan_sunflower':popup.export_to_png(str(OUT/f'edge-picker-{self.width}.png'))
            touch=SimpleNamespace(pos=card.center)
            assert card.on_touch_down(touch) and card.on_touch_up(touch)
            Clock.schedule_once(self.reference,.12)
        except Exception:self.fail()

    def reference(self,*_):
        try:
            popup=self.home._pending_popup
            assert popup.reference_kind==self.kind and popup._is_open
            assert self.cube is self.source and self.root.current=='HomeScreen'
            now=tuple(self.cube.colors) if hasattr(self.cube,'colors') else repr(self.cube.cubies)
            assert now==self.before
            if self.kind=='lanlan_sunflower':popup.export_to_png(str(OUT/f'reference-{self.width}.png'))
            popup.dismiss()
            assert self.picker._is_open
            self.picker.dismiss()
            self.home.open_search()
            edit=next(w for w in self.home._search_popup.content.walk() if isinstance(w,TextInput))
            edit.text=tr('directory.'+self.kind)
            Clock.schedule_once(self.search_pick,.08)
        except Exception:self.fail()

    def search_pick(self,*_):
        try:
            popup=self.home._search_popup
            matches=[w for w in popup.content.walk() if isinstance(w,UIButton)
                     and tr('directory.'+self.kind) in w.text and tr('expanded.pending_short') in w.text]
            assert len(matches)==1
            matches[0].dispatch('on_release')
            assert self.home._pending_popup.reference_kind==self.kind and self.cube is self.source
            self.home._pending_popup.dismiss();self.rows.append(dict(kind=self.kind,size=[self.width,self.height],passed=True,input_preserved=True))
            Clock.schedule_once(self.next,.05)
        except Exception:self.fail()

    def fail(self):
        self.rows.append(dict(kind=getattr(self,'kind',''),passed=False,error=traceback.format_exc()));self.stop()

    def on_stop(self):
        OUT.mkdir(parents=True,exist_ok=True);(OUT/'ui-results.json').write_text(json.dumps(self.rows,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);a=Audit();a.run()
    if len(a.rows)!=2*len(PENDING_KINDS) or not all(r['passed'] for r in a.rows):raise SystemExit(1)
