"""Repeatable visible-input -> fresh model -> production solve -> legal replay.

Adapters are listed explicitly. This checks data entry/matching, not GUI taps;
the separate real-controls tests remain necessary. No inverse scramble is used.
"""
import argparse,json,random,sys,threading,os
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from candidate_puzzles import PLAY_ONLY_KINDS,REQUESTED
from cube.articulated import MIXUP_MODELS
from cube.cuboid import MODELS as CUBOIDS,FIXED_SHAPE_KINDS
from services.solve_service import SolveService,CancelToken

BANDAGED=('fused_cube','two_bar_cube','bandaged_c','bicube','ai_cube','burr_cube')
FIXED={e.kind:e.n for e in REQUESTED if e.mechanism not in
       ('extended','shape','blanker','mirror_minx','skewb_shell','reference_needed') and e.kind not in PLAY_ONLY_KINDS}
BASE_SUPPORTED=tuple(MIXUP_MODELS)+('camouflage_3','tangram','tangram_extreme')+BANDAGED+tuple('cube_'+str(n) for n in (2,3,4,5))+tuple(FIXED)
from vision.scan_profiles import SUPPORTED as PHOTO_MODELS
FIXED.update({kind:orders[0] for kind,orders in PHOTO_MODELS.items()
              if kind not in set(BASE_SUPPORTED)|PLAY_ONLY_KINDS|{'pandora','tangram'} and kind not in CUBOIDS})
SUPPORTED=tuple(dict.fromkeys(BASE_SUPPORTED+tuple(FIXED)+tuple(CUBOIDS)))
ADDITIONAL=tuple(kind for kind in SUPPORTED if kind not in BASE_SUPPORTED)


def enter(kind,seed,length,folder):
    folder.mkdir(parents=True,exist_ok=True)
    if kind in BANDAGED or kind in ('tangram','tangram_extreme') or kind in CUBOIDS and kind not in FIXED_SHAPE_KINDS:
        import tools.audit_state_pipeline as prior
        prior.OUT=folder
        cube,path=prior.reenter(kind,seed,length)
        return cube,path,'visible panels / fixed bandage layout'
    if kind in FIXED_SHAPE_KINDS:
        from cube.cuboid import CuboidCube
        from cube.polyhedral_scramble import scramble
        from vision.scan_profiles import ScanProfile
        source=CuboidCube.solved(kind);scramble(source,length,seed)
        profile=ScanProfile(kind,source.n);payload=profile.from_cube(source)
        # JSON object keys are strings after serialization.
        def rebuild(data):
            entered=profile.apply({face:{int(i):v for i,v in values.items()} for face,values in data.items()},CuboidCube.solved(kind))
            assert entered.colors==source.colors
            return entered
        method='fixed cuboid visible panels, colours only'
    elif kind in MIXUP_MODELS:
        from cube.mixup import MixupCube
        from cube.mixup_entry import MixupEntryDraft
        from cube.articulated_observation import match_observations
        from solver.mixup_reduction import geometry
        source=MixupCube(kind);model=geometry(kind);rng=random.Random(seed);last=None
        for i in range(length):
            choices=list(model.children(source.frames,model.describe(source.frames)[0],last=last,complete=True))
            odd=[v for v in choices if v[1].amount%2]
            frames,move=rng.choice(odd if i==length-1 and odd else choices)
            source.apply_move(move)
            layers=getattr(move,'layers',()) or (move.layer,);last=move.axis,tuple(layers)
        target=MixupEntryDraft.from_cube(source)
        from tools.audit_mixup_manual_roundtrip import menu_coverage,geometry as panels
        coverage,draft=menu_coverage(target)
        assert draft is not None,coverage
        payload=draft.observations().state()
        def rebuild(data):
            from cube.articulated_observation import ObservationDraft
            result=match_observations(ObservationDraft(kind,data),seconds=20.)
            assert result.status=='matched',result.status
            assert panels(MixupEntryDraft.from_cube(result.cube))==panels(target)
            return result.cube
        method='blank assembly choices + actual rotation step + panel colours'
    elif kind.startswith('cube_'):
        from cube.cube2 import Cube2
        from cube.cube3 import Cube3
        from cube.cube4 import Cube4
        from cube.cube5 import Cube5
        from cube.conversion import cubies_to_facelets,facelets_to_cubies
        from demo.expanded_support import scramble
        n=int(kind.split('_')[1]);cls={2:Cube2,3:Cube3,4:Cube4,5:Cube5}[n]
        source=scramble(cls.solved(),seed,length);payload=cubies_to_facelets(source.cubies,n)
        def rebuild(data):
            cubies=facelets_to_cubies(data,n)
            if n==4:
                from solver.solver4 import _rebuild_center_homes
                _rebuild_center_homes(cubies)
            cube=cls(cubies);assert cubies_to_facelets(cube.cubies,n)==payload
            return cube
        method='six faces, colours only'
    else:
        from cube.polyhedral import PolyhedralPuzzle
        from demo.expanded_support import scramble
        n=FIXED[kind];source=scramble(PolyhedralPuzzle(kind,n),seed,length)
        payload={'colours':list(source.colors)}
        def rebuild(data):
            cube=PolyhedralPuzzle(kind,n,list(data['colours']))
            assert cube.colors==source.colors
            return cube
        method='fixed visible model panels, colours only'
    assert not {'frames','history','source_cube'}&payload.keys()
    path=folder/f'{kind}-{seed}-{length}.json';path.write_text(json.dumps(payload),encoding='utf-8')
    cube=rebuild(json.loads(path.read_text(encoding='utf-8')))
    assert not getattr(cube,'history',None) and not getattr(cube,'scramble_history',None)
    return cube,str(path),method


