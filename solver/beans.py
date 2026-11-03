"""Colour-only bean sorting: free ring targets and short local three-cycles."""
from functools import lru_cache
from heapq import nsmallest

import numpy as np

from cube.dial_beans import KINDS,LOOP
from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import simplify
from solver.polyhedral_reduction import Transports,joined_length


@lru_cache(maxsize=2)
def actions(kind):
    cube=PolyhedralPuzzle(kind,KINDS[kind]);g=cube.geometry
    moves=tuple(Move(m.axis,0,k*g.spec.step(m.axis)) for m in cube.moves()
                for k in range(1,g.spec.order(m.axis)))
    return moves,np.asarray([g.inverse_permutation(m) for m in moves],dtype=np.int16)


def scores(states,count):
    rings=states.reshape(-1,count,LOOP)
    counts=np.stack([(rings==c).sum(axis=2,dtype=np.int16) for c in range(count)],axis=2)
    return (counts*counts).sum(axis=(1,2)),counts.max(axis=2).sum(axis=1)


def improve_rings(cube,check,width=24,depth=3):
    """Bounded lookahead for bulk colour grouping, with a complete fallback."""
    moves,perms=actions(cube.puzzle_kind);count=KINDS[cube.puzzle_kind]
    axes=np.asarray([m.axis for m in moves]);m=len(moves)
    states=np.asarray([cube.colors],dtype=np.int16);paths=[()];last=np.asarray([-1])
    initial=int(scores(states,count)[0][0]);best_score=initial;best=()
    visited={states[0].tobytes()}
    for _ in range(depth):
        check()
        raw=states[:,perms].reshape(-1,states.shape[1])
        parents=np.repeat(np.arange(len(states)),m);choices=np.tile(np.arange(m),len(states))
        keep=(last[parents]!=axes[choices]) & np.any(raw!=states[parents],axis=1)
        raw=raw[keep];parents=parents[keep];choices=choices[keep]
        if not len(raw):break
        pair,purity=scores(raw,count)
        solved=np.flatnonzero(purity==count*LOOP)
        if len(solved):
            i=int(solved[0]);return paths[int(parents[i])]+(moves[int(choices[i])],),True
        order=np.lexsort((np.arange(len(raw)),-purity,-pair))
        top=int(order[0])
        if int(pair[top])>best_score:
            best_score=int(pair[top]);best=paths[int(parents[top])]+(moves[int(choices[top])],)
        selected=[];next_paths=[];next_last=[]
        for i in order:
            identity=raw[i].tobytes()
            if identity in visited:continue
            visited.add(identity);selected.append(int(i));next_last.append(int(axes[choices[i]]))
            next_paths.append(paths[int(parents[i])]+(moves[int(choices[i])],))
            if len(selected)>=width:break
        if not selected:break
        states=raw[selected];paths=next_paths;last=np.asarray(next_last)
    return best,False


def nearest_target(colors,count):
    """Exact maximum-overlap one-to-one assignment of colours to rings."""
    weights=[[colors[r*LOOP:(r+1)*LOOP].count(c) for c in range(count)] for r in range(count)]
    best={0:(0,())}
    for mask in range(1<<count):
        if mask not in best:continue
        row=mask.bit_count()
        if row==count:continue
        score,chosen=best[mask]
        for color in range(count):
            if mask&(1<<color):continue
            hits=weights[row][color];candidate=(score+1000*hits+hits*hits,chosen+(color,))
            nxt=mask|(1<<color)
            if nxt not in best or candidate[0]>best[nxt][0]:best[nxt]=candidate
    return [c for c in best[(1<<count)-1][1] for _ in range(LOOP)]


def transports_for(cube,check,cancel):
    from solver.dial_beans import primitive
    word,base=primitive(cube)
    transport=Transports(cube,tuple(range(len(cube.colors))),base,cancel,both_directions=True)
    depths=np.full(len(transport.parents),255,dtype=np.uint8)
    depths[transport._frontier]=0;level=0
    while transport._expand():
        check();level+=1;depths[transport._frontier]=level
    return word,transport,depths


def finish_colors(cube,prefix,word,transport,depths,check,progress):
    """Fix two or three visible colours per macro; equal beads are donors."""
    work=cube.entered();path=tuple(prefix);order=work.geometry.spec.turn_order
    target=nearest_target(work.colors,KINDS[work.puzzle_kind]);n=len(target)
    total=sum(a!=b for a,b in zip(work.colors,target));done=0
    macro_cache={}
    while not work.is_solved():
        check();colors=work.colors;bad=[i for i in range(n) if colors[i]!=target[i]]
        if not bad:break
        available=[[] for _ in range(KINDS[work.puzzle_kind])]
        misplaced=[[] for _ in available]
        for i,c in enumerate(colors):available[c].append(i)
        for i in bad:misplaced[colors[i]].append(i)
        candidates={}
        for a in bad:
            for b in misplaced[target[a]]:
                needed=target[b]
                choices=available[needed] if needed==colors[a] else misplaced[needed]
                for c in choices:
                    if c==a or c==b:continue
                    cycle=(a,c,b);code=transport._canon(*cycle)
                    gain=2+int(colors[c]!=target[c] and colors[c]!=colors[a] and target[c]==colors[a])
                    candidates[code]=(cycle,gain)
        if not candidates:raise ValueError('No balanced colour cycle found')
        shortlist=nsmallest(24,candidates,key=lambda c:((len(word)+2*int(depths[c]))/candidates[c][1],c))
        best=None
        for code in shortlist:
            cycle,gain=candidates[code]
            macro=macro_cache.get(code)
            if macro is None:
                macro=transport.conjugate(cycle,word);macro_cache[code]=macro
            cost=joined_length(path,macro,order)-len(path)
            key=(cost/gain,-gain,cost,code)
            if best is None or key<best[0]:best=(key,macro)
        for move in best[1]:work.apply_move(move)
        path=simplify(path+tuple(best[1]),order)
        remaining=sum(a!=b for a,b in zip(work.colors,target))
        if remaining>=len(bad):raise ValueError('Colour cycle did not improve the entered state')
        done=total-remaining
        if progress:progress(done,max(total,1))
    return tuple(path)


def solve_beans(cube,cancel=None,progress=None):
    def check():
        if cancel and cancel():raise InterruptedError()
    def verified(result):
        replay=cube.entered()
        for move in result:check();replay.apply_move(move)
        if not replay.is_solved():raise ValueError('Bean colour solution replay failed')
        if progress:progress(1,1)
        return tuple(result)
    check();work=cube.entered();prefix=()
    # Coarse turns move many correct colours together. Keep the direct plan
    # as a competitor, since a higher purity score is not a move-count proof.
    for _ in range(4):
        word,_=improve_rings(work,check)
        if not word:break
        for move in word:work.apply_move(move)
        prefix=simplify(prefix+tuple(word),cube.geometry.spec.turn_order)
        if work.is_solved():return verified(prefix)
    word,transport,depths=transports_for(cube,check,cancel)
    plans=[finish_colors(cube,(),word,transport,depths,check,None)]
    if prefix:plans.append(finish_colors(work,prefix,word,transport,depths,check,progress))
    return verified(min(plans,key=len))
