"""Mechanism-aware examples for irregular puzzles through order five.

Examples start from the inverse of the displayed sequence, like the ordinary
cube lessons. No example reads, scrambles, or changes the user's input draft.
"""
from functools import lru_cache
from copy import deepcopy

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
    if move.__class__.__name__=='PyramidAlignment':
        from app.i18n import tr
        return tr('ghost_pyramid.align_move',angle=move.angle)
    if getattr(move, 'notation', None):
        return move.notation
    if move.__class__.__name__=='Square1Move':
        return str(move)
    label=f'A{move.axis+1}:{move.layer+1}'
    if getattr(move,'layers',()):label=f'A{move.axis+1}:'+','.join(str(l+1) for l in move.layers)
    if spec is None:
        return label if move.amount==1 else f'{label} ×{move.amount}'
    if spec.kind.startswith(('crazy_','circle_2','cuboid_','camouflage_3')):
        from cube.circle_cube import FACES
        power=(-move.amount)%4
        prefix=f'{move.layer+1}' if spec.kind.startswith(('cuboid_','camouflage_3')) and move.layer else ''
        return prefix+FACES[move.axis]+('w' if prefix else '')+{0:'',1:'',2:'2',3:"'"}[power]
    if spec.kind=='coin_tetrahedron':
        label=f'C{move.axis+1}' if move.axis<4 else f'V{move.axis-3}'
    amount=move.amount%spec.turn_order
    if amount>spec.turn_order/2:
        amount-=spec.turn_order
    return f'{label} {amount*360/spec.turn_order:+g}°'


def case(name, moves, tip):
    return {'name':name, 'moves':tuple(moves),
            'text':' '.join(map(token,moves)), 'tip':tip}


def step(title, desc, cases):
    return {'title':title, 'desc':desc, 'cases':cases}


def _piece_group_names(size):
    return {
        1:('单色中心块','single-colour centre','単色センター'),
        2:('双色棱块','two-colour edge','2色エッジ'),
        3:('三色角块','three-colour corner','3色コーナー'),
    }.get(size,(f'{size}色块',f'{size}-colour piece',f'{size}色ピース'))


