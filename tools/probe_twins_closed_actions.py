"""Certify proposed Twins exchanges on whole material, without publishing it."""
import json,sys
from itertools import combinations,permutations
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.twins_state import TwinsState,AXES,JUMBLE,SECOND
from cube.polyhedral import Move,unit,dot


def run():
    started=monotonic();base=TwinsState();words=[]
    for a in range(20):words.append((Move(a,0,180. if a<12 else 120.),))
    for a in range(12):
        for b in range(20):
            if a==b:continue
            for angle in (JUMBLE,-JUMBLE,SECOND,-SECOND,180-JUMBLE,JUMBLE-180):
                words.append((Move(a,0,angle),Move(b,0,180. if b<12 else 120.),Move(a,0,-angle)))
    for target in range(12,20):
        perpendicular=[a for a in range(12) if abs(dot(AXES[a],AXES[target]))<1e-8]
        for triple in combinations(perpendicular,3):
            if any(abs(sum(AXES[a][i] for a in triple))>1e-8 for i in range(3)):continue
            for ordered in permutations(triple):
                for angle in (-SECOND,SECOND):
                    prefix=tuple(Move(a,0,angle) for a in ordered)
                    suffix=tuple(Move(a,0,-angle) for a in reversed(ordered))
                    for amount in (60.,120.):words.append(prefix+(Move(target,0,amount),)+suffix)
    found={};rejected=0
    for word in words:
        work=base.clone()
        try:work.apply_moves(word);action=work.aligned_permutation()
        except ValueError:rejected+=1;continue
        if action not in found:found[action]=word
    rows=[dict(word=[(m.axis,m.layer,m.amount) for m in word],action=action)
          for action,word in found.items()]
    target=Path('artifacts/research/twins/closed-actions.json');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(dict(version=1,scope='unpublished geometric prototype',
        panels=len(base.panels),pieces=len(base.solids),candidates=len(words),rejected=rejected,
        verified=rows),separators=(',',':')),encoding='utf-8')
    print('TWINS_VERIFIED',len(rows),'REJECTED',rejected,'SECONDS',round(monotonic()-started,2),flush=True)


if __name__=='__main__':run()
