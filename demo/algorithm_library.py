"""Offline advanced-method catalog and state-specific animated examples."""
from functools import lru_cache
import json
from pathlib import Path
import re

from demo.formula_notation import FormulaCube, FormulaPolyhedralCube, NotationError, compile_algorithm
from demo.solutions import inverse_demo_move, solved_demo_cube

PUZZLES = ('2x2', '3x3', '4x4', '5x5', 'SQ1', 'Skewb', 'Pyraminx', 'Megaminx')
MODES = {'2x2': 2, '3x3': 3, '4x4': 4, '5x5': 5, 'SQ1': ('square1', 3),
         'Skewb': ('skewb', 3), 'Pyraminx': ('pyraminx', 3), 'Megaminx': ('megaminx', 3)}

# Prerequisites are written here rather than copied from the source website.
METHODS = {
    'OrtegaOLL': ('Ortega OLL · 顶面朝向', '底面一面已完成；识别顶面角块朝向，再翻好顶面。'),
    'OrtegaPBL': ('Ortega PBL · 两层换位', '上下两面颜色已统一；同时识别两层相邻／对角角块的排列。'),
    'CLL': ('CLL · 一步还原顶角', '底层连同侧色已经完成；识别顶角朝向和相对位置。'),
    'EG1': ('EG-1 · 底层相邻交换', '底面颜色统一，底层有一对相邻角块需要交换；同时识别顶层情况。'),
    'EG2': ('EG-2 · 底层对角交换', '底面颜色统一，底层有一对对角角块需要交换；同时识别顶层情况。'),
    'F2L': ('F2L · 角棱配对', '底层十字已完成；识别同一槽位的角块与棱块的位置、朝向和连接方式。'),
    'AdvancedF2L': ('进阶 F2L', '十字已完成；本组处理角棱在槽内、被卡住或需要利用空槽的情况。'),
    'OLL': ('OLL · 顶层朝向', '前两层已完成；识别顶层颜色在顶面及四个侧面的分布，不要求顶块位置先对齐。'),
    'PLL': ('PLL · 顶层换位', '前两层和顶面颜色已完成；识别顶层角棱循环、色条和车灯的排列。'),
    'COLL': ('COLL · 顶角朝向与位置', '前两层已完成、顶棱朝向已统一；一步处理顶角，棱块位置留到后续。'),
    'CMLL': ('CMLL · Roux 顶角', 'Roux 左右两个 1×2×3 块已完成；处理四个顶角，允许中层棱继续变化。'),
    'SBLS': ('SBLS · Roux 第二块最后槽', 'Roux 第一块已完成；识别第二块最后一个槽的角棱关系。'),
    'EO4A': ('EO 4a · Roux 棱朝向', 'Roux 两块和顶角已完成；识别剩余棱的朝向。'),
    'WV': ('WV · Winter Variation', '顶棱已定向；最后一组 F2L 角棱已配对，插入时同时完成顶角朝向。'),
    'SV': ('SV · Summer Variation', '顶棱已定向；识别最后一组角棱及顶角朝向，边插入边完成定向。'),
    'CLS': ('CLS · 最后槽角块', '最后一槽的棱已处理；结合槽中角块与顶角的朝向选择公式。'),
    'FRUF': ("F <R,U> F'", '按模型识别最后槽及顶层关系；本组用前面准备动作配合 R、U 操作。'),
    'ELL': ('ELL · 顶层棱朝向与位置', '四个顶角已还原；一步处理顶层棱的朝向和位置。'),
    'AntiPLL': ('Anti-PLL', '识别本组模型中顶层角棱的排列及朝向；与普通 PLL 的识别条件分别核对。'),
    'ZBLL': ('ZBLL · 顶棱定向后一步还原', '前两层已完成且四条顶棱朝向正确；同时识别顶角朝向、角排列与棱排列。'),
    'VLS': ('VLS · 最后槽与顶层朝向', '前三组 F2L 已完成；最后一组角棱在指定位置，同时识别顶层朝向。'),
    'OLLCP': ('OLLCP · 顶面朝向与角排列', '前两层已完成；结合 OLL 形状与顶角的相对位置选择公式，棱排列可留到后续。'),
    '1LLL': ('1LLL · 一步还原顶层', '前两层已完成；同时识别全部顶层角棱的朝向和排列。'),
    'OLLParity': ('OLL 奇偶 · 单棱翻转', '中心和棱已配对；降阶后出现一条逻辑棱翻转，普通三阶 OLL 无法单独处理。'),
    'PLLParity': ('PLL 奇偶 · 排列特殊情况', '中心和棱已配对；识别逻辑棱交换和顶角排列，选择与模型相同的情况。'),
    'L2C': ('L2C · 最后两中心', '前四个中心已完成；识别最后两个中心内条带及单块的相对位置。'),
    'L2E': ('L2E · 最后两棱', '中心及其余十组棱已完成；识别最后两组翼块相对中棱的位置及朝向。'),
    'SQ1CS': ('Cube Shape · 复原外形', '按上下层宽角块、窄棱块的轮廓识别外形；每次斜切前确认切口没有跨过角块。'),
    'SQ1CO': ('CO · 上下层角块分色', '先恢复立方体外形；按角块顶色区分上下层，识别图示需要换层的角块。'),
    'SQ1EO': ('EO · 上下层棱块分色', '立方体外形及角块分色已完成；识别需要在上下层之间交换的棱块。'),
    'SQ1CP': ('CP · 角块排列', '上下层分色已完成；按角块侧色识别相邻交换、对角交换和循环关系。'),
    'SQ1EP': ('EP · 棱块排列', '角块已定位；按上下两层棱块侧色识别排列，执行后核对中层方向。'),
    'SQ1Parity': ('Parity · SQ1 奇偶', '立方体外形已恢复；识别图示奇偶排列并核对角棱、上下层位置。'),
    'Lin': ('Lin · 进阶排列', '使用 Lin 方法完成对应前置阶段；同时核对上下层角棱位置与奇偶情况。'),
    'SarahsAdvanced': ("Sarah’s Advanced · 斜转进阶", '第一面及其相邻角块侧色已完成；同时识别其余角块和五个中心的排列。'),
    'L3E': ('L3E · 最后三棱', '金字塔第一层已完成；识别最后三条双色棱的循环和朝向。'),
    'L4E': ('L4E · 最后四棱', '金字塔已完成一个匹配角及两条相邻棱；识别其余四棱的位置和朝向。'),
    'MegaminxEO': ('EO · 五魔方顶棱朝向', '前面各层已完成；观察五条顶棱的顶色朝向，角块暂不参与识别。'),
    'MegaminxCO': ('CO · 五魔方顶角朝向', '前面各层和顶棱朝向已完成；识别五个顶角的顶色方向。'),
    'MegaminxEP': ('EP · 五魔方顶棱排列', '识别顶层五条棱的相对位置与循环方向，先对齐可用的参考侧面。'),
    'MegaminxCP': ('CP · 五魔方顶角排列', '识别顶层五个角块的相对位置；核对配色顺序和循环方向。'),
    'MegaminxOLL': ('OLL · 五魔方顶层朝向', '前面各层已完成；同时识别五条顶棱与五个顶角的朝向。'),
    'MegaminxPLL': ('PLL · 五魔方顶层排列', '前面各层及顶面颜色已完成；结合侧面色条识别五角、五棱的排列。'),
}


