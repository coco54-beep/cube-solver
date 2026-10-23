"""Verify full model groups, then solve visible-only random circle inputs."""
import hashlib
import json
import sys
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.circle_cube import Circle2Cube,KINDS
from cube.polyhedral import PolyhedralPuzzle,Move
from cube.polyhedral_scramble import scramble
from solver.circle2_group import table
from solver.circle_cube import solve_circle


def run(output):
    from sympy.combinatorics import Permutation,PermutationGroup
    report={'method':'fresh visible colours -> entered() -> state solve -> independent physical replay',
            'group_verification':{},'cases':[]}
    for kind in ('circle_2',)+KINDS:
        root=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
        data=table(kind);g=root.geometry;degree=len(root.colors);identity=tuple(range(degree))
        atoms=[Move(a,0,n) for a in range(3 if kind=='circle_2' else 6) for n in (1,2,3)]
        maps={m:g.permutation(m) for m in atoms}
        group=PermutationGroup([Permutation(p) for p in maps.values()]);group._schreier_sims(base=data['base'])
        assert str(group.order())==data['order']
        checked=0
        for level,(point,orbit) in enumerate(zip(data['base'],data['transversals'])):
            assert {int(beta) for beta in orbit}==set(group.basic_orbits[level])
            for beta,entry in orbit.items():
                actual=identity
                for raw in entry['word']:
                    p=maps[Move(*raw)];actual=tuple(p[x] for x in actual)
                assert actual==tuple(entry['permutation']) and actual[point]==int(beta)
                assert all(actual[b]==b for b in data['base'][:level])
                checked+=1
        filename='circle2_group.bin' if kind=='circle_2' else kind+'_group.bin'
        asset=Path('solver/data')/filename
        report['group_verification'][kind]=dict(full_order=str(group.order()),
            verified_transversals=checked,bytes=asset.stat().st_size,sha256=hashlib.sha256(asset.read_bytes()).hexdigest())
        print(kind,'verified full group',checked,flush=True)
        for seed,length in [(i,n) for n in (24,100) for i in range(12)]+[(20261023,40)]:
            source=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
            scramble(source,length,seed)
            cube=(Circle2Cube(colors=list(source.colors)) if kind=='circle_2' else
                  PolyhedralPuzzle(kind,3,list(source.colors))).entered()
            assert not cube.circle_history and cube.colors==source.colors
            before=list(cube.colors);started=monotonic()
            word=solve_circle(cube)
            assert cube.colors==before and not cube.circle_history
            replay=cube.entered()
            for move in word:replay.apply_move(move)
            assert replay.is_solved()
            report['cases'].append(dict(kind=kind,seed=seed,scramble_turns=length,
                history_empty=True,entry_matches=True,success=True,replay_solved=True,
                moves=len(word),seconds=round(monotonic()-started,3)))
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':run(Path('reports/solver-audit/2026-10-23/circle-state-acceptance.json'))
