"""Shared, complete narration timelines for playback and video export."""
from demo.cases import localized


def course_sections(case):
    parts=case.get('narration_sections')
    if parts is not None:return tuple(dict(p) for p in parts)
    count=len(case['moves'])
    return tuple(dict(start=i,end=min(i+64,count),title=localized(case['name']),
                      text=localized(case['tip']),check='') for i in range(0,count,64))


def narration(case,part,first=False):
    intro=case.get('narration_intro',localized(case.get('tip',''))) if first else ''
    from demo.irregular_cases import token
    initial=case.get('initial');spec=getattr(getattr(initial,'geometry',None),'spec',None)
    moves=case['moves'][part['start']:min(part['end'],part['start']+3)]
    from app.i18n import tr
    concrete=tr('media.first_actions',moves='、'.join(token(move,spec) for move in moves)) if moves else ''
    return ' '.join(str(s) for s in (intro,part['title'],part['text'],concrete,part.get('check','')) if s)


def action_duration(cube,move,speed=1):
    if isinstance(move,str):
        if getattr(cube,'standard_notation',False):
            from demo.formula_notation import animation_steps
            steps=animation_steps(move,cube)
        else:
            from renderer.turn import decompose_move
            steps=decompose_move(move,cube.n)
        return sum(.5*abs(step.angle)/90 for step in steps)/speed
    return .5/speed


def video_seconds(case,cube,speed=1,voice=True,parts=None):
    parts=course_sections(case) if parts is None else parts
    motion=sum(action_duration(cube,move,speed) for p in parts for move in case['moves'][p['start']:p['end']])
    holds=sum(max(2,len(narration(case,p,first=p['start']==0))/(5 if voice else 7)) for p in parts)
    return motion+holds+2


def action_description(cube,move,move_text):
    from app.i18n import tr
    if isinstance(move,str):
        try:
            from cube.notation import parse_move_full
            face,layers,count=parse_move_full(move)
            if face in 'URFDLB':
                direction=tr('media.counterclockwise' if count==3 else 'media.clockwise')
                return tr('media.face_action',face=tr('face.'+face),layers=layers,
                          angle=180 if count==2 else 90,direction=direction)
        except (ValueError,KeyError):pass
    return tr('media.axis_action',move=move_text)


def section_at(parts,index):
    return next((i for i,p in enumerate(parts) if p['start']<=index<p['end']),max(0,len(parts)-1))


def speech_language(text):
    if any('\u3040'<=c<='\u30ff' for c in text):return 'ja-JP'
    if any('\u4e00'<=c<='\u9fff' for c in text):return 'zh-CN'
    return 'en-US'
