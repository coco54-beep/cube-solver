"""Native shared-cut Dogic entry checks and comparable grey/painted views."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_lanlan_models as shared
from kivy.clock import Clock

shared.KINDS=('dogic_i','dogic_20')
shared.OUT=Path(os.environ.get('DOGIC_AUDIT_OUT','reports/expansion/2026-10-27/dogic-colourways/visible'))
shared.OUT.mkdir(parents=True,exist_ok=True)


class Audit(shared.Audit):
    def input(self,*args):
        # Window-size changes can finish after the first scheduled entry
        # callback. Settle layout, then draw labels and FBO from one geometry.
        Clock.schedule_once(self.ready_input,.25)

    def ready_input(self,*args):
        self.entry.view._draw()
        # Each inset is clickable. Three twenty-colour centre inlays select
        # the same logical colour field, while plastic gaps select nothing.
        view=self.entry.view;g=self.entry._cube.geometry;hits=set()
        for polygon,slot in view._polygons:
            if slot is None:continue
            x=sum(p[0] for p in polygon)/len(polygon)+view.x
            y=sum(p[1] for p in polygon)/len(polygon)+view.y
            if view.pick(x,y)==slot:hits.add(slot)
        assert hits
        if self.kind=='dogic_i':assert any(len(g.pieces[g.stickers[s].piece])==3 for s in hits)
        super().input()

    def open_turn(self,*args):
        self.entry.view._draw();super().open_turn()

    def solved(self,attempt):
        screen=self.root.current_screen
        if screen._seek_job is None:
            screen._refresh();screen.view._draw()
        super().solved(attempt)


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=4 or not all(row['passed'] for row in app.rows):raise SystemExit(1)
