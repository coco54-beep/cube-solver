"""Mechanism-aware examples for irregular puzzles through order five.

Examples start from the inverse of the displayed sequence, like the ordinary
cube lessons. No example reads, scrambles, or changes the user's input draft.
"""
from functools import lru_cache

from cube.polyhedral import PolyhedralPuzzle, Move
from demo.cases import CASE_2X2, CASE_3X3, CASE_4X4, CASE_5X5
from demo.mastermorphix_cases import CASE_MASTERMORPHIX


_JA = {
    "Top and bottom turns": "上下層の回転",
    "Turn the top and bottom layers independently, then reverse the turn.":
        "SQ1 の上下層はそれぞれ回せます。まずパーツの位置変化を観察し、逆向きに戻してみましょう。",
    "Turn the top layer": "上層を回す",
    "Observe the edge and corner order after one turn.": "1手回した後の辺と角の並びを観察します。",
    "Turn the bottom layer": "下層を回す",
    "The bottom layer uses its own turn direction.": "下層は独自の方向記号で回します。",
    "Slash and shape change": "斜め切断と形状変化",
    "The slash is legal only when no corner crosses the cut. It swaps half of each layer.":
        "切断線上に角がまたがっていないときだけ斜め切断できます。上下層の半分を交換します。",
    "Align layers, then restore with a slash": "層を合わせてから斜め切断で復元",
    "This example starts with a changed shape. All three moves restore the cube shape; each layer unit is 30 degrees.":
        "本例は変形した状態から始まります。3つの動作で立方体の形に戻ります。各層の1単位は30°です。",
    "Shape and layer turns": "形状と層の回転",
    "Right-layer turn": "右層の回転",
    "Observe the right-side pieces turn.": "右側のパーツが回る様子を観察します。",
    "Turn sequence and restoration": "連続回転と復元",
    "Complete the sequence to restore the example state.": "公式を最後まで実行すると形状とパーツが戻ります。",
    "Silver pieces and layers": "銀色パーツと層",
    "The Mirror Tower records piece size and orientation. Follow each axis and layer to observe piece movement.":
        "鏡面タワーはパーツの寸法と向きを入力情報にします。軸と層ごとに銀色パーツの位置と向きの変化を観察します。",
    "Outer-layer turn": "外層の回転",
    "Observe the silver pieces move and change orientation.": "外層の銀色パーツの移動と向きの変化を観察します。",
    "Adjacent layer turn": "隣接層の回転",
    "Both displayed turns restore the silver pieces in this example.":
        "表示された2つの回転で本例の銀色パーツが戻ります。",
    "Match piece shapes and sizes using the U/D, R/L and F/B axes. These examples use the corresponding cube-order algorithms; completing each formula restores its example.":
        "ピースの形と大きさを U/D・R/L・F/B 軸で合わせます。本例は対応する段数の手順を使い、公式を完了すると例の状態に戻ります。",
    "Follow the face labels and piece shapes. Left undoes one action; right executes one action.":
        "面ラベルとピースの形を確認し、左右の矢印で1動作を戻す／進めます。",
    "Follow the labelled mechanical face. Completing the formula restores this example.":
        "表示された機械的な回転面に従ってピースの移動を観察します。公式を完了すると本例に戻ります。",
    "Corner sequences and orientation": "角の組合せと向き",
    "Observe corner positions and orientation around mechanical axes. Order two has only corners; orders four and five also require centers and edges. Each example restores its prepared state.":
        "機械軸まわりの角の位置と向きを観察します。2段は角のみ、4・5段は中心と辺も扱います。各例は準備した状態に戻ります。",
    "Center and edge reduction moves": "中心と辺の縮約動作",
    "Combine centers and wings before solving the reduced corner/edge puzzle. Rw turns the outer two layers.":
        "縮約後の角・辺を解く前に、同じ領域の中心とウィングを組みます。Rw は外側2層を同時に回します。",
    "Wide turn": "ワイド回転",
    "Watch two layers turn together.": "外側2層が同時に回る様子を観察します。",
    "Center/wing combination": "中心とウィングの組合せ",
    "Judge the effect after the complete sequence.": "途中で他のパーツも動きます。全部終えてから効果を判断します。",
    "Setup and interchange": "準備動作付きの交換",
    "F sets up the sequence; F' undoes that setup.": "F は準備動作で、最後に F' で戻します。",
    "Edge turns and two-colour caps": "辺の回転と2色キャップ",
    "Each edge turns 180 degrees, flipping its own cap and moving four petals. Face centres stay fixed. An edge is labelled by its two face numbers. Left undoes one move; right executes one move.":
        "各辺は180°回転し、2色キャップが反転して4枚の花びらが動きます。面中心は動きません。辺は両側の面番号（例 1/2）で示します。",
    "One edge half turn": "1辺の半回転",
    "A second half turn on the same edge restores it.": "同じ辺をもう1回半回転すると元に戻ります。",
    "Independent petal three-cycles": "独立した花びらの三循環",
    "Orient the edge caps, then restore six petal orbits. Each complete eight-move macro cycles three petals in one orbit and fixes every other sticker. Each example starts with its formula inverse.":
        "2色キャップの向きを整えてから、6組の花びらを処理します。8手のマクロは指定の組の花びら3枚だけを巡回し、他のステッカーは変えません。各例は公式の逆から始まります。",
    "Observe the effect after all eight moves. Other pieces move temporarily.":
        "8手すべて終えた後の効果を観察します。途中で他のパーツが一時的に動きます。",
    "A1, A2, etc. identify the twist-page axes. The number after : is the layer; signed angles give the direction. Each axis uses its labelled angle. Each example begins with its formula inverse.":
        "A1、A2 などは回転画面の軸番号です。コロン後の数字は層、符号付き角度は方向を示します。各軸の角度は動作の表示に従います。各例は公式の逆から始まります。",
    "Axes and layers": "軸と層を知る",
    "Forward layer turn": "層の正方向回転",
    "Press Next to turn one layer on the indicated axis.": "「次へ」で指定軸の1層を回します。",
    "Reverse layer turn": "層の逆方向回転",
    "A negative angle reverses the turn; either half-turn direction has the same effect.":
        "負の角度は正の向きと逆です。半回転はどちらの向きでも同じ結果です。",
    "A face with a different turn angle": "回転角が異なる面",
    "Dino / Lattice corner turns": "ダイノ／ラティスの角回転構造",
    "Dino and Lattice cubes share eight shallow corner-turn directions. Dino has twelve two-colour edges; Lattice variants add layers to this mechanism. Each turn is 120 degrees. A1 through A8 match the twist-page axes.":
        "ダイノとラティスは同じ8方向の浅い角回転を持ちます。ダイノは12本の2色辺、ラティスは同じ機構に層を追加します。各回転は120°、A1〜A8 は回転画面の軸番号に対応します。",
    "Four corners and six leaf centres": "4つの角と6枚の葉中心",
    "Four alternating corners turn by 120 degrees. Each turn rotates one three-colour corner and cycles its three neighbouring leaf centres. A1 through A4 match the four twist-page axes.":
        "相対する4つの角が120°回転します。1回転で1つの3色角と隣接する3枚の葉中心が巡回します。A1〜A4 は4つの軸に対応します。",
    "Corner turn 120°": "角の正回転 120°",
    "Reverse corner turn 120°": "角の逆回転 120°",
    "Independent tip alignment": "チップ（尖角）の独立調整",
    "Tips turn independently by 120 degrees. On order two, the face-center triangles remain fixed.":
        "チップは120°ずつ独立に回せます。2段では中央の三角が固定です。",
    "Only the selected tip moves.": "選んだチップだけが動きます。",
    "Adjacent-axis sequences": "隣接軸の組合せ",
    "Observe setup and undo moves using this puzzle's actual mechanism. These local examples demonstrate A B A' B' and their restoration; use Solve for a complete entered scramble.":
        "このパズルの実際の機構で準備動作と戻し動作を観察します。本例は A B A' B' と復元を示す局所例です。入力した全体の復元は「解く」を使ってください。",
    "Three-move sequence": "3手の組合せ",
    "Four-move sequence": "4手の組合せ",
    "Inner-layer combination": "内層の組合せと縮約準備",
    "Higher orders add inner layers and movable center/edge pieces. Observe a full inner/outer sequence.":
        "高次は内層と可動の中心・辺を追加します。内層と外層の組合せを1通り観察します。",
    "Turn an inner layer": "内層を回す",
    "Inner/outer interchange": "内外層の交換例",
    "Far outer layer": "反対側の外層",
    "The two layers are the near and far outer halves. Layer 2 selects the far half.":
        "3段斜転の2層は手前側と奥側の外層です。本例は奥側（層番号2）を示します。",
    "Turn the far outer half": "奥側の外層を回す",
    "Near/far outer sequence": "内外層の組合せ",
}


