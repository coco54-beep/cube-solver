"""Shorten existing universal Mixup loop groups; never reads input cases."""
import json
import sys
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.weighted_group_builder import build
from solver.mixup_group import GeometryGroup,geometry_fingerprint
from cube.mixup import MixupSliceMove
from cube.polyhedral import Move


def compact(word):
    result=[]
    for a,l,n,layers in word:
        if result and result[-1][:2]==(a,l) and result[-1][3]==layers:n=(result.pop()[2]+n)%8
        if n:result.append((a,l,n,layers))
    return tuple(result)


def inverse_word(word):return tuple((a,l,-n%8,layers) for a,l,n,layers in reversed(word))


def preserve_catalogue(old,new):
    """Inner-cycle helpers still need the original universal primitive list."""
    strong=list(old['strong']);offset=len(strong)
    for record in new['strong']:
        word=new['moves'][record['original']]
        strong.append(dict(original=None,shortcut=word,permutation=record['permutation'],product=[]))
    transversals=[{beta:dict(permutation=entry['permutation'],
                           product=[offset+ref for ref in entry['product']])
                   for beta,entry in orbit.items()} for orbit in new['transversals']]
    return dict(new,strong=strong,moves=old['moves'],transversals=transversals,weighted_transversals=True)


def rebuild(kind):
    path=Path('solver/data')/(kind+'_group.bin')
    data=json.loads(zlib.decompress(path.read_bytes()));degree=data['degree'];pool={}
    for record in data['strong']:
        if record['original'] is None:continue
        p=tuple(record['permutation'])
        w=compact(tuple((a,l,n,tuple(layers)) for a,l,n,layers in data['moves'][record['original']]))
        if p not in pool or len(pool[p])>len(w):pool[p]=w
    # Union-find obtains every exact point orbit of the original generators.
    links=list(range(degree))
    def find(a):
        while links[a]!=a:links[a]=links[links[a]];a=links[a]
        return a
    for p in pool:
        for a,b in enumerate(p):links[find(a)]=find(b)
    orbits={}
    for a in range(degree):orbits.setdefault(find(a),[]).append(a)
    expected=[{int(b) for b in orbit} for orbit in data['transversals']]
    records=build(pool,data['base'],expected,orbits.values(),compact,inverse_word,
                  report=lambda *args:print(kind,*args,flush=True))
    old=GeometryGroup(kind,path);root=(0,)*len(old.model.cube.solids)
    checked=0;words=[];strong=[];transversals=[]
    for orbit in records:
        level={}
        for beta,entry in orbit.items():
            word=entry['word'];frames=root;features=old.model.describe(frames)[0]
            for a,l,n,layers in word:
                move=MixupSliceMove(a,l,n,layers) if layers else Move(a,l,n)
                result=old.model.apply(frames,features,move)
                if result is None:raise ValueError('Compiled word contains an illegal physical move')
                frames,features=result
            if old.element(frames)!=tuple(entry['permutation']):raise ValueError('Compiled physical permutation mismatch')
            product=[]
            if word:
                product=[len(strong)]
                strong.append(dict(original=len(words),permutation=entry['permutation'],product=[]))
                words.append(word)
            level[beta]=dict(permutation=entry['permutation'],product=product);checked+=1
        transversals.append(level)
    assert data['geometry']==geometry_fingerprint(kind)
    new=preserve_catalogue(data,dict(data,strong=strong,moves=words,transversals=transversals))
    target=Path('artifacts/development')/(kind+'-weighted-group.bin')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(zlib.compress(json.dumps(new,separators=(',',':')).encode(),9))
    print('VERIFIED',kind,checked,'max_word',max(map(len,words)),'bytes',target.stat().st_size,flush=True)


if __name__=='__main__':
    for kind in sys.argv[1:]:rebuild(kind)