def _cycle_formula_lessons(cube):
    """Expose solver-certified three-cycle macros as typical-case lessons."""
    from solver.polyhedral import piece_orbits
    from solver.lattice_data import geometry_key

    kind,n=cube.puzzle_kind,cube.n
    records={}
    if kind=='dino' and n in (4,6):
        from solver.lattice_data import _data
        record=_data().get(str(n),{})
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind in ('dino_skewb','dayan_dino_skewb'):
        from solver.dino_skewb import prepared
        record=prepared(kind)
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind in ('mosaic','tins'):
        from solver.mosaic import prepared
        record=prepared(kind)
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind=='helicopter':
        from solver.helicopter import prepared
        record=prepared()
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind=='super_ivy':
        from solver.super_ivy import prepared
        record=prepared()
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind=='fto':
        from solver.fto import _cycle_assets
        record=_cycle_assets().get(str(n),{})
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind=='football':
        from solver.football import _assets
        record=_assets().get(str(n),{})
        if record.get('geometry')==geometry_key(cube.geometry):
            records=dict(record.get('cycles',{}))
            if record.get('edge_cycle'):
                records['edge']=record['edge_cycle']
    elif kind=='icosahedron':
        from solver.icosahedron import _cycles
        record=_cycles().get(str(n),{})
        if record.get('geometry')==geometry_key(cube.geometry):
            records=record.get('cycles',{})
    elif kind=='megaminx' and n>=4:
        from solver.minx_plans import orbit_plan
        orbits=piece_orbits(kind,n)
        targets={i:orbit for i,orbit in enumerate(orbits) if len(orbit)>1}
        prepared=orbit_plan(cube,targets)
        if prepared and not prepared[2]:
            macros,_,_=prepared
            records={str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                             'base':list(base)}
                     for i,(word,base) in macros.items()}
    elif kind in ('clover','eight_petals','ivy','moyu','pyraminx','skewb',
                  'void_cube','void_tower','war_drum','pentahedron'):
        # Derive exact, isolated three-cycle formulas from each puzzle's own
        # geometry instead of reusing a cube algorithm with mismatched turns.
        from solver.polyhedral_reduction import primitives
        orbits=piece_orbits(kind,n)
        targets={}
        macros={}
        seen_sizes=set()
        for index,orbit in enumerate(orbits):
            if len(orbit)<3:
                continue
            size=len(cube.geometry.pieces[orbit[0]])
            if size in seen_sizes:
                continue
            try:
                # Some piece orbits (notably tetrahedral face references)
                # cannot cycle independently. Keep searching other orbits of
                # the same piece type rather than aborting the entire lesson.
                candidate=primitives(cube,{index:orbit},use_prepared=True)
            except ValueError:
                continue
            targets[index]=orbit
            macros.update(candidate)
            seen_sizes.add(size)
            if len(targets)>=(1 if kind in ('war_drum','pentahedron') else 3):
                break
        if targets:
            records={str(i):{'word':[[m.axis,m.layer,m.amount] for m in word],
                             'base':list(base)}
                     for i,(word,base) in macros.items()}

    if not records:
        return None
    g=cube.geometry
    cases=[]
    for key,record in sorted(records.items(),key=lambda item:str(item[0])):
        try:
            base=tuple(int(piece) for piece in record['base'])
            word=tuple(Move(*move) for move in record['word'])
            if len(base)!=3 or not word or any(not 0<=p<len(g.pieces) for p in base):
                continue
        except (KeyError,TypeError,ValueError):
            continue
        from cube.cycle_effects import three_cycle
        from solver.polyhedral import simplify, inverse_word
        word=simplify(word,g.spec.turn_order)
        effect=three_cycle(kind,n,word)
        if effect is None:
            continue
        destinations=dict(effect[0])
        base=tuple(sorted(destinations))
        markers={piece:label for piece,label in zip(base,('A','B','C'))}
        group_zh,group_en,group_ja=_piece_group_names(len(g.pieces[base[0]]))
        if kind in ('mosaic','tins'):
            if min(abs(v) for v in g.centres[base[0]])<1e-6:
                group_zh,group_en,group_ja=('双色中心块','Paired centre','2色の中心')
            elif kind=='mosaic':
                group_zh,group_en,group_ja=('外围块','Outer piece','外側パーツ')
            elif max(len(g.stickers[s].polygon) for s in g.pieces[base[0]])==5:
                group_zh,group_en,group_ja=('五边形块','Pentagon','五角形')
            else:
                group_zh,group_en,group_ja=('三角块','Triangle','三角形')
        if kind=='super_ivy' and len(g.pieces[base[0]])==1:
            orbit=next(o for o in piece_orbits(kind,n) if base[0] in o)
            group_zh,group_en,group_ja=(('中心块','Centre','センター') if len(orbit)==6
                                      else ('叶片','Leaf','葉'))
        for reverse,formula in ((False,word),(True,inverse_word(word,g.spec.turn_order))):
            mapping={v:k for k,v in destinations.items()} if reverse else destinations
            a=base[0];b=mapping[a];c=mapping[b]
            route=' → '.join(markers[p] for p in (a,b,c,a))
            label=text(f'{group_zh}循环 · {key} · '+('反向' if reverse else '正向'),
                       f'{group_en} cycle · {key} · '+('reverse' if reverse else 'forward'),
                       f'{group_ja}循環 · {key} · '+('逆方向' if reverse else '順方向'))
            tip=text(
                f'看哪里：橙色描边的 A、B、C 标记位置。适用情况：只有这三块循环错位，块的朝向与图示一致，其余块已还原。\n'
                f'怎么判断：当前 A 位置的块应去 {markers[mapping[a]]}，按 {route} 归位；方向相反时选另一例。\n'
                '怎么做：先整体旋转实物，对齐模型上的位置和面色编号；不要靠转动某一层来硬套位置。完整执行公式，中途其他块可暂时移动；结束后三块归位，其余贴纸不变。A/B/C 标记固定位置，转动时暂时隐藏。',
                f'Look at the orange-outlined slots A, B and C. Use this case only when those three pieces are cycled, their orientations match, and everything else is solved.\n'
                f'The piece at A belongs at {markers[mapping[a]]}: restore {route}. Choose the other example for the opposite cycle.\n'
                'Match the slot labels and face colours by rotating the whole puzzle. Complete the entire algorithm: other pieces may move temporarily but finish unchanged. Labels mark fixed slots and hide during turns.',
                f'オレンジの輪郭で示す位置A・B・Cを確認します。この3個だけが循環し、向きが図と一致し、他が揃っている場合に使います。\n'
                f'Aのピースは{markers[mapping[a]]}へ移ります。{route}の順で戻します。逆の循環には別の例を選びます。\n'
                'パズル全体を持ち替え、位置と面色番号を図に合わせてください。公式を最後まで実行すると3個が戻り、他のステッカーは元のままです。文字は固定位置を示し、回転中は非表示です。')
            item=case(label,formula,tip)
            item['text']='  '.join(token(move,g.spec) for move in formula)
            item['tutorial_targets']=markers
            item['cycle_route']=route
            item['show_all']=True
            item['camera']=_cycle_camera(g,base)
            cases.append(item)
    if not cases:
        return None
    return [step(text('典型情况：三块循环错位','Typical case: three-cycle','典型例：3点交換'),text(
        '先识别同一类块中仅有三块循环错位的情形。每条公式针对图示的一组位置；公式结束后，这三块归位，其他块保持不动。',
        'Recognize a three-cycle in one piece group with the rest solved. Each formula targets the positions shown; it restores those three pieces and leaves the others fixed.',
        '他が揃った状態で、同じピース組の3個だけが循環している場合を見分けます。各公式は図の位置に対応し、3個を戻して他を保ちます。'),cases)]


