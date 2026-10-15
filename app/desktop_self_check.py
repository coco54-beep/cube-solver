"""Frozen-package solver smoke check, without a window or preference writes."""
import json
from pathlib import Path
from app.constants import APP_VERSION

def run(report_path):
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    from cube.cube_n import CubeN,MAX_N
    from cube.conversion import cubies_to_facelets
    from cube.polyhedral import PolyhedralPuzzle,Move
    from solver.solver3 import solve_3x3
    from solver.solver4 import solve_4x4
    from solver.solver_n import solve_nxn
    from solver.polyhedral import solve_polyhedral
    from solver.minx_plans import orbit_plan
    results=[]
    root=Path(__file__).resolve().parents[1]
    assert (root/'p4_table.bin').stat().st_size>100000000
    assert (root/'assets/fonts/NotoSansSC.ttf').is_file()
    assert (root/'ui/kv/app.kv').is_file()
    for n in (3,4,6,17):
        cube={3:Cube3.solved,4:Cube4.solved}.get(n,lambda:CubeN.solved(n))()
        cube.apply_moves(['R','U',"F'",'2R'] if n>3 else ['R','U',"F'"])
        if n==3:result=solve_3x3(cubies_to_facelets(cube.cubies,3))
        elif n==4:result=solve_4x4(cube)
        else:result=solve_nxn(cube)
        assert result.success,result.message
        cube.apply_moves(result.moves);assert cube.is_solved(),n
        results.append({'kind':'cube','order':n,'steps':len(result.moves),'replay':'pass'})
    for kind,n in (('fto',3),('football',3),('pentahedron',2)):
        cube=PolyhedralPuzzle(kind,n);cube.apply_move(cube.moves()[0])
        word=solve_polyhedral(cube.entered())
        for move in word:cube.apply_move(move)
        assert cube.is_solved(),kind
        results.append({'kind':kind,'order':n,'steps':len(word),'replay':'pass'})
    from solver.polyhedral import piece_orbits
    for n in range(4,14):
        cube=PolyhedralPuzzle('megaminx',n)
        targets={i:o for i,o in enumerate(piece_orbits('megaminx',n)) if len(o)>1}
        assert orbit_plan(cube,targets) is not None,n
    assert MAX_N==17
    from demo.algorithm_library import catalog
    from solver.formula_finishes import _tables
    from demo.practice import PracticeSession
    from demo.learning import LearningProgress
    formula_cases=sum(len(group['cases']) for group in catalog()['sets'])
    assert formula_cases==6060
    finishes,_=_tables()
    assert all(finishes.get(p) for p in ('3x3','Megaminx','SQ1'))
    practice=PracticeSession(progress=LearningProgress(),clock=lambda:10.)
    practice.configure('2x2',['CLL'])
    practice.next_question()
    assert practice.start()
    assert practice.stop() is not None and practice.penalty('+2')
    assert practice.stats()['best']==2.
    data={'status':'pass','version':APP_VERSION,'max_n':MAX_N,'samples':results,
          'minx_precomputed_orders':list(range(4,14)), 'formula_cases':formula_cases,
          'formula_finish_states':{p:len(rows) for p,rows in finishes.items()},'practice':'pass'}
    Path(report_path).write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data
