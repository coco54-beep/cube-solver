"""Extract our certified short leaf relations for a smaller staged rebuild."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.flower_copter_aligned import AlignedFlowerCopter,generators,source_key
from solver.flower_copter import _profile
from solver.polyhedral import apply_word
from cube.polyhedral import Move

if __name__=='__main__':
    c=AlignedFlowerCopter();g=c.geometry;data=_profile.data();left=set(range(120));leaves=[]
    while left:
        orbit={min(left)};queue=list(orbit)
        for s in queue:
            for action,w in generators():
                if action[s] not in orbit:orbit.add(action[s]);queue.append(action[s])
        left-=orbit
        if all(len(g.pieces[g.stickers[s].piece])==1 for s in orbit):leaves.append(orbit)
    records=[r for row in data['transversals'] for r in row.values()]+data.get('leaf_stages',[])
    tools=[]
    for orbit in leaves:
        candidates=[]
        for r in records:
            word=tuple(Move(*m) for m in r['word']);p=apply_word(g,word)
            support={i for i,j in enumerate(p) if i!=j}
            if len(support)==3 and support<=orbit:candidates.append(word)
        best=min(candidates,key=len);tools.append([[m.axis,m.layer,m.amount] for m in best])
    target=Path('artifacts/research/flower-copter/leaf-tools-dwg.json');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(dict(source=source_key(),tools=tools),separators=(',',':')),encoding='utf-8')
    print('Own verified leaf tools:',[len(w) for w in tools])
