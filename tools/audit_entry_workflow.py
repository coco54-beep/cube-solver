"""All catalogue routes: invalid input, solver failure, cancel and late result.

Uses real entry/solve controls with a held service, so this tests page and task
ownership without spending solver time on hundreds of already-solved states.
"""
import sys,traceback
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from solver.result import SolveResult
from services.solve_service import SolveService
import tools.audit_entry_buttons as buttons
from tools.audit_catalogue_inputs import CatalogueAudit


class WorkflowAudit(CatalogueAudit):
    def on_start(self):
        self.held=[]
        SolveService.start=lambda service,cube,**kw:self.held.append((cube,kw))
        super().on_start()

    def buttons(self,screen):
        result=super().buttons(screen)
        if 'solve' not in result and hasattr(screen,'btn_solve'):result=dict(result,solve=screen.btn_solve)
        return result

    def after_clear(self):
        try:
            self.source=self.root.current_screen
            self.empty=buttons.state(self.source)
            assert self.empty!=self.full
            self.source_name=self.source.name;self.started=monotonic()
            self.press('solve');Clock.schedule_once(self.invalid_finished,.1)
        except Exception:self.fail()

    def invalid_finished(self,*_):
        try:
            assert self.root.current==self.source_name,'Invalid input navigated away'
            assert monotonic()-self.started<15,'Input validation did not finish'
            if self.source.entry_state.locked or getattr(self.source,'_busy_turn',False):
                Clock.schedule_once(self.invalid_finished,.1);return
            assert self.source._entry_notice['kind']=='input'
            assert buttons.state(self.source)==self.empty,'Validation changed the input'
            self.no_popup();self.row['invalid_stays_inline']=True
            self.press('undo');self.equal(self.full,'Undo after validation did not restore input')
            self.started=monotonic();self.press('solve')
            Clock.schedule_once(self.solver_started,.1)
        except Exception:self.fail()

    def solver_started(self,*_):
        try:
            assert monotonic()-self.started<15,'Valid input did not reach solving'
            if self.root.current!='SolvingScreen':
                Clock.schedule_once(self.solver_started,.1);return
            solving=self.root.current_screen
            if solving._run is None:Clock.schedule_once(self.solver_started,.1);return
            assert self.source.entry_state.locked and not solving.cancel.disabled
            self.notice_started=monotonic()
            solving._finish(SolveResult(False,[],'simulated internal error',0,0),solving._run)
            Clock.schedule_once(self.failure_returned,.1)
        except Exception:self.fail()

    def failure_returned(self,*_):
        try:
            assert self.root.current==self.source_name
            if getattr(self.source,'_entry_pending_notice',None) or getattr(self.source,'_entry_notice_delivery',None):
                assert monotonic()-self.notice_started<15,'Failure notice was not delivered'
                Clock.schedule_once(self.failure_returned,.05);return
            assert self.source._entry_notice['kind']=='solver'
            assert buttons.state(self.source)==self.full
            assert self.source.entry_can_edit() and not self.buttons(self.source)['random'].disabled
            self.no_popup();self.row['solver_failure_inline_input_preserved']=True
            self.press('solve');Clock.schedule_once(self.cancel_run,.1)
        except Exception:self.fail()

    def cancel_run(self,*_):
        try:
            assert self.root.current=='SolvingScreen'
            solving=self.root.current_screen;old=solving._run
            assert old is not None
            solving.back()
            self.notice_started=monotonic()
            solving._finish(SolveResult(True,[],'',0,0),old)
            solving._progress_for(old,{'progress':1.})
            Clock.schedule_once(self.cancel_returned,.1)
        except Exception:self.fail()

    def cancel_returned(self,*_):
        try:
            assert self.root.current==self.source_name
            if getattr(self.source,'_entry_pending_notice',None) or getattr(self.source,'_entry_notice_delivery',None):
                assert monotonic()-self.notice_started<15,'Cancellation notice was not delivered'
                Clock.schedule_once(self.cancel_returned,.05);return
            assert self.source.entry_can_edit() and not self.buttons(self.source)['random'].disabled
            assert buttons.state(self.source)==self.full
            self.no_popup();self.row.update(cancel_back_late_callbacks=True,ok=True);self.finish()
        except Exception:self.fail()

    def no_popup(self):
        assert not any(isinstance(w,Popup) and w._is_open for w in Window.children),'Unexpected error popup'


if __name__=='__main__':
    buttons.OUT=Path('reports/workflow-audit/2026-10-25/catalogue')
    buttons.OUT.mkdir(parents=True,exist_ok=True)
    app=WorkflowAudit();app.run()
    raise SystemExit(not(len(app.rows)==len(app.routes) and all(r.get('ok') for r in app.rows)))
