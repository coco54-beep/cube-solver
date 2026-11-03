"""Run reversible entry actions through every exposed catalogue order route.

Software UI audit only; does not certify correspondence with real mechanisms.
"""
import os,sys,argparse
from time import monotonic
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from kivy.clock import Clock
from kivy.core.window import Window
from types import SimpleNamespace
import tools.audit_entry_buttons as buttons
from ui.screens.irregular_directory_screen import ORDERS


class CatalogueAudit(buttons.Audit):
    scramble_checks=False
    only=()
    def on_start(self):
        self.simple_input=False;self.root.transition.duration=0
        Window.size=(800,600)
        self.routes=[(family,order) for family,orders in ORDERS.items() for order in orders]
        self.routes.extend((kind,None) for kind in ('pentacle','pandora','o2','ancient_coin','camouflage_3',
                            'helicopter','clover','blossom','petal_tetrahedron',
                            'petal_tetrahedron_nocentre','petal_icosahedron',
                            'petal_icosahedron_nocentre','pyraminx_duo','coin_tetrahedron'))
        if self.only:self.routes=[r for r in self.routes if r[0] in self.only]
        self.cases=self.routes;self.rows=[];self.index=0
        Clock.schedule_once(self.advance,.1)

    def advance(self,*_):
        if self.index==len(self.routes):self.stop();return
        family,order=self.routes[self.index]
        self.row=dict(case=f'{family}-{order}',family=family,order=order,actions=[])
        self.root.current='HomeScreen'
        def enter(*_):
            try:
                if family=='pentacle':self.new_pentacle();name='PentacleScreen'
                elif family=='pandora':self.new_shape_cube('pandora');name='ShapeCubeScreen'
                elif order is None:
                    self.new_polyhedral(family,1 if family=='o2' else 3)
                    from ui.screens.polyhedral_screen import _entry_for
                    name=_entry_for(self.cube)
                else:
                    directory=self.root.get_screen('HomeScreen')
                    directory.select_order(SimpleNamespace(dismiss=lambda:None),family,order)
                    name=self.root.current
                    assert name not in ('HomeScreen','IrregularDirectoryScreen'),('unrouted',family,order)
                self.root.current=name;self.row['screen']=name
                self.row['kind']=self.cube.puzzle_kind if hasattr(self.cube,'puzzle_kind') else 'cube'
                self.row['n']=self.cube.n
                Clock.schedule_once(self.actions,.12)
            except Exception:self.fail()
        Clock.schedule_once(enter,.03)

    def buttons(self,screen):
        result=super().buttons(screen)
        if 'random' not in result and hasattr(screen,'btn_random'):
            result=dict(result,random=screen.btn_random)
        return result

    def after_clear(self):
        if not self.scramble_checks:return super().after_clear()
        try:
            screen=self.root.current_screen
            assert buttons.state(screen)!=self.full,'Clear made no change'
            self.press('undo');self.equal(self.full,'Clear undo did not restore input')
            self.random_started=monotonic();self.press('random')
            Clock.schedule_once(self.after_random,.1)
        except Exception:self.fail()

    def after_random(self,*_):
        try:
            screen=self.root.current_screen
            elapsed=monotonic()-self.random_started
            assert elapsed<40,('scramble timeout',self.row['case'])
            if self.buttons(screen)['random'].disabled or getattr(screen,'_job',None) is not None:
                Clock.schedule_once(self.after_random,.1);return
            assert buttons.state(screen)!=self.full,('scramble made no change',getattr(screen,'_message',''))
            self.row['scramble_seconds']=round(elapsed,3)
            self.press('undo');self.equal(self.full,'Scramble undo did not restore input')
            self.row['ok']=True;self.finish()
        except Exception:
            if hasattr(self.root.current_screen,'cancel_matching'):self.root.current_screen.cancel_matching()
            elif hasattr(self.root.current_screen,'_cancel_solve'):self.root.current_screen._cancel_solve()
            self.fail()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scramble',action='store_true');parser.add_argument('--only',nargs='+')
    args=parser.parse_args();CatalogueAudit.scramble_checks=args.scramble;CatalogueAudit.only=args.only or ()
    folder=('catalogue-scrambles' if args.scramble else 'catalogue-inputs')
    if args.only:folder+='-'+'-'.join(args.only)
    buttons.OUT=Path('reports/full-audit/2026-10-24')/folder
    buttons.OUT.mkdir(parents=True,exist_ok=True)
    audit=CatalogueAudit();audit.run()
    raise SystemExit(not(len(audit.rows)==len(audit.routes) and all(r.get('ok') for r in audit.rows)))