def _cycle_camera(g,pieces):
    import math
    from cube.polyhedral import dot,unit,add
    faces=[tuple({g.stickers[i].face for i in g.pieces[p]}) for p in pieces]
    candidates=list(g.spec.normals)
    candidates.extend(unit(add(a,b)) for a in g.spec.normals for b in g.spec.normals
                      if dot(add(a,b),add(a,b))>.01)
    def score(eye):
        visibility=[max(dot(eye,g.spec.normals[f]) for f in group) for group in faces]
        return sum(v>.15 for v in visibility),sum(visibility)
    eye=max(candidates,key=score)
    return math.degrees(math.atan2(eye[0],eye[2])),math.degrees(math.asin(max(-1,min(1,eye[1])))),0


@lru_cache(maxsize=32)
def lessons(kind,n):
    if not 2<=n<=5:
        raise ValueError('Teaching demos support orders up to five')
    if kind=='coin_tetrahedron':
        from cube.polyhedral import dot
        cube=PolyhedralPuzzle(kind,n)
        g=cube.geometry
        examples=[]
        for corner in range(4,8):
            face=next(i for i,normal in enumerate(g.spec.normals) if dot(normal,g.spec.axes[corner])>0)
            for amount in (1,2):
                moves=(Move(corner),Move(face,0,amount),Move(corner,0,2))
                item=case(text(f'角已齐，跨面叶片错位 · V{corner-3}/C{face+1} · {"正向" if amount==1 else "反向"}',
                               f'Corners solved, misplaced leaves · V{corner-3}/C{face+1} · {"forward" if amount==1 else "reverse"}',
                               f'角が揃い、葉を移す・V{corner-3}/C{face+1}・{"正方向" if amount==1 else "逆方向"}'),moves,text(
                    '四个角已对齐，图示椭圆叶片分布在相邻两面。按模型核对颜色和拿法，依次转角、转圆盘、把角转回。公式实际移动三片叶片，其中同色片可能让它看起来只有两片错位；其余角和中心在结束后保持归位。',
                    'All four corners match; the shown oval leaves are misplaced across adjacent faces. Match the colours and grip. Turn the corner, turn the disc, then undo the corner turn. Three leaves cycle; equal colours can hide one displacement. Corners and centres are restored at the end.',
                    '角4個が揃い、隣接する2面の楕円の葉がずれた場合。色と持ち方を合わせ、角→円盤→角を戻す順に実行します。葉3個の循環ですが、同色により2個だけの交換に見えることがあります。角と中心は最後に元へ戻ります。'))
                item['text']='  '.join(token(m,g.spec) for m in moves)
                item['show_all']=True
                examples.append(item)
        return [step(text('典型情况：保留角块，调整跨面叶片','Typical case: move leaves while preserving corners','典型例：角を保ち、面をまたぐ葉を移す'),text(
            'C1–C4是面上圆盘，V1–V4是角轴，每步120°。先按角块确定拿法，再核对椭圆叶片的颜色位置。每例从待还原状态开始，执行完整公式后还原。',
            'C1–C4 are face discs and V1–V4 are corner axes; each move is 120°. Orient the puzzle using its corners and match the oval leaf colours. Each case starts unsolved and the complete formula restores it.',
            'C1–C4は円盤、V1–V4は角軸で、1手は120°です。角で持ち方を決め、楕円の葉の色配置を確認します。各例は未完成の状態から始まり、公式全体で完成します。'),examples)]
    if kind=='pyraminx_duo':
        from solver.pyraminx_duo import prepared
        cube=PolyhedralPuzzle(kind,n)
        g=cube.geometry
        corners={s for piece in g.pieces if len(piece)==3 for s in piece}
        first=[]
        for axis in range(4):
            for amount in (1,2):
                moves=(Move(axis,0,amount),)
                item=case(text(f'角 A{axis+1} 与相邻中心错位 · {"+120°" if amount==1 else "−120°"}',
                               f'Corner A{axis+1} and its centres · {"+120°" if amount==1 else "−120°"}',
                               f'角 A{axis+1} と隣接中心・{"+120°" if amount==1 else "−120°"}'),moves,text(
                    '其余三个角已对齐，图示角及相邻三个面中心沿同一方向错开一格。核对模型中三色角的颜色顺序，再按标出的方向转120°一起归位。',
                    'The other three corners match; the shown corner and its three adjacent centres are offset together. Match the three-colour corner order, then turn 120° in the shown direction.',
                    '他の角3個は揃い、図の角と隣接中心3個が一緒にずれた場合。角の色順を確認し、表示方向へ120°回します。'))
                item['text']=token(moves[0],g.spec)
                corner=next(p for p in g.layers[axis][0] if len(g.pieces[p])==3)
                item['camera']=_cycle_camera(g,(corner,))
                first.append(item)
        centres=[]
        for state,atoms in prepared().items():
            if not atoms or any(int(state[s])!=g.stickers[s].face for s in corners):
                continue
            moves=tuple(Move(*atom) for atom in atoms)
            item=case(text(f'四角已齐，中心两两交换 · {len(centres)+1}',
                           f'Corners solved, two centre pairs swapped · {len(centres)+1}',
                           f'角が揃い、中心2組を交換・{len(centres)+1}'),moves,text(
                '四个角的三色都已对齐，但四个面中心成两对交换。按模型核对是哪两对，保持图示拿法，完整执行四步公式；结束后角和中心同时还原。',
                'All four corners match, but the four centres form two swapped pairs. Match both pairs and the model orientation, then complete all four moves to restore corners and centres.',
                '角4個は揃い、中心4個が2組ずつ入れ替わった場合。交換する組と持ち方をモデルに合わせ、4手を最後まで実行します。'))
            item['text']='  '.join(token(m,g.spec) for m in moves)
            item['show_all']=True
            centres.append(item)
        return [step(text('典型情况：角与中心一起错位','Typical case: corner and centres offset','典型例：角と中心のずれ'),text(
                    '先核对四个三色角；普通Duo的单色面中心不需要判断旋转方向。以下情况均从待还原状态开始。',
                    'Identify the four three-colour corners first. Plain centres have no visible orientation. Every example begins in its unsolved case.',
                    'まず3色の角を確認します。単色中心の回転方向は区別不要です。各例は未完成の状態から始まります。'),first),
                step(text('典型情况：角已齐，只换面中心','Typical case: corners solved, centres swapped','典型例：角が揃い、中心だけ交換'),text(
                    '四角归位后，合法的剩余中心错位只有以下三种两两交换。选择与实物相同的颜色排列，完整执行四步公式。',
                    'With corners solved, these are the three legal remaining centre pair swaps. Match the colour arrangement and complete the four-move formula.',
                    '角が揃った後に残る合法な中心交換は次の3種類です。実物と同じ色配置を選び、4手の公式を実行します。'),centres)]
    if kind=='fisher_skewb':
        from cube.fisher_skewb import appearance
        from cube.mirror_pyraminx import placements
        from solver.fisher_skewb import prepared
        record=prepared()
        invisible=sum(1<<i for i,h in enumerate(record['homes'])
                      if len({appearance(h,f) for f in placements(3,h,h,'skewb')})==1)
        shortest={}
        for mask,word in record['finishers'].items():
            visible=int(mask)&~invisible
            if visible and visible.bit_count()==1 and (visible not in shortest or len(word)<len(shortest[visible])):
                shortest[visible]=word
        examples=[]
        for i,(mask,word) in enumerate(sorted(shortest.items())):
            moves=tuple(Move(*m) for m in word)
            item=case(text(f'单个侧中心方向错误 · {i+1}',f'One misoriented side centre · {i+1}',f'側面中心1個の向き違い・{i+1}'),moves,text(
                '适用情况：其余块已归位，只有图示侧中心没有与外壳和邻面接平。先把实物摆成图中的方向，再执行完整公式；两个单色方形中心的不可见方向不需要区分。',
                'Use when every other piece is restored and only the shown side centre fails to align with the shell. Match the model orientation and complete the algorithm. Invisible directions of the two square centres do not matter.',
                '他が揃い、図の側面中心だけが外形に合わない場合。図と同じ向きで持ち、公式を最後まで実行します。単色の四角中心2個の見えない向きは区別不要です。'))
            home=record['homes'][mask.bit_length()-1]
            from cube.polyhedral import geometry
            item['camera']=_cycle_camera(geometry('skewb',3),(home,))
            item['text']='  '.join(token(m,geometry('skewb',3).spec) for m in moves)
            item['show_all']=True
            examples.append(item)
        return [step(text('典型情况：侧面中心方向','Typical case: side-centre direction','典型例：側面中心の向き'),text(
            'Fisher Skewb需要同时还原颜色、外形和可见方向。以下公式会把示例中的侧中心归位，其余可见块在公式结束后保持原样。',
            'Restore colour, shape and visible direction together. These formulas correct the shown centre and leave the other visible pieces restored after the full sequence.',
            '色、外形、見える向きを同時に戻します。公式終了後は図の中心が戻り、他の見えるパーツも元のままです。'),examples)]
    if kind=='square1':
        from cube.square1 import Square1Move
        return [
            step(text('典型情况：立方体外形复原','Typical case: restore cube shape','典型例：立方体形状への復元'),text(
                '识别上下层各偏一格、切口对齐且可以斜切的状态。按公式先转上层和下层，再斜切；每个层转单位为30°。',
                'Use this when the top and bottom are each offset by one unit and the cut is aligned. Turn both layers, then slash; each unit is 30 degrees.',
                '上下層がそれぞれ1単位ずれ、切断位置が揃った状態で使います。上下層を回してから斜め切断します。1単位は30°です。'),[
                case(text('上下层错位一格','Both layers offset by one unit','上下層が1単位ずれた場合'),
                     (Square1Move(0,1),Square1Move(1,-1),Square1Move(2)),text(
                    '只适用于模型显示的这一种切口对齐状态。先确认斜切没有被角块挡住，再完整执行公式恢复立方体外形。',
                    'This formula is for the exact aligned shape shown. Confirm no corner blocks the slash, then complete the formula to restore cube shape.',
                    '表示された切断位置が揃った形にのみ適用します。角が切断を妨げないことを確認し、公式を最後まで実行します。')),
                case(text('反向错位一格','Reverse one-unit offset','逆向きに1単位ずれた場合'),
                     (Square1Move(0,-1),Square1Move(1,1),Square1Move(2)),text(
                    '适用于上下层错位方向相反的对应状态；先核对模型方向和切口，再执行。',
                    'Use for the mirrored offset shown. Check the model orientation and cut alignment before following the formula.',
                    '上下層のずれ方向が逆の状態に使います。モデルの向きと切断位置を確認してから実行します。'))])]
    if kind in ('axis','pandora','windmill','fisher'):
        names={'axis':('轴心魔方','Axis Cube','アクシスキューブ'),'pandora':('潘多拉魔方','Pandora Cube','パンドラキューブ'),
               'windmill':('风火轮魔方','Windmill Cube','ウィンドミルキューブ'),'fisher':('移棱魔方','Fisher Cube','フィッシャーキューブ')}
        zh,en,ja=names[kind]
        # These shape modifications retain the ordinary 3x3 layer mechanism.
        # Teach the same recognizable layer-by-layer cases and algorithms,
        # while reminding learners to match the physical shape as well as colour.
        result=deepcopy(CASE_3X3)
        result[0]=dict(result[0],desc=text(
            f'{zh}沿用三阶转层结构。按贴纸颜色和块形状一起识别白底棱块，把白色棱块对到相邻面后用半圈归底。',
            f'{en} keeps the 3x3 layer mechanism. Identify each white edge by both sticker colours and piece shape, align its side colour, then turn it into the bottom layer.',
            f'{ja} は3×3の層回転機構です。色とピース形状で白い辺を見分け、側面色を合わせてから半回転で底面に入れます。'))
        result[1]=dict(result[1],desc=text(
            '先完成底层十字，再按目标角块的颜色与形状识别插入方向；白色朝右、朝前和角块反向时分别套用对应公式。',
            'After the bottom cross, identify the corner by its colours and shape. Choose the matching insertion formula for white facing right, facing front, or a reversed corner.',
            '底面の十字を作り、色と形で角を見分けます。白が右向き・前向き・逆向きの場合に対応する挿入公式を使います。'))
        result[2]=dict(result[2],desc=text(
            '目标棱块在顶层且侧色对正时，按所在位置使用右插或左插公式；中层棱反向时先取出，再转顶层后插回。',
            'When the target edge is in the top layer, align its side colour and use the right- or left-insertion algorithm. If a middle edge is flipped, take it out, turn the top, then insert it again.',
            '対象の辺が上層にある場合、側面色を合わせて右または左の挿入公式を使います。中段の辺が反転していたら、一度取り出して上層を回してから戻します。'))
        for item in result:
            item['desc']=dict(item['desc']) if isinstance(item['desc'],dict) else text(item['desc'],item['desc'],item['desc'])
            item['desc']['zh'] += ' 本例图示公式适用于当前标出的状态；先按示例方向拿稳魔方，再逐步跟做。'
            item['desc']['en'] += ' The displayed algorithm applies to the illustrated case; hold the puzzle in the shown orientation and follow it move by move.'
            item['desc']['ja'] += ' 表示された公式は図の状態に適用します。図と同じ向きで持ち、一手ずつ進めてください。'
        return result
    if kind=='mirror_tower':
        a,b=Move(0,0),Move(1,0)
        commutator=(a,b,a.inverse(3),b.inverse(3))
        reverse=(b,a,b.inverse(3),a.inverse(3))
        return [step(text('典型情况：相邻转轴公式','Typical case: adjacent-axis formula','典型例：隣接軸の公式'),text(
            '镜面魔塔按块的尺寸和朝向识别位置。先在模型上找到与案例相同的尺寸排列，再照公式逐步执行。此处每条公式对应模型展示的具体状态；×2表示反向转120°。',
            'Identify positions by piece size and orientation. Match the arrangement shown in the model, then follow the formula. Each formula applies to its displayed state; ×2 means a reverse 120-degree turn.',
            'ピースの大きさと向きで位置を見分けます。モデルの配置を確認してから公式を実行してください。各公式は表示状態に対応し、×2は120°の逆回転です。'),[
            case(text('相邻轴 A B A⁻¹ B⁻¹','Adjacent-axis A B A⁻¹ B⁻¹','隣接軸 A B A⁻¹ B⁻¹'),commutator,text(
                '先辨认模型展示的块形与尺寸错位，再按标出的两条转轴和层号执行完整公式。',
                'Match the piece shapes and size offsets shown, then complete the formula using the labelled axes and layers.',
                '表示されたピース形状と大きさのずれを確認し、軸と層番号に従って公式を最後まで実行します。')),
            case(text('反向相邻轴 A B A⁻¹ B⁻¹','Reverse adjacent-axis A B A⁻¹ B⁻¹','逆向きの隣接軸 A B A⁻¹ B⁻¹'),reverse,text(
                '适用于模型展示的反向排列。对照尺寸和朝向，确认与当前情况一致后再执行。',
                'Use for the reversed arrangement shown. Compare the sizes and orientations before applying it.',
                '表示された逆向きの配置に使います。大きさと向きが現在の状態に合うことを確認してください。'))])]
    if kind in ('mirror', 'mirror_axis', 'mirror_windmill', 'mirror_fisher',
                'mirror_windmill_unequal', 'mirror_fisher_unequal',
                'mirror_windmill_offset', 'mirror_fisher_offset'):
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
    if kind in ('petal_tetrahedron','petal_tetrahedron_nocentre'):
        from solver.petal_tetrahedron import prepared
        with_centres=kind=='petal_tetrahedron'
        cases=[]
        for i,example in enumerate(prepared(kind).get('examples',())):
            word=tuple(Move(*move) for move in example['word'])
            affected=tuple(example['affected'])
            item=case(text(f'联动错位 {i+1}',f'Coupled case {i+1}',f'連動ケース {i+1}'),word,text(
                f'适用：图示的 {len(affected)} 块联动错位，其余块已归位。拿法与图一致时，完整执行 {len(word)} 步；反向情况用逆公式。',
                f'Use when the {len(affected)} highlighted pieces match this case and the rest are solved. Match the grip and complete all {len(word)} moves. Use the inverse for the opposite case.',
                f'表示の{len(affected)}ピースが同じ状態で、他が揃っている場合。同じ持ち方で{len(word)}手を実行。逆の場合は逆手順。'))
            item['tutorial_targets']={p:str(j+1) for j,p in enumerate(affected)}
            item['show_all']=True
            item['camera']=_cycle_camera(g,affected)
            cases.append(item)
        return [step(text('典型情况：花瓣与中心联动' if with_centres else '典型情况：花瓣联动换位',
                          'Typical cases: coupled petals and centres' if with_centres else 'Typical cases: coupled petals',
                          '典型例：花びらと中心の連動' if with_centres else '典型例：花びらの連動'),text(
            '先对照模型的错位位置与方向，再使用对应公式。相关块的换位需要一起考虑。',
            'Match the shown positions and orientations before choosing a formula. The affected piece permutations are coupled.',
            '位置と向きを模型に合わせて公式を選びます。関係するピースの交換は連動します。'),cases)]
    if kind in ('petal_icosahedron','petal_icosahedron_nocentre'):
        from solver.blossom import _assets
        from solver.polyhedral import piece_orbits
        orbits=piece_orbits(kind,n)
        lessons=[]
        petal_group=0
        for index,macro in _assets(kind)['cycles'].items():
            orbit=orbits[int(index)]
            is_centre=len(orbit)==20
            if not is_centre:
                petal_group+=1
            name=text('三角中心三循环' if is_centre else f'花瓣组 {petal_group} 三循环',
                      'Triangle centre three-cycle' if is_centre else f'Petal group {petal_group} three-cycle',
                      '三角中心の三循環' if is_centre else f'花びら組 {petal_group} の三循環')
            word=tuple(Move(*move) for move in macro['word'])
            lessons.append(step(name,text(
                '适用：模型标出的三个同组块需要循环换位，其余块已归位。按所示拿法，完整执行公式；反向情况执行逆公式。仅支持整棱半转状态。',
                'Use when the three shown pieces need a cycle and all other pieces are solved. Match the shown grip and finish the whole formula; reverse it for the opposite cycle. Edge half-turn states only.',
                '表示された同じ組の3ピースを循環させ、他が揃っている場合。表示の持ち方で全手順を実行。逆循環は逆手順。辺の半回転状態のみ対応。'),[
                    case(name,word,text(
                        f'完整执行 {len(word)} 步后，其他块保持原状。',
                        f'After all {len(word)} moves, every other piece is unchanged.',
                        f'{len(word)}手をすべて実行すると他のピースは元に戻ります。'))]))
        return lessons
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
    formula_lessons=_cycle_formula_lessons(cube)
    if formula_lessons:
        return formula_lessons
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
        if n==2:
            return [step(text('典型情况：三条棱循环错位','Typical case: three cycled edges','典型例：3本の辺が循環'),text(
                '二阶恐龙魔方每次角转会循环相邻三条棱。当图示这组三条棱循环错位、其余块已复原时，按对应方向执行一次120°转动。',
                'Each order-two Dino corner turn cycles three adjacent edges. When the three edges shown are cycled and the rest is solved, use the matching 120° turn.',
                '2段ダイノの角回転は隣接する3本の辺を巡回させます。図の3本だけが循環し、他が揃っている場合、対応する向きに120°回します。'),[
                case(text('三棱正向循环','Cycle three edges forward','3本の辺を順方向に循環'),(a,),text(
                    '本例由该转动的逆公式构造；看清图示角轴，正向转一次即可复原。',
                    'This case is built from the inverse turn. Match the shown corner axis and turn forward once to solve it.',
                    '本例は回転の逆操作から作っています。図の角軸を合わせて1回回すと揃います。')),
                case(text('三棱反向循环','Cycle three edges backward','3本の辺を逆方向に循環'),(inverse(a),),text(
                    '与正向情况相反，按图示角轴反向转一次。',
                    'This is the opposite cycle; turn the shown corner axis in reverse once.',
                    '正方向とは逆の循環です。図の角軸を反対向きに1回回します。'))])]
        result[0]=dict(result[0],title=text('恐龙与格子的角转结构','Dino / Lattice corner turns'),desc=text(
            '恐龙魔方与格子魔方同属一组：恐龙以12个双色棱块为主体，格子在相同的八个角转方向上增加切层。'
            '每次转动120°；本组使用浅切的恐龙结构。A1至A8对应拧动页的转轴编号。',
            'Dino and Lattice cubes share eight shallow corner-turn directions. Dino has twelve two-colour '
            'edges; Lattice variants add layers to this mechanism. Each turn is 120 degrees. A1 through A8 '
            'match the twist-page axes.'))
    if kind=='ivy':
        result[0]=step(text('典型情况：角块和三片叶错位','Typical case: corner and three leaves','典型例：角と3枚の葉がずれている'),text(
            '当一个三色角块及其相邻三片叶形块呈现图示循环错位、其余块已还原时，执行该角轴的120°公式。A1至A4对应拧动页的四个转轴。',
            'When one three-colour corner and its three neighbouring leaves have the cycle shown while the rest is solved, apply the 120° algorithm for that corner axis. A1–A4 match the twist-page axes.',
            '3色コーナー1個と隣接する葉3枚だけが図のように循環している場合、その角軸の120°公式を使います。A1〜A4は回転画面の軸番号です。'),[
                case(text('角轴正转归位','Solve with a forward corner turn','角軸を正回転して戻す'),(a,),text(
                    '本例由该转动的逆公式构造；先找到图中错位的角和叶，再按相同方向转一次。',
                    'This case is built from the inverse turn. Locate the displaced corner and leaves shown, then turn the same axis once.',
                    '本例は回転の逆操作から作っています。図の角と葉を見つけ、同じ軸を1回回します。')),
                case(text('角轴反转归位','Solve with a reverse corner turn','角軸を逆回転して戻す'),(inverse(a),),text(
                    '若循环方向与上一例相反，使用反向公式。',
                    'Use the reverse algorithm when the cycle runs opposite to the previous case.',
                    '循環方向が前の例と逆の場合は、逆向きの公式を使います。'))])
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
