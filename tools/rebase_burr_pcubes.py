"""Re-root the certified Burr graph at the pCubes layout and conjugate loops.

Requires the development snapshot made before replacing the old profile.
Every tree edge, complete successor set, and exported native word is checked.
The snapshots are local audit artifacts, never application dependencies.
"""
import json,pickle,struct,sys,zlib
from pathlib import Path
from collections import deque
from time import monotonic
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.bandaged_cube import BandagedCube
from solver.bandaged_reduction import geometry,locate,inverse_word
from solver.cuboid_search import packed_turn
from tools.build_bandaged_reduction import compact

BEFORE=Path('artifacts/development/burr-before-pcubes-2026-11-02')
OUT=Path('reports/optimization/2026-11-02/burr-pcubes')


def run():
    started=monotonic();OUT.mkdir(parents=True,exist_ok=True)
    old=pickle.loads((BEFORE/'old-geometry.pickle').read_bytes())
    root_cube=pickle.loads((BEFORE/'old-cube.pickle').read_bytes())
    setup=tuple(json.loads((BEFORE/'rebase.json').read_text())['path'])
    raw=(BEFORE/'burr_shapes.bin').read_bytes();size=struct.unpack_from('<I',raw,4)[0]
    header=json.loads(raw[8:8+size]);blob=zlib.decompress(raw[8+size:]);count=header['count'];width=header.get('key_bytes',14)
    table=json.loads(zlib.decompress((BEFORE/'burr_group.bin').read_bytes()))
    g=geometry('burr_cube');grid=g.grid
    assert old.shapes==g.shapes and old.grid.moves==grid.moves and old.atoms==g.atoms
    root_cube.apply_moves(setup)
    assert {frozenset(root_cube.cubies_by_home(h).pos for h in group) for group in root_cube.groups}==set(grid.base.groups)
    root_key=g.key(grid.encode(grid.base));root=locate(root_key,header,blob);assert root is not None
    parents=np.frombuffer(blob,dtype='<u4',count=count,offset=count*width).copy()
    original=parents.copy();moves=bytearray(blob[count*(width+4):]);old_moves=bytes(moves)
    inverse_index={i:grid.moves.index(inverse_word((token,))[0]) for i,token in enumerate(grid.moves)}
    i=root
    while original[i]!=0xffffffff:
        parent=int(original[i]);parents[parent]=i;moves[parent]=inverse_index[old_moves[i]];i=parent
    parents[root]=0xffffffff;moves[root]=255
    children=[[] for _ in range(count)]
    for child,parent in enumerate(parents):
        if parent!=0xffffffff:children[int(parent)].append(child)
    states=[None]*count;states[root]=grid.encode(grid.base);todo=deque((root,));visited=0
    while todo:
        parent=todo.popleft();visited+=1
        for child in children[parent]:
            move=moves[child];state=states[parent]
            assert all(grid.masks[u][pose]&(1<<move) for u,pose in enumerate(state))
            state=packed_turn(state,grid.actions[move]);states[child]=state
            assert g.key(state).to_bytes(width,'big')==blob[child*width:(child+1)*width]
            todo.append(child)
    assert visited==count
    print('Verified rooted tree',visited,flush=True)
    # Vectorised complete-neighbour closure on both limbs of each layout key.
    values=np.asarray([list(s) for s in states],dtype=np.uint8)
    lo=np.zeros((len(grid.units),256),dtype=np.uint64);hi=lo.copy()
    for u,positions in enumerate(g.positions):
        for pose,index in enumerate(positions):
            (lo if index<64 else hi)[u,(u%8)*24+pose]=np.uint64(1)<<np.uint64(index%64)
    low=np.zeros(count,dtype=np.uint64);high=low.copy()
    for u in range(len(grid.units)):low|=lo[u,values[:,u]];high|=hi[u,values[:,u]]
    dtype=np.dtype([('hi','<u8'),('lo','<u8')]);keys=np.empty(count,dtype=dtype);keys['hi']=high;keys['lo']=low
    assert np.all(keys==np.sort(keys))
    edges=0
    for move in range(len(grid.moves)):
        valid=np.ones(count,dtype=bool)
        for u in range(len(grid.units)):
            allowed=np.asarray([bool(mask&(1<<move)) for mask in grid.masks[u]])
            valid&=allowed[values[:,u]]
        child=values[valid].copy()
        for u in range(len(grid.units)):
            action=np.frombuffer(grid.actions[move][u//8],dtype=np.uint8)
            child[:,u]=action[child[:,u]]
        changed=np.any(child!=values[valid],axis=1);child=child[changed];edges+=len(child)
        lows=np.zeros(len(child),dtype=np.uint64);highs=lows.copy()
        for u in range(len(grid.units)):lows|=lo[u,child[:,u]];highs|=hi[u,child[:,u]]
        targets=np.empty(len(child),dtype=dtype);targets['hi']=highs;targets['lo']=lows
        indices=np.searchsorted(keys,targets)
        assert np.all(indices<count) and np.all(keys[indices]==targets)
    assert edges==header['edges']
    print('Verified complete graph edges',edges,flush=True)
    slots={(h,n):i for i,(h,n,c) in enumerate(g.atoms)}
    source={ (h,c):i for i,(h,n,c) in enumerate(g.atoms)}
    mapping=[None]*len(g.atoms)
    for cubie in root_cube.cubies.values():
        for normal,color in cubie.stickers.items():mapping[source[cubie.home,color]]=slots[cubie.pos,normal]
    assert sorted(mapping)==list(range(len(mapping)))
    records=[];verified=0
    for row in table['transversals']:
        result={}
        for beta,rec in row.items():
            permutation=[None]*len(mapping)
            for i,j in enumerate(rec['permutation']):permutation[mapping[i]]=mapping[j]
            word=compact(inverse_word(setup)+tuple(rec['word'])+setup)
            trial=BandagedCube.solved('burr_cube');trial.apply_moves(word);actual=[None]*len(mapping)
            for cubie in trial.cubies.values():
                for normal,color in cubie.stickers.items():actual[source[cubie.home,color]]=slots[cubie.pos,normal]
            assert actual==permutation and g.key(grid.encode(trial))==root_key
            result[str(mapping[int(beta)])]=dict(permutation=permutation,word=word);verified+=1
        records.append(result)
    table.update(geometry=grid.fingerprint,base=[mapping[i] for i in table['base']],transversals=records,
                 layout_version=2,source='pCubes Burr.xml',verified_transversals=verified)
    header.update(geometry=grid.fingerprint,root=root_key,key_bytes=width,layout_version=2)
    new_blob=blob[:count*width]+parents.astype('<u4').tobytes()+bytes(moves)
    encoded=json.dumps(header,separators=(',',':')).encode()
    (Path('solver/data')/'burr_shapes.bin').write_bytes(b'BS01'+struct.pack('<I',len(encoded))+encoded+zlib.compress(new_blob,9))
    (Path('solver/data')/'burr_group.bin').write_bytes(zlib.compress(json.dumps(table,separators=(',',':')).encode(),9))
    report=dict(layout_version=2,groups=28,shell_cells=56,layouts=count,verified_graph_edges=edges,
                verified_transversals=verified,setup=setup,geometry=grid.fingerprint,seconds=round(monotonic()-started,3))
    (OUT/'solver-certificate.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':run()
