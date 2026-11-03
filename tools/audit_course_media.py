"""Run actual Kivy course playback and narrated MP4 export, without packaging."""
import os,sys,time,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.application import CubeApp
from demo.course import load
from demo.solutions import state_signature
from ui.demo_video import VideoExport
from candidate_puzzles import BY_KIND


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',default='i_cube')
    parser.add_argument('--section',type=int);parser.add_argument('--no-voice',action='store_true')
    parser.add_argument('--cancel',action='store_true')
    parser.add_argument('--timeout',type=int,default=180)
    parser.add_argument('--compare-redraw',action='store_true')
    parser.add_argument('--speed',type=float,default=1.)
    args=parser.parse_args();kind=args.kind;n=BY_KIND[kind].n
    out=Path('reports/course-audit/2026-10-25');out.mkdir(parents=True,exist_ok=True)
    app=CubeApp();app.simple_input=False;app.theme.apply(False)
    manager=app.root=app.build();manager.transition=NoTransition();Window.size=(480,850)
    Window.add_widget(manager);EventLoop.start()
    demo=manager.get_screen('DemoScreen');steps=load(kind,n)
    demo.enter_case((kind,n),0,0,steps);manager.current=demo.name
    demo.set_speed(args.speed)
    before=state_signature(demo._work)
    for _ in range(4):EventLoop.idle()
    demo.export_to_png(str(out/'course-player.png'))
    selected=demo._parts[args.section] if args.section is not None else None
    job=VideoExport(demo,selected,not args.no_voice);demo._export_job=job;job.start()
    checked_frames=[]
    if args.compare_redraw:
        capture=job._capture
        def verified_capture(redraw=True):
            rgba=capture(redraw)
            if not redraw and len(checked_frames)<12:
                import numpy as np
                expected=capture(True)
                difference=np.abs(np.frombuffer(rgba,dtype=np.uint8).astype(int)-np.frombuffer(expected,dtype=np.uint8))
                assert np.count_nonzero(difference>8)/len(difference)<.01,'Cached geometry changed the frame'
                checked_frames.append(int(np.count_nonzero(difference)))
            return rgba
        job._capture=verified_capture
    started=time.monotonic();deadline=started+args.timeout;next_report=started+10
    while demo._export_job is job and time.monotonic()<deadline:
        EventLoop.idle();time.sleep(.002)
        if time.monotonic()>=next_report:
            print(json.dumps(dict(elapsed=round(time.monotonic()-started,1),
                move=getattr(job.player,'_move_index',None),frames=job.frame_count)),flush=True)
            next_report=time.monotonic()+10
        if args.cancel and job.frame_count>0:
            job.cancel();assert job.finished.wait(10)
            assert not job.folder.exists() and not job.output.exists()
            assert state_signature(demo._work)==before and demo._export_job is None
            (out/'cancel.json').write_text(json.dumps(dict(cancelled=True,temporary_files_removed=True,
                input_unchanged=True),indent=2),encoding='utf-8')
            print('CANCEL_PASS',flush=True);Window.remove_widget(manager);EventLoop.stop();return
    if demo._export_job is job:job.cancel();raise AssertionError('Export timed out')
    assert job.output.exists(),demo.lbl_media.text
    assert state_signature(demo._work)==before
    assert job.actions_started==job.end_index-job.start_index
    expected=demo._initial.clone()
    for move in demo._moves[:job.end_index]:expected.apply_move(move)
    assert job.final_signature==state_signature(expected)
    import shutil
    stem=kind+('-complete' if selected is None else '-section')+('-silent' if args.no_voice else '-narrated')
    if args.speed!=1.:stem+=f'-{args.speed:g}x'
    destination=out/(stem+'.mp4');shutil.copy2(job.output,destination)
    shutil.copy2(job.output.with_suffix('.srt'),destination.with_suffix('.srt'))
    demo.export_to_png(str(out/'export-complete.png'))
    (out/(stem+'.json')).write_text(json.dumps(dict(output=str(destination),course_moves=len(demo._moves),
        rendered_moves=job.actions_started,start=job.start_index,end=job.end_index,final_state_matches_replay=True,
        frames=job.frame_count,fps=job.FPS,input_unchanged=True,elapsed=round(time.monotonic()-started,2),
        speed=job.speed,checked_geometry_frames=len(checked_frames)),indent=2),encoding='utf-8')
    print('EXPORTED',destination,flush=True)
    Window.remove_widget(manager);EventLoop.stop()


if __name__=='__main__':main()