@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).parent / 'data' / 'speedcubedb.json').read_text(encoding='utf-8'))


def family(set_id):
    name = set_id.split('/')[1]
    for prefix in ('MegaminxOLL', 'MegaminxPLL', 'OLLCP', 'ZBLL', '1LLL', 'VLS'):
        if name.startswith(prefix):
            return prefix
    if name.startswith('SQ1Lin'):
        return 'Lin'
    return name


@lru_cache(maxsize=8)
def groups(puzzle):
    merged = {}
    for source in catalog()['sets']:
        if source['puzzle'] != puzzle:
            continue
        group = family(source['id'])
        target = merged.setdefault(group, {'id': group, 'puzzle': puzzle, 'cases': []})
        for case in source['cases']:
            target['cases'].append(dict(case, set_id=source['id'], source_set=source['name']))
    def order(group):
        return list(METHODS).index(group) if group in METHODS else len(METHODS)
    return tuple(merged[key] for key in sorted(merged, key=order))


def title(group, language='zh'):
    return METHODS.get(group['id'], (group['id'],))[0] if language == 'zh' else group['id']


def prerequisite(group, language='zh'):
    if language == 'zh':
        return METHODS.get(group['id'], ('', '先对照模型识别目标块的朝向与相对位置。'))[1]
    if language == 'ja':
        return f"{group['id']}：この方法の前段階を完成させ、モデルの向き・側面色・ピース配置を照合してください。"
    return f"{group['id']}: complete the method's preceding stage, then match the model's orientation, side colours and piece pattern."


def solved(puzzle):
    if puzzle in ('2x2', '3x3', '4x4', '5x5'):
        return FormulaCube(int(puzzle[0]))
    if puzzle in ('Skewb', 'Pyraminx', 'Megaminx'):
        return FormulaPolyhedralCube(MODES[puzzle][0], 3)
    return solved_demo_cube(MODES[puzzle])


def prepare_algorithm(puzzle, algorithm):
    _, animated = initial_hold(puzzle, algorithm)
    moves = compile_algorithm(puzzle, animated)
    initial = solved(puzzle)
    for move in reversed(moves):
        initial.apply_move(inverse_demo_move(move, initial))
    return initial, moves


def initial_hold(puzzle, algorithm):
    # Some Megaminx authors use an initial x' grip change with no defined
    # dodecahedral rotation angle. Present the model after this initial hold,
    # preserving the published formula separately. Never invent a 90° minx turn.
    if puzzle == 'Megaminx':
        match = re.match(r"^\s*(x'?)(?:\s+)(.+)$", algorithm)
        if match:
            return match[1], match[2]
    return '', algorithm


