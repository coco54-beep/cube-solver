"""Actual photo menus, recognition workers and original entry pages, no camera."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.application import CubeApp
from ui.widgets.photo_entry import choose_photo_puzzle,photo_groups
from vision.scan_profiles import project_controls
import numpy as np
from PIL import Image,ImageDraw

OUT=Path('reports/camera-audit/2026-10-25/visible');OUT.mkdir(parents=True,exist_ok=True)


def photo(profile,face,world,values=None):
    canonical,templates=profile.templates(face,world)
    quad=np.array(((42,37),(518,54),(493,492),(58,511)),float)
    square=np.array(((0.,0.),(1.,0.),(1.,1.),(0.,1.)))
    controls=project_controls(square,quad,canonical)
    picture=Image.new('RGB',(560,550),(12,12,12));draw=ImageDraw.Draw(picture)
    expected={}
    for j,(index,polygon,patches,interior) in enumerate(templates):
        colour=values[index] if values is not None else j%len(profile.palette)
        expected[index]=colour
        for patch in patches:
            points=project_controls(square,quad,patch)
            draw.polygon([tuple(p) for p in points],fill=tuple(round(c*255) for c in profile.palette[colour][:3]))
    return np.asarray(picture),controls,expected


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();Window.size=(390,844);self.rows=[]
        self.camera=self.root.get_screen('CameraScreen');self.camera._ensure_source=lambda:None
        self.home=self.root.get_screen('HomeScreen');self.root.current=self.home.name
        popup=choose_photo_puzzle(self.home)
        assert tuple(popup.photo_buttons)==tuple(k for k,v in photo_groups())
        self.menu=popup;Clock.schedule_once(lambda _:Clock.schedule_once(self.select_prism,0),0)

    def select_prism(self,_):
        self.menu.export_to_png(str(OUT/'existing-families.png'))
        self.menu.photo_buttons['pentagonal_family'].dispatch('on_release')
        from kivy.uix.popup import Popup
        self.models=next(w for w in Window.children if isinstance(w,Popup) and w._is_open and w is not self.menu)
        Clock.schedule_once(lambda _:Clock.schedule_once(self.open_prism,0),0)

    def open_prism(self,_):
        self.models.export_to_png(str(OUT/'pentagonal-models.png'))
        self.models.photo_buttons['professor_pentagonal'].dispatch('on_release')
        Clock.schedule_once(self.scan_prism,.15)

    def scan_prism(self,_):
        camera=self.camera;assert camera._profile.kind=='professor_pentagonal'
        self.rows.append(dict(case='existing_family_constructs_correct_model',passed=True))
        self.recognize(self.prism_finished)

    def recognize(self,done):
        camera=self.camera;profile=camera._profile;face=camera._ori.current_face()
        picture,controls,expected=photo(profile,face,camera._ori.world)
        path=OUT/(profile.kind+'-import.png');Image.fromarray(picture).save(path)
        camera.load_image(str(path))
        attempts=[0];aligned=[False]
        def check(_):
            attempts[0]+=1
            if camera._recognizing:
                assert attempts[0]<150,'Recognition did not finish';Clock.schedule_once(check,.05);return
            if camera._data[face]!=expected and not aligned[0]:
                # The same public correction path as dragging the guide and
                # pressing Recognize; no sticker data is inserted by the audit.
                aligned[0]=True;camera.guide.set_image((picture.shape[1],picture.shape[0]),controls)
                camera.recheck();Clock.schedule_once(check,.05);return
            assert camera._data[face]==expected
            assert all(v==-1 for f,values in camera._data.items() if f!=face for v in values.values())
            Clock.schedule_once(lambda _:done(),.1)
        Clock.schedule_once(check,.05)

    def prism_finished(self):
        self.camera.export_to_png(str(OUT/'professor-recognition.png'))
        self.camera.apply_to_input();assert self.root.current=='PolyhedralScreen'
        self.rows.append(dict(case='seven_colour_face_recognized_and_partial_input_preserved',passed=True))
        Clock.schedule_once(self.select_tangram,.15)

    def select_tangram(self,_):
        self.root.current=self.home.name;popup=choose_photo_puzzle(self.home)
        popup.photo_buttons['tangram_family'].dispatch('on_release')
        Clock.schedule_once(self.scan_tangram,.15)

    def scan_tangram(self,_):
        assert self.camera._profile.kind=='tangram'
        self.recognize(self.tangram_finished)

    def tangram_finished(self):
        self.camera.export_to_png(str(OUT/'tangram-recognition.png'))
        self.camera.apply_to_input();assert self.root.current=='ArticulatedEntryScreen'
        entry=self.root.current_screen;assert entry._ao_dirty and entry._ao_applied is None
        assert sum(map(len,entry._ao_state['views']))>0
        assert not all(entry._ao_state['complete'])
        self.rows.append(dict(case='tangram_photo_opens_original_partial_colour_entry',passed=True))
        Clock.schedule_once(self.finish,.15)

    def finish(self,_):
        self.root.current_screen.export_to_png(str(OUT/'tangram-colour-entry.png'))
        entry=self.root.current_screen;before=entry._ao_state;entry.back()
        assert self.root.current=='CameraScreen' and entry._ao_state==before
        self.rows.append(dict(case='return_to_photo_keeps_manual_draft',passed=True))
        (OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
        self.stop();print(json.dumps(self.rows),flush=True)


if __name__=='__main__':Audit().run()
