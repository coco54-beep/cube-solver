"""Review essential-only simple actions, with no overflow menu at any width."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_entry_buttons as base
from kivy.clock import Clock
from kivy.core.window import Window
from ui.widgets.entry_controls import EntryActionRow
from ui.widgets.icons import icon_image
from app.session import encode
from cube.bandaged_cube import KINDS
OUT=Path('reports/optimization/2026-11-03/simple-icon-controls')
OUT.mkdir(parents=True,exist_ok=True)
base.OUT=OUT
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        super().on_start()
        self.simple_input=True
        self.cases.extend((
            ('time-machine','PolyhedralScreen',lambda:self.new_polyhedral('time_machine',2)),
            ('bean6','PolyhedralScreen',lambda:self.new_polyhedral('bean_6',6)),
            ('bean10','PolyhedralScreen',lambda:self.new_polyhedral('bean_10',10)),
            ('twins','TwinsInputScreen',self.new_twins),
            ('flower','FlowerCopterInputScreen',self.new_flower_copter),
            ('helicopter14','EdgeJumblingInputScreen',lambda:self.new_polyhedral('helicopter_14',3)),
        ))
        self.cases.extend((kind,'BandagedSixViewScreen',lambda k=kind:self.new_cube_variant(k,KINDS[k])) for kind in KINDS)
        self.cases=[(label,name,prepare,size) for size in ((390,844),(800,600))
                    for label,name,prepare in self.cases]

    def advance(self,*_):
        if self.index==len(self.cases):self.stop();return
        label,name,prepare,size=self.cases[self.index]
        self.row=dict(case=label,screen=name,size=size,ok=False)
        try:
            self.root.current='HomeScreen';Window.size=size;prepare()
            self.root.current=name
            Clock.schedule_once(self.actions,.3)
        except Exception:self.fail()

    def actions(self,*_):
        try:
            screen=self.root.current_screen
            self.icon_rows=[w for w in screen.walk() if isinstance(w,EntryActionRow)]
            assert self.icon_rows,screen.name
            self.snapshot=json.dumps(encode(self.cube),sort_keys=True)
            for row in self.icon_rows:
                row.reflow()
                for key,button in row.buttons.items():
                    assert button.icon_name and not button.text,(self.row['case'],key,button.text)
                    assert icon_image(button.icon_name) is not None,(key,button.icon_name)
                assert not hasattr(row,'more') and not hasattr(row,'open_more')
                keys=row.play_keys if getattr(row.owner,'play_only',False) else row.simple_keys
                assert list(reversed(row.children))==[row.buttons[k] for k in keys if k in row.buttons and k not in row.hidden_keys]
                for key,button in row.buttons.items():
                    if key not in keys or key in row.hidden_keys:assert button.parent is None
                self.simple_input=False;row.reflow()
                assert list(reversed(row.children))==[b for k,b in row.buttons.items() if k not in row.hidden_keys]
                self.simple_input=True;row.reflow()
                assert json.dumps(encode(self.cube),sort_keys=True)==self.snapshot
            Clock.schedule_once(self.check,.15)
        except Exception:self.fail()

    def check(self,*_):
        try:
            screen=self.root.current_screen
            for row in self.icon_rows:
                assert all(b.icon_name and not b.text for b in row.buttons.values())
            if self.row['case'] in ('cube3','time-machine','mixup','bicube'):
                screen.export_to_png(str(OUT/f"{self.row['case']}-{self.row['size'][0]}.png"))
            self.row['ok']=True;self.row['action_rows']=len(self.icon_rows)
            self.rows.append(self.row);self.write();self.index+=1
            Clock.schedule_once(self.advance,.02)
        except Exception:self.fail()

    def write(self):
        (OUT/'native-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')

    def fail(self):
        import traceback
        self.row['error']=traceback.format_exc();self.rows.append(self.row);self.write();self.stop()

    def on_stop(self):pass


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=len(app.cases) or not all(row['ok'] for row in app.rows):raise SystemExit(1)
