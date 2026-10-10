"""Direction-based selection shared by the irregular twist views."""
import math


def choose_turn(drag, candidates, minimum=.65, margin=.05):
    """Choose a signed turn by alignment, never by lever length.

    candidates contains (identifier, projected positive-turn velocity).
    Near ties are intentionally ignored rather than choosing an arbitrary axis.
    """
    length=math.hypot(*drag)
    if length<1e-8:
        return None
    ranked=[]
    for identifier,velocity in candidates:
        speed=math.hypot(*velocity)
        if speed<1e-7:
            continue
        score=sum(a*b for a,b in zip(drag,velocity))/(length*speed)
        ranked.append((abs(score),identifier,1 if score>0 else -1))
    ranked.sort(key=lambda item:item[0],reverse=True)
    if not ranked or ranked[0][0]<minimum:
        return None
    if len(ranked)>1 and ranked[0][0]-ranked[1][0]<margin:
        return None
    return ranked[0][1],ranked[0][2]
