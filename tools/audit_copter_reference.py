"""Deep independent replay audit of the unpublished Copter reference solver."""
import sys,json,random,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.curvy_copter import CopterState
from cube.copter_aligned import generators,observed_colors
from solver.curvy_copter import solve


def walk(seed,length,closed_mix):
    rng=random.Random(seed);cube=CopterState();count=0
    if closed_mix:
        while count<length-25:
            word=rng.choice(generators())[1]
            for move in word:cube.apply_move(move)
            count+=len(word)
    while count<length:
        choices=list(cube.moves());rng.shuffle(choices)
        for move in choices:
            try:cube.apply_move(move);break
            except ValueError:continue
        else:raise ValueError('No legal source scramble move')
        count+=1
    return cube,count


def run():
    rows=[];out=Path('reports/expansion/2026-10-27/pending-completion/copter-reference')
    out.mkdir(parents=True,exist_ok=True)
    for mixed in (False,True):
        for length in (100,300,1000):
            for seed in range(4):
                source,steps=walk(20263027+seed,length,mixed)
                data=json.loads(json.dumps(source.observation_data()))
                # An untrusted extra history field cannot influence solving.
                data['history']='not a move sequence'
                observed=CopterState.from_observation(data);before=observed.signature();started=time.monotonic()
                row=dict(seed=20263027+seed,source_steps=steps,closed_mix=mixed)
                try:
                    word=solve(observed,seconds=30.);replay=observed.clone()
                    for move in word:replay.apply_move(move)
                    assert observed_colors(replay)==tuple(face for home,face,p in replay.panels)
                    assert observed.signature()==before
                    row.update(passed=True,moves=len(word),seconds=round(time.monotonic()-started,3))
                except (ValueError,TimeoutError,AssertionError) as exc:
                    row.update(passed=False,error=str(exc),seconds=round(time.monotonic()-started,3))
                rows.append(row);print(row,flush=True)
                (out/'deep-colour-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if not all(r['passed'] for r in rows):raise SystemExit(1)


if __name__=='__main__':run()
