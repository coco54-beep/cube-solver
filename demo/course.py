"""Verified full worked courses, with bounded sections and no move truncation."""
import json,zlib
from functools import lru_cache
from pathlib import Path


def sections(initial,moves,final,chunk=64):
    from demo.expanded_checkpoints import features
    expected=features(final);keys=tuple(sorted(expected));total=len(keys)
    work=initial.clone();masks=[]
    def mask(cube):
        current=features(cube)
        return sum(1<<i for i,key in enumerate(keys) if current.get(key)==expected[key])
    masks.append(mask(work))
    for move in moves:work.apply_move(move);masks.append(mask(work))
    suffix=(1<<total)-1
    for i in range(len(masks)-1,-1,-1):suffix &= masks[i];masks[i]=suffix
    result=[]
    for start in range(0,len(moves),chunk):
        end=min(start+chunk,len(moves));done=masks[end].bit_count()
        result.append(dict(start=start,end=end,title=f'完整实例 · 第 {len(result)+1} 段',
            text=f'本段执行第 {start+1} 至 {end} 步。注意模型标出的实际转轴和层，保持与示例相同的握法。',
            check=f'本段结束后，{done}/{total} 个可观察目标与最终状态一致，后续示例步骤不再改变这些目标。'))
    return result


def record(initial,result):
    from app.session import encode
    from demo.solutions import verified_solution_lessons
    from demo.expanded_tutorials import tutorial
    from demo.expanded_curriculum import work_plan
    case=verified_solution_lessons(initial,result)[0]['cases'][0]
    moves=case['moves'];final=initial.clone()
    for move in moves:final.apply_move(move)
    if not final.is_solved():raise ValueError('Course replay did not solve')
    guide=tutorial(initial.puzzle_kind)
    chunks=sections(initial,moves,final)
    plan=work_plan(initial.puzzle_kind)
    for i,part in enumerate(chunks):
        part['text']+=plan[min(len(plan)-1,i*len(plan)//max(1,len(chunks)))]
    from candidate_puzzles import BY_KIND
    return dict(order=BY_KIND[initial.puzzle_kind].n,initial=encode(initial),moves=encode(tuple(moves)),
                sections=chunks,intro=guide.intro,goals=list(guide.goals))


@lru_cache(maxsize=1)
def catalogue():
    data=json.loads(zlib.decompress((Path(__file__).parent/'data/expanded_courses.bin').read_bytes()))
    if data.get('version')!=1:raise ValueError('Unsupported course data')
    return data['models']


@lru_cache(maxsize=2)
def _verified(kind,n):
    from app.session import decode
    from demo.irregular_cases import text
    data=catalogue()[kind]
    if data['order']!=n:raise ValueError('Course order mismatch')
    initial=decode(data['initial']);moves=decode(data['moves'])
    replay=initial.clone()
    for move in moves:replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Course data no longer matches the model')
    case=dict(name=text('完整原创实例课程','Full original worked course'),initial=initial,
        moves=tuple(moves),text=text(f'完整保留 {len(moves)} 步，可按段跳转、聆听讲解或导出视频。',
                                  f'All {len(moves)} moves are retained. Navigate sections, listen or export.'),
        tip=text('请先核对示例起始块位；其他实物打乱请用录入求解。','Match this example start. Use input solving for another scramble.'),
        teaching_kind='full_worked_course',show_all=True,
        narration_intro='这是一次完整的独立打乱还原实例。'+data['intro']+'请先核对起始块位和握法。',
        narration_sections=tuple(dict(p) for p in data['sections']))
    return [dict(title=text('完整实例课程 · 全步骤','Full worked course · Every move'),
        desc=text('从独立打乱状态求解并验证的完整过程；分段讲解不删减步骤，也不表示任意实物只有这一条解法。',
                  'A verified complete solution of an independent scramble. Sections retain every move.'),cases=[case])]


def load(kind,n):
    """Reuse verified resources, returning fresh mutable state to each player."""
    from copy import deepcopy
    result=[]
    for step in _verified(kind,n):
        restored=deepcopy({k:v for k,v in step.items() if k!='cases'});restored['cases']=[]
        for case in step['cases']:
            data=deepcopy({k:v for k,v in case.items() if k not in ('initial','moves')})
            data['initial']=case['initial'].clone();data['moves']=case['moves'];restored['cases'].append(data)
        result.append(restored)
    return result
