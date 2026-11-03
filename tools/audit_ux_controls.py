"""Real visible controls: failure recovery, phone menus, paint, chapters and speed."""
import os,sys,json
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from services.solve_service import SolveService
from solver.result import SolveResult
from cube.conversion import cubies_to_facelets
from demo.course import load
from demo.solutions import state_signature

OUT=Path('reports/ux-optimization/2026-10-25/visible');OUT.mkdir(parents=True,exist_ok=True)


class Audit(CubeApp):
    def on_start(self):
        self.simple_input=True;self.root.transition=NoTransition();Window.size=(390,844)
        self.rows=[];self.held=[]
        SolveService.start=lambda service,cube,**kw:self.held.append((cube,kw))
        self.new_cube(3);self.root.current='InputScreen';Clock.schedule_once(self.incomplete,.2)

    def shot(self,name,widget=None):
        (widget or self.root.current_screen).export_to_png(str(OUT/(name+'.png')))

    def incomplete(self,_):
        s=self.root.current_screen;before=s.collect_facelets();s.start_solve()
        assert self.root.current=='InputScreen' and s._entry_notice['category']=='incomplete'
        s._entry_problem_actions.locate.dispatch('on_release');assert s.collect_facelets()==before
        assert s.view._entry_pivot is not None and s._ori.current_face()==s.view._entry_pivot[0]
        self.rows.append(dict(case='incomplete_locate_keeps_input',passed=True))
        Clock.schedule_once(lambda _:Clock.schedule_once(self.menu,0),0)

    def menu(self,_):
        s=self.root.current_screen;self.shot('incomplete')
        from cube.coordinates import pos_from_rc
        face,r,c=s.view._entry_pivot
        matches=[q for q,p,f in s.view._last_quads if p==pos_from_rc(3,face,r,c) and f==face]
        assert matches and s.view._pivot_marks.children,'Located cell must be visibly marked'
        s.set_facelets(cubies_to_facelets(self.cube.cubies,3));self.solved=s.collect_facelets()
        row=s.simple_turn_row;assert len(row.children)==3
        row.more.dispatch('on_release');assert row.popup and row.popup._is_open
        Clock.schedule_once(lambda _:Clock.schedule_once(self.random_and_undo,0),0)

    def random_and_undo(self,_):
        s=self.root.current_screen;row=s.simple_turn_row;self.shot('more-menu',row.popup)
        row.buttons['random'].dispatch('on_release');assert row.popup is None
        row.buttons['undo'].dispatch('on_release');assert s.collect_facelets()==self.solved
        self.rows.append(dict(case='compact_menu_random_undo',passed=True))
        s.start_solve();Clock.schedule_once(self.timeout,.2)

    def timeout(self,_):
        solving=self.root.current_screen;assert solving.name=='SolvingScreen'
        self.old_run=solving._run
        solving._finish(SolveResult(False,[],'cuboid.search_budget',0,0,[],'solver','timeout'),self.old_run)
        Clock.schedule_once(self.retry,.15)

    def retry(self,_):
        s=self.root.current_screen;assert s.name=='InputScreen' and s._entry_notice['category']=='timeout'
        assert s.msg.text==s._entry_notice['text']
        assert s.collect_facelets()==self.solved and s.entry_can_edit()
        self.shot('timeout-retry');s._entry_problem_actions.retry.dispatch('on_release')
        Clock.schedule_once(self.cancel,.15)

    def cancel(self,_):
        solving=self.root.current_screen;assert solving.name=='SolvingScreen'
        solving.on_cancel();solving._finish(SolveResult(True,[],'',0,0),self.old_run)
        assert self.root.current=='InputScreen' and self.root.current_screen.collect_facelets()==self.solved
        self.rows.append(dict(case='timeout_retry_cancel_ignores_old_result',passed=True))
        self.new_articulated('mixup_plus_444');self.root.current='MixupInputScreen'
        Clock.schedule_once(self.paint,.2)

    def paint(self,_):
        s=self.root.current_screen;draft=s._get_draft()
        corners=[i for i,b in enumerate(draft.blocks) if b['role']=='corner'][:2]
        s.select_color(2);s.select_color(2);assert s._paint_enabled
        for bi in corners:s.pick(bi*1024)
        assert all(s._get_draft().blocks[bi]['cells'][0]['color']==2 for bi in corners)
        before=deepcopy(s._mx_state);s.mode_button.dispatch('on_release');s.pick(corners[0]*1024)
        assert s._mx_state==before and not s._paint_enabled
        self.rows.append(dict(case='continuous_paint_explicit_select_mode',passed=True))
        Clock.schedule_once(lambda _:Clock.schedule_once(self.chapters,0),0)

    def chapters(self,_):
        self.shot('mixup-mode');self.draft_before=tuple(self.cube.frames)
        d=self.root.get_screen('DemoScreen');d.enter_case(('master_brilic',3),0,0,load('master_brilic',3))
        self.root.current=d.name;d.set_speed(2);popup=d.open_chapters()
        Clock.schedule_once(lambda _:Clock.schedule_once(self.chapter_chosen,0),0)

    def chapter_chosen(self,_):
        d=self.root.current_screen;popup=d._chapter_popup;self.shot('chapter-directory',popup)
        popup.content.children[0].children[0].dispatch('on_release')
        assert d._move_index==d._parts[-1]['start'] and d._playback_speed==2
        assert len(d._moves)==2456 and tuple(self.cube.frames)==self.draft_before
        self.rows.append(dict(case='chapter_seek_speed_preserves_input_and_full_word',passed=True))
        Clock.schedule_once(lambda _:Clock.schedule_once(self.export_chooser,0),0)

    def export_chooser(self,_):
        d=self.root.current_screen;self.shot('long-course-controls');popup=d.open_export()
        Clock.schedule_once(lambda _:Clock.schedule_once(lambda _:self.finish(popup),0),0)

    def finish(self,popup):
        self.shot('export-estimate',popup);popup.dismiss()
        (OUT/'results.json').write_text(json.dumps(self.rows,ensure_ascii=False,indent=2),encoding='utf-8')
        assert len(self.rows)==5 and all(r['passed'] for r in self.rows)
        self.stop();print(json.dumps(self.rows),flush=True)


if __name__=='__main__':Audit().run()
