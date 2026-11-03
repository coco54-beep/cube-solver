"""Original worked-solution checkpoints derived from real piece states.

These are observable progress checks, not invented human-method phase names.
An earlier checkpoint counts a piece only if every remaining move leaves it
at the demonstrated final target.
"""
from types import SimpleNamespace


def features(cube):
    if hasattr(cube,'cubies'):
        return {piece.home:(position,piece.frame,tuple(sorted(piece.stickers.items())))
                for position,piece in cube.cubies.items()}
    if isinstance(getattr(cube,'pieces',None),dict):
        from cube.mirror_tower import frame_key
        return {piece.home:(position,frame_key(piece.frame)) for position,piece in cube.pieces.items()}
    if hasattr(cube,'frames'):
        return {p:frame for p,frame in enumerate(cube.frames) if cube.geometry.pieces[p]}
    return {p:tuple(cube.colors[s] for s in slots) for p,slots in enumerate(cube.geometry.pieces) if slots}


def stages(initial,moves,final):
    from demo.irregular_cases import text
    expected=features(final);keys=tuple(sorted(expected));total=len(keys)
    if not total or len(moves)<4:return []
    def mask(cube):
        current=features(cube)
        return sum(1<<i for i,k in enumerate(keys) if current.get(k)==expected[k])
    work=initial.clone();masks=[mask(work)]
    for move in moves:work.apply_move(move);masks.append(mask(work))
    suffix=(1<<total)-1
    for i in range(len(masks)-1,-1,-1):suffix &= masks[i];masks[i]=suffix
    start=masks[0].bit_count();cuts=[];last=0
    for fraction in (.25,.5,.75):
        threshold=start+max(1,int((total-start)*fraction+.9999))
        index=next((i for i in range(last+1,len(moves)) if masks[i].bit_count()>=threshold),None)
        if index is not None:cuts.append(index);last=index
    if not cuts:return []
    cuts.append(len(moves));result=[];begin=0
    for i,end in enumerate(cuts,1):
        done=masks[end].bit_count()
        result.append(SimpleNamespace(name=f'original_checkpoint_{i}',moves=list(moves[begin:end]),
            description=text(f'归位检查点 {i}：{done}/{total} 块',f'Checkpoint {i}: {done}/{total} pieces'),
            teaching_description=text(
                f'执行本段后，{done}/{total} 个目标块与本次最终状态一致，后续动作不再改变这些目标。先核对本段起点，再看本段结束时的归位变化；继续下一段完成其余块。',
                f'After this section, {done}/{total} target pieces match the final state and remain there. Match this section start, inspect the new placements, then continue.')))
        begin=end
    return result
