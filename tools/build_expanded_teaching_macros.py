"""Select short, isolated three-piece cycles and verify complete effects.

This reads existing mechanism tables and never rebuilds solver data. Output
contains only a few teaching words, not a second collection of solver tables.
"""
import os,sys,json,hashlib,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from candidate_puzzles import REQUESTED
from demo.expanded_support import make_cube,legal_moves
from cube.polyhedral import Move
from solver.polyhedral import apply_word,inverse_word,simplify


def cycle_support(g,action):
    support=tuple(p for p,slots in enumerate(g.pieces) if any(action[s]!=s for s in slots))
    if len(support)!=3:return None
    mapping={p:g.stickers[action[g.pieces[p][0]]].piece for p in support}
    if set(mapping.values())!=set(support) or any(p==q for p,q in mapping.items()):return None
    if any({action[s] for s in g.pieces[p]}!=set(g.pieces[mapping[p]]) for p in support):return None
    if any(action[action[action[s]]]!=s for s in range(len(action))):return None
    return support


def main():
    output={}
    selected=set(sys.argv[1:])
    if selected:
        output=json.loads(Path('demo/data/expanded_macros.json').read_text(encoding='utf-8'))['models']
    for entry in REQUESTED:
        if selected and entry.kind not in selected:continue
        output.pop(entry.kind,None)
        cube=make_cube(entry.kind,entry.n)
        if hasattr(cube,'cubies'):continue
        choices=[]
        if entry.mechanism=='extended':
            from solver.cuboid_extensions import extension_mechanism,expand
            adapter,panels,_,_=extension_mechanism(entry.kind)
            for i,raw in enumerate(adapter.words):choices.append(tuple(raw))
            data=json.loads(zlib.decompress((Path('solver/data')/(entry.kind+'_extension_group.bin')).read_bytes()))
            for row in data['transversals']:
                for item in row.values():
                    action=item['permutation']
                    if len({panels[i][0] for i,v in enumerate(action) if i!=v})==3:
                        choices.append(tuple(expand(entry.kind,tuple(Move(*m) for m in item['word']))))
            verified=[];roles=set();g=cube.geometry
            from cube.mastermorphix import IDENTITY
            for word in sorted(choices,key=len):
                if len(word)>100:continue
                state=cube.clone()
                try:
                    for move in word:state.apply_move(move)
                except ValueError:continue
                moved=tuple(i for i,f in enumerate(state.frames) if f!=IDENTITY)
                if len(moved)!=3 or min(moved)<27:continue
                role=len(g.pieces[moved[0]])
                if role in roles:continue
                check=state.clone()
                for _ in range(2):
                    for move in word:check.apply_move(move)
                if check.frames!=cube.frames:continue
                roles.add(role)
                verified.append(dict(word=[list((m.axis,m.layer,m.amount)) for m in word],pieces=list(moved),role='extension-'+str(role)))
                if len(roles)==2:break
        else:
            g=cube.geometry
            options=legal_moves(cube)
            neighbours={p:{p} for p in range(len(g.pieces))}
            for move in options:
                action=g.permutation(move)
                for p,slots in enumerate(g.pieces):
                    neighbours[p].add(g.stickers[action[slots[0]]].piece)
            orbit_of={};remaining=set(neighbours);orbit_index=0
            while remaining:
                found={min(remaining)};todo=list(found)
                while todo:
                    for p in neighbours[todo.pop()]-found:found.add(p);todo.append(p)
                for p in found:orbit_of[p]=orbit_index
                remaining-=found;orbit_index+=1
            for a in options:
                for b in options:
                    if a.axis==b.axis:continue
                    inv=inverse_word((a,b),g.spec.turn_order)
                    comm=(a,b)+inv
                    choices.extend((comm,comm*2,comm*3))
                    nested=comm+(b,)+tuple(inverse_word(comm,g.spec.turn_order))+(b.inverse(g.spec.turn_order),)
                    choices.append(nested)
            if entry.kind in ('pyraminx_diamond','mirror_kilominx','mirror_megaminx'):
                # [a b a^-1, c] isolates overlaps unavailable to a four-move
                # commutator. Every candidate is still checked on all panels.
                for a in options:
                    for b in options:
                        if a.axis==b.axis:continue
                        setup=(a,b,a.inverse(g.spec.turn_order))
                        for c in options:
                            if c.axis in (a.axis,b.axis):continue
                            choices.append(setup+(c,)+tuple(inverse_word(setup,g.spec.turn_order))+(c.inverse(g.spec.turn_order),))
            data_kind=entry.kind
            path=Path('solver/data')/(data_kind+'_expanded_group.bin')
            if path.exists():
                data=json.loads(zlib.decompress(path.read_bytes()))
                for row in data['transversals']:
                    for item in row.values():
                        if len(item['word'])<=80 and cycle_support(g,item['permutation']):
                            choices.append(tuple(Move(*m) for m in item['word']))
            if entry.kind=='master_brilic':
                from solver.master_brilic import _asset
                choices.extend(tuple(Move(*m) for m in item['word']) for item in _asset()['cycles'].values())
            verified=[];roles=set();seen=set()
            for word in sorted(choices,key=len):
                if len(word)>100 or word in seen:continue
                seen.add(word);action=apply_word(g,word);support=cycle_support(g,action)
                if support is None:continue
                role=(orbit_of[support[0]],len(g.pieces[support[0]]))
                if role in roles:continue
                # A silver body's in-place orientation must be checked too.
                if isinstance(getattr(cube,'pieces',None),dict):
                    state=cube.clone()
                    for move in word:state.apply_move(move)
                    if any(state.pieces[p]!=cube.pieces[p] for p in range(len(g.pieces)) if p not in support):continue
                roles.add(role)
                verified.append(dict(word=[list((m.axis,m.layer,m.amount)) for m in word],pieces=list(support),role=list(role),
                                     permutation_sha256=hashlib.sha256(repr(action).encode()).hexdigest()))
        if verified:output[entry.kind]=verified
        print(entry.kind,[(v['role'],len(v['word'])) for v in verified],flush=True)
    path=Path('demo/data/expanded_macros.json')
    path.write_text(json.dumps(dict(version=1,models=output),separators=(',',':')),encoding='utf-8')
    print('models',len(output),'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':main()
