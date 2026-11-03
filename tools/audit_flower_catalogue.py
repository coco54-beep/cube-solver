"""Open the visible family popup and search, then click the Flower card."""
import sys,os,json,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from app.i18n import tr,set_language
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import NoTransition
from ui.widgets.cards import HomeCard
from ui.widgets.buttons import UIButton
from ui.screens.irregular_directory_screen import picker_orders

OUT=Path('reports/expansion/2026-10-29/flower-copter/catalogue');OUT.mkdir(parents=True,exist_ok=True)


class Audit(CubeApp):
    def on_start(self):
        # Do not load or overwrite the user's session for this audit.
        set_language('zh');self.root.transition=NoTransition();self.rows=[];self.index=0
        Clock.schedule_once(self.next,.1)

    def next(self,*_):
        if self.index==2:self.stop();return
        self.viewport=((800,600),(390,844))[self.index];self.index+=1
        try:
            Window.size=self.viewport;self.root.current='HomeScreen'
            self.home=self.root.current_screen
            self.home._buttons['edge_family']._on_click()
            Clock.schedule_once(self.check_picker,.35)
        except Exception:self.fail()

    def check_picker(self,*_):
        try:
            self.popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open
                            and w.title==tr('directory.edge_family'))
            cards=[w for w in self.popup.content.walk() if isinstance(w,HomeCard)]
            assert len(cards)==len(picker_orders('edge_family'))
            card=next(w for w in cards if w._title.text==tr('directory.lanlan_flower_copter'))
            assert card.top<self.popup.top and card.y>self.popup.y
            self.popup.export_to_png(str(OUT/f'picker-{self.viewport[0]}.png'))
            touch=SimpleNamespace(pos=card.center)
            assert card.on_touch_down(touch) and card.on_touch_up(touch)
            Clock.schedule_once(self.check_entry,.25)
        except Exception:self.fail()

    def check_entry(self,*_):
        try:
            assert self.root.current=='FlowerCopterInputScreen' and self.puzzle_kind=='lanlan_flower_copter'
            self.root.current='HomeScreen';self.home.open_search()
            popup=self.home._search_popup
            edit=next(w for w in popup.content.walk() if isinstance(w,TextInput));edit.text='花瓣'
            Clock.schedule_once(self.check_search,.2)
        except Exception:self.fail()

    def check_search(self,*_):
        try:
            popup=self.home._search_popup
            matches=[w for w in popup.content.walk() if isinstance(w,UIButton)
                     and tr('directory.lanlan_flower_copter') in w.text]
            assert len(matches)==1
            matches[0].dispatch('on_release')
            assert self.root.current=='FlowerCopterInputScreen' and self.puzzle_kind=='lanlan_flower_copter'
            self.rows.append(dict(size=self.viewport,passed=True,visible_cards=len(picker_orders('edge_family')),card_click=True,search_click=True))
            self.save();Clock.schedule_once(self.next,.2)
        except Exception:self.fail()

    def save(self):(OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
    def fail(self):
        self.rows.append(dict(size=self.viewport,passed=False,error=traceback.format_exc()));self.save();self.stop()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