def text(zh, en, ja=None):
    return {'zh':zh, 'en':en, 'ja':ja if ja is not None else _JA.get(en, en)}


def token(move,spec=None):
    if isinstance(move,str):
        return move
    if move.__class__.__name__=='Square1Move':
        return str(move)
    label=f'A{move.axis+1}:{move.layer+1}'
    if spec is None:
        return label if move.amount==1 else f'{label} ×{move.amount}'
    amount=move.amount%spec.turn_order
    if amount>spec.turn_order/2:
        amount-=spec.turn_order
    return f'{label} {amount*360/spec.turn_order:+g}°'


def case(name, moves, tip):
    return {'name':name, 'moves':tuple(moves),
            'text':' '.join(map(token,moves)), 'tip':tip}


def step(title, desc, cases):
    return {'title':title, 'desc':desc, 'cases':cases}


@lru_cache(maxsize=32)
def lessons(kind,n):
    if not 2<=n<=5:
        raise ValueError('Teaching demos support orders up to five')
    if kind=='square1':
        from cube.square1 import Square1Move
        return [
            step(text('上下层转动','Top and bottom turns'),text(
                'SQ1 的上下层可以分别转动；先观察块的位置变化，再尝试反向转回。',
                'Turn the top and bottom layers independently, then reverse the turn.'),[
                case(text('上层转动','Turn the top layer'),(Square1Move(0,3),),text(
                    '一步转动后观察棱块和角块的排列。','Observe the edge and corner order after one turn.')),
                case(text('下层转动','Turn the bottom layer'),(Square1Move(1,-2),),text(
                    '下层按自己的方向记号转动。','The bottom layer uses its own turn direction.'))]),
            step(text('斜切与形状变化','Slash and shape change'),text(
                '上下层转到切口处没有跨界的角块后才能斜切。斜切会交换两层的一半，再转回可恢复原状。',
                'The slash is legal only when no corner crosses the cut. It swaps half of each layer.'),[
                case(text('转层后斜切复原','Align layers, then restore with a slash'),
                     (Square1Move(0,1),Square1Move(1,-1),Square1Move(2)),text(
                    '本例从变形状态开始；按顺序执行三个动作恢复立方体外形。每个转层单位是30°。',
                    'This example starts with a changed shape. All three moves restore the cube shape; each layer unit is 30 degrees.'))])]
    if kind in ('axis','pandora','windmill','fisher'):
        names={'axis':('轴心魔方','Axis Cube','アクシスキューブ'),'pandora':('潘多拉魔方','Pandora Cube','パンドラキューブ'),
               'windmill':('风火轮魔方','Windmill Cube','ウィンドミルキューブ'),'fisher':('移棱魔方','Fisher Cube','フィッシャーキューブ')}
        zh,en,ja=names[kind]
        return [step(text('观察外形与转层','Shape and layer turns'),text(
            f'{zh}使用三阶立方体转层结构。先观察转动后外形和色块如何改变，再完成公式回到示例起始状态。',
            f'{en} uses a three-layer cube mechanism. Observe the changing shape and stickers, then complete each formula.',
            f'{ja} は3層の立方体機構です。回転で外形とステッカーがどう変わるかを観察し、公式を完了すると例の初期状態に戻ります。'),[            case(text('右层转动','Right-layer turn'),('R',),text(
                '观察右侧结构转动。','Observe the right-side pieces turn.')),
            case(text('连续转动与复位','Turn sequence and restoration'),('U','R',"U'","R'"),text(
                '完整执行公式后观察形状和色块复位。','Complete the sequence to restore the example state.'))])]
    if kind=='mirror_tower':
        moves=(Move(0,0),Move(1,0))
        return [step(text('观察银色块与转层','Silver pieces and layers'),text(
            '魔塔魔方以块的尺寸和朝向作为录入信息。按转轴和层号逐步观察银色块的位置及朝向变化。',
            'The Mirror Tower records piece size and orientation. Follow each axis and layer to observe piece movement.'),[
            case(text('外层转动','Outer-layer turn'),(moves[0],),text(
                '观察外层银色块移动和朝向变化。','Observe the silver pieces move and change orientation.')),
            case(text('相邻转层','Adjacent layer turn'),moves,text(
                    '完整执行两次转动后，银色块回到本例的还原外形。','Both displayed turns restore the silver pieces in this example.'))])]
    if kind=='mirror':
        originals={2:CASE_2X2,3:CASE_3X3,4:CASE_4X4,5:CASE_5X5}[n]
        result=[]
        for index, original in enumerate(originals):
            title = text(f'形状复位阶段 {index+1}', f'Shape restoration stage {index+1}',
                         f'形状復元 段階 {index+1}')
            result.append(step(title,text(
                '镜面魔方按块的形状和大小定位。U/D、R/L、F/B 为转动面标签；用形状匹配替代普通魔方的颜色匹配。'
                '本组沿用对应阶数的层先法或降阶动作，每个示例完成公式后恢复其初始构造前的形状。',
                'Match piece shapes and sizes using the U/D, R/L and F/B axes. '
                'These examples use the corresponding cube-order algorithms; completing each formula restores its example.'),
                [case(text(f'形状复位示例 {i+1}',f'Shape example {i+1}',f'形状復元 例 {i+1}'),c['moves'],text(
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
            'not the four surface colors. A prime reverses a turn; 2 denotes a half turn.',
            f'{n}段のマスターモルフィックスは立方体の内部機構を持ちます。U/D・F/B・R/L は機械軸で、'
            '4色の表面色とは異なります。プライムは逆回転、2 は半回転です。'))
        if n != 3:
            result[0]=dict(result[0],cases=[dict(c,tip=text(
                '按标记的机械转动面观察块的移动；完整执行显示公式后恢复本例。',
                'Follow the labelled mechanical face. Completing the formula restores this example.'))
                for c in result[0]['cases']])
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
    if kind=='blossom':
        from cube.polyhedral import dot
        from solver.blossom import _assets
        def edge_name(move):
            axis=g.spec.axes[move.axis]
            nearest=max(dot(normal,axis) for normal in g.spec.normals)
            return '/'.join(str(i+1) for i,normal in enumerate(g.spec.normals)
                            if abs(dot(normal,axis)-nearest)<1e-7)
        def flower_case(name, word, tip):
            item=case(name,word,tip)
            notation='  '.join(edge_name(move) for move in word)
            item['text']=text('棱 '+notation,'Edges '+notation,'辺 '+notation)
            return item
        first=Move(0,0,g.spec.step(0))
        cycles=_assets()['cycles'].values()
        return [step(text('棱转与双色棱块','Edge turns and two-colour caps'),text(
            '每条棱转动180°，双色棱块在原位置翻转，同时带动四片花瓣。面中心不动。'
            '棱号由两侧面的颜色编号组成，例如1/2；用左右按钮退回或执行一步。',
            'Each edge turns 180 degrees, flipping its own cap and moving four petals. Face centres stay fixed. '
            'An edge is labelled by its two face numbers. Left undoes one move; right executes one move.'),[
                flower_case(text('单棱半圈','One edge half turn'),(first,),text(
                    '同一条棱再转180°就恢复原位。','A second half turn on the same edge restores it.'))]),
            step(text('独立花瓣三循环','Independent petal three-cycles'),text(
                '先调整双色棱块朝向，再分别处理六组花瓣。完整执行八步公式只交换指定组中的三片花瓣，'
                '其他花瓣和双色棱块在公式结束后保持不变。每个例子的起始状态由对应公式的逆序产生。',
                'Orient the edge caps, then restore six petal orbits. Each complete eight-move macro cycles '
                'three petals in one orbit and fixes every other sticker. Each example starts with its formula inverse.'),[
                    flower_case(text(f'花瓣组 {i+1}',f'Petal orbit {i+1}',f'花びら組 {i+1}'),
                                tuple(Move(*move) for move in macro['word']),text(
                                    '观察完整八步后的效果；中间动作会暂时移动其他块。',
                                    'Observe the effect after all eight moves. Other pieces move temporarily.'))
                    for i,macro in enumerate(cycles)])]
    inverse=lambda move:move.inverse(g.spec.turn_order)
    # Pyraminx tip layer and body layer are different legal bands.
    body_layer=next((i for i,b in enumerate(g.layers[0]) if len(b)>1),0)
    a=Move(0,body_layer,g.spec.step(0))
    b=Move(1,body_layer,g.spec.step(1))
    notation=text('A1、A2 等对应拧动页的转轴编号；冒号后是层号，正负角度表示该轴的正反方向。不同转轴的角度以动作旁标注为准。'
                  '案例从所示公式的逆操作构造，完成整段后恢复本案例。',
                  'A1, A2, etc. identify the twist-page axes. The number after : is the layer; signed angles give the direction. '
                  'Each axis uses its labelled angle. Each example begins with its formula inverse.')
    result=[step(text('认识转轴与转层','Axes and layers'),notation,[
        case(text('单层正向转动','Forward layer turn'),(a,),text(
            '按下一步，观察指定轴的一层转动。', 'Press Next to turn one layer on the indicated axis.')),
        case(text('单层反向转动','Reverse layer turn'),(inverse(a),),text(
            '负角度与正角度方向相反，半圈的两个方向等效。', 'A negative angle reverses the turn; either half-turn direction has the same effect.'))])]
    other=next((i for i in range(len(g.spec.axes)) if g.spec.order(i)!=g.spec.order(0)),None)
    if other is not None:
        move=Move(other,0,g.spec.step(other))
        result[0]['cases'].append(case(text('另一类转面的转动','A face with a different turn angle'),(move,),text(
            f'本轴的最小转动角为{360//g.spec.order(other)}°，按动作旁的转轴编号选择。',
            f'This axis turns by {360//g.spec.order(other)} degrees; select its labelled axis.',
            f'本軸の最小回転角は{360//g.spec.order(other)}°です。動作の軸番号で選択します。')))
    if kind=='dino':
        result[0]=dict(result[0],title=text('恐龙与格子的角转结构','Dino / Lattice corner turns'),desc=text(
            '恐龙魔方与格子魔方同属一组：恐龙以12个双色棱块为主体，格子在相同的八个角转方向上增加切层。'
            '每次转动120°；本组使用浅切的恐龙结构。A1至A8对应拧动页的转轴编号。',
            'Dino and Lattice cubes share eight shallow corner-turn directions. Dino has twelve two-colour '
            'edges; Lattice variants add layers to this mechanism. Each turn is 120 degrees. A1 through A8 '
            'match the twist-page axes.'))
    if kind=='ivy':
        result[0]=step(text('四个转角和六片叶形块','Four corners and six leaf centres'),text(
            '枫叶魔方的四个相间角可转动120°。每次转动一个三色角块，并循环移动相邻三片叶形块。'
            'A1至A4对应拧动页的四个转轴；观察角块的三色朝向，再观察叶形块的移动。',
            'Four alternating corners turn by 120 degrees. Each turn rotates one three-colour corner '
            'and cycles its three neighbouring leaf centres. A1 through A4 match the four twist-page axes.'),[
                case(text('角块正转120°','Corner turn 120°'),(a,),notation),
                case(text('角块反转120°','Reverse corner turn 120°'),(inverse(a),),notation)])
    if kind=='pyraminx':
        tips=[Move(i,0,g.spec.step(i)) for i,layers in enumerate(g.layers) if len(layers[0])==1]
        if tips:
            result.append(step(text('尖角独立复位','Independent tip alignment'),text(
                '尖角每次转 120°，可独立对齐相邻面。二阶只转尖角，中间三角块不动；更高阶可在主体复位后处理尖角。',
                'Tips turn independently by 120 degrees. On order two, the face-center triangles remain fixed.'),[
                case(text(f'对齐尖角 {tip.axis+1}',f'Align tip {tip.axis+1}',f'チップ {tip.axis+1} を合わせる'),(tip,),text(
                    '观察只有对应尖角移动。','Only the selected tip moves.')) for tip in tips]))
    if n!=2 or kind!='pyraminx':
        insertion=(a,b,inverse(a))
        exchange=(a,b,inverse(a),inverse(b))
        result.append(step(text('相邻转轴组合','Adjacent-axis sequences'),text(
            '先观察 A1、A2 的配合，再撤回准备动作。组合由 A B A逆 B逆 等构成，实际影响取决于当前模型的结构。'
            '下列案例用于观察局部动作和复位，实际录入后的完整还原请使用求解功能。',
            'Observe setup and undo moves using this puzzle\'s actual mechanism. These local examples demonstrate '
            'A B A\' B\' and their restoration; use Solve for a complete entered scramble.'),[
            case(text('三步组合','Three-move sequence'),insertion,notation),
            case(text('四步组合','Four-move sequence'),exchange,notation)]))
    if len(g.layers[0])>body_layer+1:
        inner=Move(0,body_layer+1,g.spec.step(0))
        result.append(step(text('内层组合与降阶准备','Inner-layer combination'),text(
            '高阶增加了内层和可移动的中心、棱。先学习准确选择内层，再观察内层与外层组合时各类块的运动。'
            '每段动作必须完整执行；中间帧的变化并不代表整段结束后的效果。',
            'Higher orders add inner layers and movable center/edge pieces. Observe a full inner/outer sequence.'),[
            case(text('单独转内层','Turn an inner layer'),(inner,),notation),
            case(text('内外层交换示例','Inner/outer interchange'),
                 (inner,b,inverse(inner),inverse(b)),notation)]))
        if kind=='skewb' and n==3:
            result[-1]['title']=text('对侧外层转动','Far outer layer')
            result[-1]['desc']=text('三阶斜转的两层分别是近侧和远侧外层。本组演示远侧外层，选择层号2。',
                                   'The two layers are the near and far outer halves. Layer 2 selects the far half.')
            result[-1]['cases'][0]['name']=text('转动对侧外层','Turn the far outer half')
            result[-1]['cases'][1]['name']=text('两侧外层组合','Near/far outer sequence')
    for item in result:
        for example in item['cases']:
            example['text']='  '.join(token(move,g.spec) for move in example['moves'])
    return result
