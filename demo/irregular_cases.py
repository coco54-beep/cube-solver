"""Mechanism-aware examples for irregular puzzles through order five.

Examples start from the inverse of the displayed sequence, like the ordinary
cube lessons. No example reads, scrambles, or changes the user's input draft.
"""
from functools import lru_cache

from cube.polyhedral import PolyhedralPuzzle, Move
from demo.cases import CASE_2X2, CASE_3X3, CASE_4X4, CASE_5X5
from demo.mastermorphix_cases import CASE_MASTERMORPHIX


def text(zh, en):
    return {'zh':zh, 'en':en, 'ja':en}


def token(move):
    if isinstance(move,str):
        return move
    suffix="'" if move.amount>1 else ''
    return f'A{move.axis+1}:{move.layer+1}{suffix}'


def case(name, moves, tip):
    return {'name':name, 'moves':tuple(moves),
            'text':' '.join(map(token,moves)), 'tip':tip}


def step(title, desc, cases):
    return {'title':title, 'desc':desc, 'cases':cases}


@lru_cache(maxsize=32)
def lessons(kind,n):
    if not 2<=n<=5:
        raise ValueError('Teaching demos support orders up to five')
    if kind=='mirror':
        originals={2:CASE_2X2,3:CASE_3X3,4:CASE_4X4,5:CASE_5X5}[n]
        result=[]
        for index, original in enumerate(originals):
            title = text(f'形状复位阶段 {index+1}', f'Shape restoration stage {index+1}')
            result.append(step(title,text(
                '镜面魔方按块的形状和大小定位。U/D、R/L、F/B 为转动面标签；用形状匹配替代普通魔方的颜色匹配。'
                '本组沿用对应阶数的层先法或降阶动作，每个示例完成公式后恢复其初始构造前的形状。',
                'Match piece shapes and sizes using the U/D, R/L and F/B axes. '
                'These examples use the corresponding cube-order algorithms; completing each formula restores its example.'),
                [case(text(f'形状复位示例 {i+1}',f'Shape example {i+1}'),c['moves'],text(
                    '先确认模型上的面标签，逐步观察块形状；左右箭头撤回或执行一个动作。',
                    'Follow the face labels and piece shapes. Left undoes one action; right executes one action.'))
                 for i,c in enumerate(original['cases'])]))
        return result
    if kind=='mastermorphix':
        result=list(CASE_MASTERMORPHIX if n==3 else CASE_MASTERMORPHIX[:2])
        result[0]=dict(result[0],desc=text(
            f'{n} 阶粽子使用对应阶数的立方体内部结构。U/D、F/B、R/L 表示机械转轴，四种表面颜色不等于六个转动面。'
            '撇号表示反向，2 表示半圈。观察单次转动怎样同时改变块形状和配色。',
            f'The {n}-order Mastermorphix has a cube mechanism. Face letters describe mechanical axes, '
            'not the four surface colors. A prime reverses a turn; 2 denotes a half turn.'))
        if n != 3:
            result[1] = dict(result[1], title=text('角块组合与朝向', 'Corner sequences and orientation'), desc=text(
                '按机械转轴观察角块的移动和朝向。二阶只有角块；四、五阶还要处理中心和棱块。'
                '这里是独立动作示例，完成显示的整段公式后回到该示例的还原状态。',
                'Observe corner positions and orientation around mechanical axes. Order two has only corners; '
                'orders four and five also require centers and edges. Each example restores its prepared state.'))
        if n>=4:
            result.insert(1,step(text('中心与棱的降阶动作','Center and edge reduction moves'),text(
                '先把同一目标区域的中心及棱组合，再处理降阶后的角棱。Rw 表示从 R 侧一起转最外两层；'
                '完整执行本案例的交换动作，再观察中心、棱和外形的复位。',
                'Combine centers and wings before solving the reduced corner/edge puzzle. Rw turns the outer two layers.'),[
                case(text('宽层转动','Wide turn'),('r',),text('观察外侧两层同时转动。','Watch two layers turn together.')),
                case(text('中心与棱组合示例','Center/wing combination'),('r','U',"r'","U'"),text(
                    '中途其他块也会移动，完成整段后再判断效果。','Judge the effect after the complete sequence.')),
                case(text('带准备动作的交换','Setup and interchange'),('F','r','U',"r'","U'","F'"),text(
                    'F 是准备动作，最后用 F\' 撤回准备动作。','F sets up the sequence; F\' undoes that setup.'))]))
        return result

    cube=PolyhedralPuzzle(kind,n)
    g=cube.geometry
    inverse=lambda move:move.inverse(g.spec.turn_order)
    # Pyraminx tip layer and body layer are different legal bands.
    body_layer=next((i for i,b in enumerate(g.layers[0]) if len(b)>1),0)
    a,b=Move(0,body_layer),Move(1,body_layer)
    angle=360//g.spec.turn_order
    notation=text(f'A1、A2 等对应拧动页的转轴编号；冒号后的数字是层号（从轴侧向里数），撇号表示反向。每次转动 {angle}°。'
                  '案例从所示公式的逆操作构造，完成整段后恢复本案例。',
                  f'A1, A2, etc. identify the numbered model axes. The number after : is the layer from that axis side; '
                  f'a prime reverses a turn. Each turn is {angle} degrees. Each example begins with its formula inverse.')
    result=[step(text('认识转轴与转层','Axes and layers'),notation,[
        case(text('单层正向转动','Forward layer turn'),(a,),text(
            '按下一步，观察指定轴的一层转动。', 'Press Next to turn one layer on the indicated axis.')),
        case(text('单层反向转动','Reverse layer turn'),(inverse(a),),text(
            '带撇号的动作与正向动作相反。', 'A prime reverses the forward turn.'))])]
    if kind=='pyraminx':
        tips=[Move(i,0) for i,layers in enumerate(g.layers) if len(layers[0])==1]
        if tips:
            result.append(step(text('尖角独立复位','Independent tip alignment'),text(
                '尖角每次转 120°，可独立对齐相邻面。二阶只转尖角，中间三角块不动；更高阶可在主体复位后处理尖角。',
                'Tips turn independently by 120 degrees. On order two, the face-center triangles remain fixed.'),[
                case(text(f'对齐尖角 {tip.axis+1}',f'Align tip {tip.axis+1}'),(tip,),text(
                    '观察只有对应尖角移动。','Only the selected tip moves.')) for tip in tips]))
    if n!=2 or kind!='pyraminx':
        insertion=(a,b,inverse(a))
        exchange=(a,b,inverse(a),inverse(b))
        result.append(step(text('准备、插入与交换','Setup, insertion and interchange'),text(
            '先观察 A1、A2 的配合，再撤回准备动作。交换示例由 A B A\' B\' 构成；它的作用取决于当前模型的实际结构。'
            '下列案例用于观察局部动作和复位，实际录入后的完整还原请使用求解功能。',
            'Observe setup and undo moves using this puzzle\'s actual mechanism. These local examples demonstrate '
            'A B A\' B\' and their restoration; use Solve for a complete entered scramble.'),[
            case(text('三步插入示例','Three-move insertion'),insertion,notation),
            case(text('四步交换示例','Four-move interchange'),exchange,notation)]))
    if len(g.layers[0])>body_layer+1:
        inner=Move(0,body_layer+1)
        result.append(step(text('内层组合与降阶准备','Inner-layer combination'),text(
            '高阶增加了内层和可移动的中心、棱。先学习准确选择内层，再观察内层与外层组合时各类块的运动。'
            '每段动作必须完整执行；中间帧的变化并不代表整段结束后的效果。',
            'Higher orders add inner layers and movable center/edge pieces. Observe a full inner/outer sequence.'),[
            case(text('单独转内层','Turn an inner layer'),(inner,),notation),
            case(text('内外层交换示例','Inner/outer interchange'),
                 (inner,b,inverse(inner),inverse(b)),notation)]))
    return result
