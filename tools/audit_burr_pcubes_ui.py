"""Exercise Burr's real entry controls at desktop and phone sizes."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
from app.fonts import setup_cjk_font
setup_cjk_font()
from kivy.lang import Builder
Builder.load_file(str(Path(__file__).resolve().parents[1]/'ui/kv/app.kv'))
from kivy.core.window import Window
import pytest
from tests.test_bandaged_manual_controls import test_empty_input_real_controls_match_a_24_turn_scramble,CaptureSolve,pump

OUT=Path('reports/optimization/2026-11-02/burr-pcubes')


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    original=CaptureSolve.configure
    for size in ((800,600),(390,844)):
        Window.size=size;patch=pytest.MonkeyPatch()
        def capture(screen,cube,*args):
            pump()
            screen.manager.get_screen('InputScreen').export_to_png(str(OUT/f'entry-{size[0]}.png'))
            return original(screen,cube,*args)
        patch.setattr(CaptureSolve,'configure',capture)
        try:test_empty_input_real_controls_match_a_24_turn_scramble(patch,'burr_cube')
        finally:patch.undo()
        rows.append(dict(size=size,passed=True,real_controls=True,faces=6,source_turns=24))
        (OUT/'ui-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    from demo.coverage import lessons,complete_lessons
    count=0
    for step in lessons('burr_cube',4)+complete_lessons('burr_cube',4):
        for case in step['cases']:
            cube=case['initial'].clone()
            for move in case['moves']:cube.apply_move(move)
            assert cube.is_solved();count+=1
    (OUT/'demo-results.json').write_text(json.dumps(dict(cases=count,all_replays_solved=True)),encoding='utf-8')
    print('UI pages',len(rows),'demo cases',count,flush=True)


if __name__=='__main__':main()
