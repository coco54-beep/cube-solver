"""Generate, visibly re-enter and solve bandages without retaining a witness."""
import json
import sys
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.bandaged_cube import BandagedCube
from cube.bandaged_entry import reconstruct,plates
from cube.conversion import cubies_to_facelets
from services.solve_service import SolveService


def run(kinds,output):
    report={'method':'visible colours + seam partitions -> reconstruct -> empty-history SolveService -> legal replay',
            'cases':[]}
    for kind in kinds:
        for seed in range(8):
            source=BandagedCube.random_scramble(kind,40,seed)
            facelets=cubies_to_facelets(source.cubies,source.n)
            seams={(p.face,p.cells) for p in plates(source)}
            cube=reconstruct(kind,facelets,seams)
            assert not cube.history
            assert cubies_to_facelets(cube.cubies,cube.n)==facelets
            assert {(p.face,p.cells) for p in plates(cube)}==seams
            started=monotonic()
            class Cancel:
                def is_set(self):return monotonic()-started>31
            result=[];SolveService()._run(cube,result.append,None,Cancel());result=result[0]
            solved=False
            if result.success:
                replay=cube.clone();replay.apply_moves(result.moves);solved=replay.is_solved()
                assert solved
            assert not cube.history and cubies_to_facelets(cube.cubies,cube.n)==facelets
            row=dict(kind=kind,seed=seed,scramble_turns=40,history_empty=True,entry_matches=True,
                     success=result.success,replay_solved=solved,moves=len(result.moves),
                     seconds=round(monotonic()-started,3),message=result.message)
            report['cases'].append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    run(sys.argv[1:] or ('fused_cube','ai_cube','burr_cube'),
        Path('reports/input-audit/2026-10-23/bandaged-portfolio-acceptance.json'))