def run(kind,seed,length,folder,budget):
    from services.solution_cache import clear
    from solver.search_resume import clear as clear_search
    clear();clear_search();row=dict(kind=kind,seed=seed,scramble_turns=length,evaluation_budget_seconds=budget);started=monotonic()
    stage='input'
    try:
        cube,path,method=enter(kind,seed,length,folder/'inputs')
        row.update(input_file=path,input_method=method,history_empty=True,visible_entry_matches=True,
                   input_seconds=round(monotonic()-started,3))
        stage='solve';solve_started=monotonic()
        events=[]
        def progress(payload):
            label=payload.get('label')
            if label and (not events or events[-1]['label']!=label):
                events.append({'label':label,'seconds':round(monotonic()-solve_started,3)})
        token=CancelToken();timer=threading.Timer(budget,token.cancel);timer.daemon=True;answers=[];timer.start()
        try:SolveService()._run(cube.clone(),answers.append,progress,token)
        finally:timer.cancel()
        assert len(answers)==1;result=answers[0]
        row.update(success=result.success,moves=len(result.moves),failure_category=result.failure_category,
                   solve_seconds=round(monotonic()-solve_started,3),
                   progress_stages=events[-20:],
                   message=result.message,evaluation_budget_hit=token.is_set())
        if result.success:
            stage='replay';replay_started=monotonic()
            replay=cube.clone()
            for move in result.moves:replay.apply_move(move)
            row['replay_solved']=replay.is_solved();assert replay.is_solved()
            row['replay_seconds']=round(monotonic()-replay_started,3)
        assert not getattr(cube,'history',None) and not getattr(cube,'scramble_history',None)
    except Exception as exc:row.update(success=False,failed_stage=stage,error=type(exc).__name__+': '+str(exc))
    row['seconds']=round(monotonic()-started,3)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',action='append',choices=SUPPORTED)
    p.add_argument('--seed',action='append',type=int);p.add_argument('--turns',type=int,default=6)
    p.add_argument('--all',action='store_true');p.add_argument('--list',action='store_true')
    p.add_argument('--budget',type=float,default=60.)
    p.add_argument('--out',type=Path,default=Path('reports/optimization/2026-10-25/phase-2-6/random-inputs'))
    args=p.parse_args()
    if args.list:print(json.dumps(SUPPORTED));return
    if args.turns<1 or args.budget<=0:p.error('turns and budget must be positive')
    kinds=SUPPORTED if args.all else args.kind or ('mixup_333','mixup_plus_444','camouflage_3','tangram_extreme','cube_4')
    args.out.mkdir(parents=True,exist_ok=True);rows=[]
    for kind in kinds:
        for seed in args.seed or (20261027,20261028):
            row=run(kind,seed,args.turns,args.out,args.budget);rows.append(row)
            (args.out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)
    if not all(r.get('replay_solved') for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
