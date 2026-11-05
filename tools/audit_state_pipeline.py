"""Fresh visible-only input -> production solve -> independent legal replay.

Source cubes are kept outside matching/solving. A serialized input is the only
boundary crossing; history and source poses are never given to the solver.
"""
import json,sys,random,threading
from collections import defaultdict
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.solve_service import SolveService,CancelToken

OUT=Path('reports/reliability-audit/2026-10-25/fresh-inputs')


def reenter(kind,seed,length):
    from cube.cuboid import MODELS as CUBOIDS
    if kind in CUBOIDS:
        from cube.cuboid import CuboidCube
        from cube.cuboid_observation import SixViewDraft,project,EMPTY
        from cube.polyhedral_scramble import scramble
        source=CuboidCube.solved(kind);scramble(source,length,seed);draft=SixViewDraft(kind)
        target=project(source,draft.model)
        for face,view in enumerate(target):
            width,_=draft.model['shapes'][face];panels=defaultdict(list)
            for index,(colour,owner,depth) in enumerate(view):
                if colour!=EMPTY:panels[colour,owner,depth].append(index)
            for (colour,_,depth),indices in sorted(panels.items(),key=lambda p:p[0][2]):
                rows=[i//width for i in indices];cols=[i%width for i in indices]
                draft.paint(face,draft.rectangle(face,min(rows)*width+min(cols),max(rows)*width+max(cols)),colour)
            draft.mark_outside(face)
        if kind=='mirror_camouflage_3':
            # Supply depth only where the app would ask for it. Keep the final
            # observation in the same format as an edited draft from the app.
            while True:
                result=draft.match(seconds=20.)
                if result.status!='ambiguous':break
                face,index=result.face,result.cell
                color,group,known_depth=draft.views[face][index]
                depth=target[face][index][2]
                assert group and known_depth is None and depth is not None,result
                indices=[i for i,(_,g,_) in enumerate(draft.views[face]) if g==group]
                draft.paint(face,indices,color,depth)
        payload=draft.state()
        def rebuild(data):
            result=SixViewDraft(kind,data).match(seconds=20.)
            assert result.status=='ok',result.status
            actual=project(result.cube,draft.model)
            assert all([(c,d) for c,g,d in a]==[(c,d) for c,g,d in b] for a,b in zip(actual,target))
            def boundaries(view):
                groups=defaultdict(list)
                for i,(colour,owner,depth) in enumerate(view):
                    if colour!=EMPTY:groups[owner].append(i)
                return sorted(tuple(indices) for indices in groups.values())
            assert all(boundaries(a)==boundaries(b) for a,b in zip(actual,target))
            assert set(result.cube.moves())==set(source.moves())
            return result.cube
    elif kind.startswith('tangram'):
        from cube.articulated import ArticulatedCube
        from cube.articulated_observation import ObservationDraft,match_observations,polygon_key
        from solver.tangram_geometry import geometry
        source=ArticulatedCube(kind);model=geometry(kind);rng=random.Random(seed);previous=None
        for _ in range(length):
            frames,move=rng.choice([(f,m) for f,m in model.children(source.frames) if (m.axis,m.layer)!=previous])
            source.apply_move(move);previous=move.axis,move.layer
        payload=ObservationDraft.from_cube(source).state()
        def signature(cube):
            return sorted((c,polygon_key(poly)) for h in range(len(cube.solids)) for poly,c in cube.placed_faces(h) if c>=0)
        def rebuild(data):
            result=match_observations(ObservationDraft(kind,data),seconds=20.)
            assert result.status=='matched',result.status
            assert signature(result.cube)==signature(source)
            return result.cube
    else:
        from cube.bandaged_cube import BandagedCube
        from cube.bandaged_entry import reconstruct,plates
        from cube.conversion import cubies_to_facelets
        source=BandagedCube.random_scramble(kind,length,seed)
        payload=dict(facelets=cubies_to_facelets(source.cubies,source.n),plates=[dict(face=p.face,cells=p.cells) for p in plates(source)])
        def rebuild(data):
            seams={(p['face'],tuple(tuple(c) for c in p['cells'])) for p in data['plates']}
            cube=reconstruct(kind,data['facelets'],seams)
            assert cubies_to_facelets(cube.cubies,cube.n)==data['facelets']
            assert {(p.face,p.cells) for p in plates(cube)}==seams
            return cube
    assert not {'history','frames','source_cube'}&payload.keys()
    OUT.mkdir(parents=True,exist_ok=True);path=OUT/f'{kind}-{seed}-{length}.json'
    path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    cube=rebuild(json.loads(path.read_text(encoding='utf-8')))
    assert not cube.history
    return cube,str(path)


def main():
    rows=[]
    cases=[('camouflage_3',seed,count) for count in (10,40,100) for seed in (20261025,20261026)]
    cases += [(kind,20261025,40) for kind in ('fused_cube','two_bar_cube','bandaged_c','bicube','ai_cube','burr_cube')]
    cases += [(kind,20261025,40) for kind in ('tangram','tangram_extreme')]
    for kind,seed,length in cases:
        row=dict(kind=kind,seed=seed,scramble_turns=length);started=monotonic()
        try:
            cube,path=reenter(kind,seed,length);row.update(input_file=path,history_empty=True,visible_entry_matches=True)
            cancel=CancelToken();timer=threading.Timer(60,cancel.cancel);timer.daemon=True;timer.start();answers=[]
            try:SolveService()._run(cube.clone(),answers.append,None,cancel)
            finally:timer.cancel()
            assert len(answers)==1;result=answers[0];replay=cube.clone()
            if result.success:
                for move in result.moves:replay.apply_move(move)
            row.update(success=result.success,replay_solved=result.success and replay.is_solved(),moves=len(result.moves),
                       failure_kind=result.failure_kind,message=result.message)
            assert not cube.history
        except Exception as exc:row.update(success=False,error=type(exc).__name__+': '+str(exc))
        row['seconds']=round(monotonic()-started,3);rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
        (OUT.parent/'fresh-state-pipeline.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(r.get('replay_solved') for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