def prepare_case(group, item, alternative=None):
    if alternative is None and 'error' in item:
        raise NotationError(item['error'])
    indices = [alternative] if alternative is not None else list(range(len(item['algorithms'])))
    if alternative is None and 'selected' in item:
        indices.remove(item['selected'])
        indices.insert(0, item['selected'])
    errors = []
    for index in indices:
        try:
            initial, moves = prepare_algorithm(group['puzzle'], item['algorithms'][index])
            verify_case_scope(group['puzzle'], group['id'], initial)
            break
        except (ValueError, KeyError, IndexError) as exc:
            errors.append(str(exc))
    else:
        raise NotationError('; '.join(dict.fromkeys(errors)))
    from demo.irregular_cases import text
    situation = item.get('group') or item['name']
    tip = text(
        f"识别分组：{situation}。先把实物摆成模型的方向，核对目标块及相邻侧色，再完整执行公式。公式结束前，其他块可能暂时离开原位。",
        f"Pattern group: {situation}. Match the hold, target pieces and adjacent colours before applying the full algorithm. Other pieces can move temporarily.",
        f"分類：{situation}。持ち方・対象ピース・隣接面の色をモデルと照合してから公式全体を実行してください。")
    case = {'name': item['name'], 'text': item['algorithms'][index], 'tip': tip,
            'initial': initial, 'moves': moves, 'show_all': True, 'source_url': item['url'],
            'alternative': index}
    hold, animated = initial_hold(group['puzzle'], case['text'])
    if hold:
        case['source_algorithm'] = case['text']
        case['text'] = animated
        case['tip'] = text(
            f"起始模型已摆好 {hold} 的拿法。" + tip['zh'],
            f"The initial model already includes the {hold} grip change. " + tip['en'],
            f"開始モデルは {hold} の持ち替え後です。" + tip['ja'])
    if group['puzzle'] == 'Pyraminx':
        case['camera'] = (135, math_degrees_tetra(), 180)
    return case


def verify_case_scope(puzzle, group_id, initial):
    """Check independent stage prerequisites, beyond inverse/replay identity."""
    method = family(puzzle + '/' + group_id)
    if puzzle == '3x3' and method in ('OLL', 'PLL', 'COLL', 'ZBLL', '1LLL', 'OLLCP', 'ELL', 'AntiPLL'):
        from cube.conversion import cubies_to_facelets
        faces = cubies_to_facelets(initial.cubies, 3)
        if any(len({v for row in faces[face][1:] for v in row}) != 1 for face in ('F', 'R', 'B', 'L')) or len({v for row in faces['D'] for v in row}) != 1:
            raise NotationError('This source alternative does not preserve the first two layers')
        if method == 'PLL' and len({v for row in faces['U'] for v in row}) != 1:
            raise NotationError('This source PLL alternative does not preserve top orientation')
    if puzzle in ('Skewb', 'Pyraminx', 'Megaminx'):
        g = initial.geometry
        count = sum(len({initial.colors[i] for i, sticker in enumerate(g.stickers) if sticker.face == face}) == 1
                    for face in range(len(g.spec.normals)))
        if puzzle == 'Skewb' and count < 1:
            raise NotationError('This source alternative does not preserve a completed first face')
        if puzzle == 'Skewb':
            def completed_layer(face):
                stickers = [i for i, sticker in enumerate(g.stickers) if sticker.face == face]
                if len({initial.colors[i] for i in stickers}) != 1:
                    return False
                corners = {g.stickers[i].piece for i in stickers if len(g.pieces[g.stickers[i].piece]) == 3}
                return all(len({initial.colors[i] for i, sticker in enumerate(g.stickers)
                                if sticker.piece in corners and sticker.face == other}) <= 1
                           for other in range(6) if other != face)
            if not any(completed_layer(face) for face in range(6)):
                raise NotationError('The first-face corners do not have matching side colours')
        if puzzle == 'Pyraminx' and method == 'L3E' and count < 1:
            raise NotationError('This source alternative does not preserve the first layer')
        if puzzle == 'Megaminx' and count < 6:
            raise NotationError('This source alternative disturbs layers below the last layer')


def math_degrees_tetra():
    import math
    return math.degrees(math.atan(1 / math.sqrt(2)))


def lesson(group, item, alternative=None):
    from demo.irregular_cases import text
    case = prepare_case(group, item, alternative)
    description = text(prerequisite(group, 'zh'), prerequisite(group, 'en'), prerequisite(group, 'ja'))
    return [{'title': text(title(group), title(group, 'en'), title(group, 'ja')),
             'desc': description, 'cases': [case]}]


def search_cases(group, query):
    words = query.casefold().split()
    return [item for item in group['cases'] if all(word in ' '.join((item['name'], item.get('group', ''),
             item.get('source_set', ''), ' '.join(item['algorithms']))).casefold() for word in words)]
