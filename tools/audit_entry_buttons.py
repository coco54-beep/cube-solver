"""Drive actual visible entry buttons through reversible action sequences."""
import json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from app.application import CubeApp
from app.session import encode
from ui.widgets.buttons import DangerButton

OUT=Path('reports/button-audit/2026-10-24')
OUT.mkdir(parents=True,exist_ok=True)


def canonical(value):
    if isinstance(value,list):return [canonical(v) for v in value]
    if not isinstance(value,dict):return value
    value={key:canonical(item) for key,item in value.items()}
    if value.get('@') in ('set','dict'):
        value['v'].sort(key=lambda item:json.dumps(item,sort_keys=True))
    return value


def state(screen):
    if hasattr(screen,'collect_facelets'):
        value=(screen.collect_facelets(),screen._bandage_connections)
    elif screen.name=='MixupInputScreen':value=screen._mx_state
    elif screen.name=='ArticulatedEntryScreen':value=screen._ao_state
    elif screen.name=='CuboidSixViewScreen':value=screen._six_state
    elif hasattr(screen,'_entry'):value=screen._entry
    else:value=(screen._cube.clone(),getattr(screen,'_recorded',None))
    return json.dumps(canonical(encode(value)),ensure_ascii=False,sort_keys=True)


class Audit(CubeApp):
    def on_start(self):
        self.simple_input=False;self.root.transition.duration=0
        Window.size=(800,600)
        self.cases=[
            ('cube2','InputScreen',lambda:self.new_cube(2)),
            ('cube3','InputScreen',lambda:self.new_cube(3)),
            ('cube4','InputScreen',lambda:self.new_cube(4)),
            ('penrose3','InputScreen',lambda:self.new_cube_variant('penrose_3',3)),
            ('penrose4','InputScreen',lambda:self.new_cube_variant('penrose_4',4)),
            ('bicube','InputScreen',lambda:self.new_cube_variant('bicube',3)),
            ('morphix3','MastermorphixScreen',lambda:self.new_mastermorphix(3)),
            ('morphix4','MastermorphixScreen',lambda:self.new_mastermorphix(4)),
            ('mirror3','MirrorScreen',lambda:self.new_mirror(3)),
            ('blanker','BlankerScreen',self.new_blanker),
            ('axis','ShapeCubeScreen',lambda:self.new_shape_cube('axis')),
            ('trajber4','ShapeCubeScreen',lambda:self.new_shape_cube('trajber',4)),
            ('ghost','GhostScreen',lambda:self.new_ghost(3)),
            ('mirror-tower','MirrorTowerScreen',self.new_mirror_tower),
            ('mirror-pyraminx','MirrorPyraminxScreen',lambda:self.new_mirror_pyraminx(3)),
            ('mirror-skewb','MirrorSkewbScreen',self.new_mirror_skewb),
            ('fisher-skewb','FisherSkewbScreen',self.new_fisher_skewb),
            ('container','ContainerScreen',self.new_container),
            ('mirror-minx2','MirrorMinxScreen',lambda:self.new_mirror_minx(2)),
            ('mirror-minx3','MirrorMinxScreen',lambda:self.new_mirror_minx(3)),
            ('megaminx','PolyhedralScreen',lambda:self.new_polyhedral('megaminx',3)),
            ('fto','PolyhedralScreen',lambda:self.new_polyhedral('fto',3)),
            ('dogic20','PolyhedralScreen',lambda:self.new_polyhedral('dogic_20',3)),
            ('fixed-cuboid','PolyhedralScreen',lambda:self.new_polyhedral('cuboid_332',3)),
            ('camouflage','CuboidSixViewScreen',lambda:self.new_polyhedral('camouflage_3',3)),
            ('changing-cuboid','CuboidSixViewScreen',lambda:self.new_polyhedral('cuboid_335',3)),
            ('mixup','MixupInputScreen',lambda:self.new_articulated('mixup_333')),
            ('mixup-plus','MixupInputScreen',lambda:self.new_articulated('mixup_plus_444')),
            ('tangram','ArticulatedEntryScreen',lambda:self.new_articulated('tangram')),
            ('tangram-extreme','ArticulatedEntryScreen',lambda:self.new_articulated('tangram_extreme')),
            ('pentacle','PentacleScreen',self.new_pentacle),
            ('square1','Square1Screen',self.new_square1),
            ('square2','SquareFamilyScreen',lambda:self.new_square_family('square2')),
            ('super-square1','SquareFamilyScreen',lambda:self.new_square_family('super_square1')),
        ]
        self.rows=[];self.index=0
        Clock.schedule_once(self.advance,.2)

    def advance(self,*_):
        if self.index==len(self.cases):self.stop();return
        label,name,prepare=self.cases[self.index]
        self.row=dict(case=label,screen=name,actions=[])
        self.root.current='HomeScreen'
        def enter(*_):
            try:
                prepare();self.root.current=name
                Clock.schedule_once(self.actions,.3)
            except Exception:self.fail()
        Clock.schedule_once(enter,.1)

    def buttons(self,screen):
        layout=getattr(screen,'_color_layout',None)
        if layout is not None and layout.active:return layout.entry_action_buttons
        if hasattr(screen,'entry_action_buttons'):return screen.entry_action_buttons
        return dict(target=screen.btn_assign,clear=screen.btn_clear,undo=screen.btn_undo)

    def press(self,key):
        button=self.buttons(self.root.current_screen)[key]
        assert not button.disabled,('button disabled',key)
        button.dispatch('on_release');self.row['actions'].append(key)

    def actions(self,*_):
        try:
            screen=self.root.current_screen;self.initial=state(screen)
            self.press('target');self.full=state(screen)
            self.press('undo');self.equal(self.initial,'Target undo changed input')
            self.press('target');assert state(screen)==self.full,'Target was not deterministic'
            if getattr(screen,'play_only',False):
                assert screen.view.on_pick is None and screen.shape_button.parent is None
                assert 'clear' in screen._play_actions.hidden_keys
                self.row['mode']='play-only';self.row['ok']=True;self.finish();return
            self.press('clear')
            popups=[w for w in Window.children if isinstance(w,Popup) and w._is_open]
            self.row['clear_confirmation']=bool(popups)
            if popups:
                popup=popups[0];popup.dismiss(animation=False)
                assert state(screen)==self.full,'Cancelling clear changed input'
                self.row['actions'].append('cancel-clear')
                Clock.schedule_once(self.confirm_clear,.1)
            else:self.after_clear()
        except Exception:self.fail()

    def confirm_clear(self,*_):
        try:
            self.press('clear')
            popup=next(w for w in Window.children if isinstance(w,Popup) and w._is_open)
            button=next(w for w in popup.walk() if isinstance(w,DangerButton))
            button.dispatch('on_release');popup.dismiss(animation=False)
            self.row['actions'].append('confirm-clear');self.after_clear()
        except Exception:self.fail()

    def after_clear(self):
        screen=self.root.current_screen
        assert state(screen)!=self.full,'Clear made no change'
        self.press('undo');self.equal(self.full,'Clear undo did not restore input')
        self.row['ok']=True;self.finish()

    def equal(self,expected,message):
        actual=state(self.root.current_screen)
        if actual!=expected:
            (OUT/(self.row['case']+'-expected.json')).write_text(expected,encoding='utf-8')
            (OUT/(self.row['case']+'-actual.json')).write_text(actual,encoding='utf-8')
            raise AssertionError(message)

    def fail(self):
        self.row['error']=traceback.format_exc()
        for w in list(Window.children):
            if isinstance(w,Popup):w.dismiss(animation=False)
        self.finish()

    def finish(self):
        self.rows.append(self.row)
        (OUT/'entry-button-matrix.json').write_text(json.dumps(self.rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(self.row,ensure_ascii=False),flush=True)
        self.index+=1;Clock.schedule_once(self.advance,.1)


if __name__=='__main__':
    audit=Audit()
    audit.run()
    raise SystemExit(0 if len(audit.rows)==len(audit.cases) and all(row.get('ok') for row in audit.rows) else 1)
