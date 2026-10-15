"""Situation-based 3x3 CFOP lessons with replayable, state-specific examples."""


def t(zh, en, ja):
    return {'zh': zh, 'en': en, 'ja': ja}


def case(name, moves, text, tip):
    return {'name': name, 'moves': moves, 'text': text, 'tip': tip}


CFOP_CASES = [
    {
        'title': t('C · 底层十字', 'C · Cross', 'C · クロス'),
        'desc': t(
            '十字主要靠观察和规划，没有一条固定公式。先找白色棱块，再看另一色对应哪个中心。本组用具体位置演示把棱块送入目标槽；实际复原时要同时规划四条白棱。',
            'The cross is planned piece by piece rather than solved with one fixed algorithm. Find a white edge and match its other colour to the centre. These examples show how a piece reaches its target; plan all four cross edges together in a real solve.',
            'クロスは決まった公式より、各ピースの位置を見て組み立てます。白いエッジを探し、もう一色を対応するセンターに合わせます。実際には4本をまとめて計画します。'),
        'cases': [
            case(t('前上白蓝棱 → 前下槽', 'White-blue edge at front-top', '前上の白青エッジ'), ['F2'],
                 'F2', t('按图示方向，白蓝棱在前上；前层半圈把它送入白底的前槽。先核对蓝色与蓝中心同面。',
                         'With the shown hold, the white-blue edge is at front-top. Turn F twice to place it in the front slot of the white cross; keep blue aligned with its centre.',
                         '図の向きで白青エッジが前上にあります。Fを半回転して白底の前スロットへ入れ、青をセンターに合わせます。')),
            case(t('右上白红棱 → 右侧槽', 'White-red edge at right-top', '右上の白赤エッジ'), ['R2'],
                 'R2', t('按图示方向，白红棱在右上；右层半圈把它送入白底右槽。实际十字中先确认红色对应红中心。',
                         'With the shown hold, the white-red edge is at right-top. Turn R twice to place it in the right cross slot; check red against its centre.',
                         '図の向きで白赤エッジが右上にあります。Rを半回転して白底の右スロットへ入れ、赤をセンターに合わせます。')),
        ],
    },
    {
        'title': t('F2L · 前两层角棱配对', 'F2L · Pair and insert', 'F2L · コーナーとエッジ'),
        'desc': t(
            'F2L 一组同时还原一个底角和相邻中棱。先认出同色角棱，再把它们配成一对，最后插入对应槽位。下面的右插和左插公式只对应各自缩略图显示的摆法。',
            'Each F2L pair solves one first-layer corner and its matching middle-layer edge together. Identify the matching pieces, pair them, then insert them into the correct slot. The right and left algorithms apply to the holds shown in their thumbnails.',
            'F2Lは底角と対応する中段エッジをペアにして同時に入れます。色を見分けてペアを作り、正しいスロットへ入れます。左右の公式は各サムネイルの向きに使います。'),
        'cases': [
            case(t('右前槽：右插配对', 'Right-front slot: right insert', '右前スロット：右挿入'),
                 ['U', 'R', "U'", "R'", "U'", "F'", 'U', 'F'],
                 "U R U' R' U' F' U F",
                 t('先把角棱配对，再按图示把这一对送入右前槽。执行前确认目标槽在右前，白色保持在底面。',
                   'Pair the corner and edge first, then insert as shown. Before starting, hold the target slot at front-right and keep white on the bottom.',
                   '角とエッジをペアにしてから図のように入れます。開始前に対象スロットを右前にし、白を底面に保ちます。')),
            case(t('左前槽：左插配对', 'Left-front slot: left insert', '左前スロット：左挿入'),
                 ["U'", "L'", 'U', 'L', 'U', 'F', "U'", "F'"],
                 "U' L' U L U F U' F'",
                 t('这是右插的镜像方向。按图确认目标槽在左前，再逐步执行；若块色与图不一致，先转 U 对位。',
                   'This is the mirrored left insert. Confirm the target slot is front-left; if the pieces do not match the picture, align them with U first.',
                   '右挿入の左右反転です。対象スロットが左前か確認します。色の位置が図と違う場合は、先にUで合わせます。')),
        ],
    },
    {
        'title': t('O · 顶层朝向（OLL）', 'O · Orient the last layer', 'O · 最終層の向き'),
        'desc': t(
            '先保持前两层完成，再让顶层黄色贴纸朝上。先看黄色棱是点、拐角还是一字，再看角块朝向。案例按图示状态给出公式；顺小鱼和反小鱼是常见的两向情况。',
            'Keep the first two layers solved and orient the last-layer stickers upward. Read the edge pattern first, then the corner pattern. Each algorithm is tied to the state shown; Sune and Anti-Sune cover two common corner cases.',
            '前二層を保ったまま、最終層の黄色を上向きにします。まずエッジの形、次にコーナーの向きを見ます。各公式は図の状態に対応し、SuneとAnti-Suneはよくある向きです。'),
        'cases': [
            case(t('顶棱：一字／拐角', 'Edges: line or L', 'エッジ：線またはL字'),
                 ['F', 'R', 'U', "R'", "U'", "F'"],
                 "F R U R' U' F'",
                 t('按缩略图把一字横放，或把拐角放在左后；执行后顶面形成黄色十字。不要在前两层未完成时套用。',
                   'Hold the line horizontally, or the L at back-left as pictured. This forms the yellow cross. Use it after F2L is solved.',
                   '図のように線を横向き、またはL字を左奥にします。黄色のクロスができます。F2L完成後に使います。')),
            case(t('顶角：顺小鱼（Sune）', 'Corners: Sune', 'コーナー：Sune'),
                 ['R', 'U', "R'", 'U', 'R', 'U2', "R'"],
                 "R U R' U R U2 R'",
                 t('匹配图中黄色角块的朝向，鱼头朝向与图一致时用顺小鱼。公式会保留前两层。',
                   'Match the yellow-corner pattern and fish-head direction in the picture. Sune preserves the first two layers.',
                   '図の黄色コーナーと魚の向きを合わせてSuneを使います。前二層は保たれます。')),
            case(t('顶角：反小鱼（Anti-Sune）', 'Corners: Anti-Sune', 'コーナー：Anti-Sune'),
                 ['R', 'U2', "R'", "U'", 'R', "U'", "R'"],
                 "R U2 R' U' R U' R'",
                 t('这是顺小鱼的反向典型情况。按图旋转整只魔方以匹配角块朝向，再执行公式。',
                   'This is the opposite common corner case. Rotate the whole cube to match the pictured orientation before applying it.',
                   'Suneと逆向きの代表例です。図に合わせて魔方全体の向きを整えてから使います。')),
        ],
    },
    {
        'title': t('P · 顶层位置（PLL）', 'P · Permute the last layer', 'P · 最終層の位置'),
        'desc': t(
            'OLL 完成后顶面颜色已统一，只剩顶层角棱换位。先识别块的循环方式和已对齐的侧面，再选择公式。以下公式只用于图示的顶层排列，执行时保持黄色朝上。',
            'After OLL, the top colour is uniform and only last-layer pieces need to move. Identify the cycle and any aligned side, then choose the matching algorithm. Keep yellow on top and use each algorithm for the pictured permutation.',
            'OLL後は上面の色が揃い、最終層の位置だけが残ります。循環と揃っている側面を見て公式を選びます。黄色を上に保ち、図の配置に使ってください。'),
        'cases': [
            case(t('T-Perm：相邻角棱交换', 'T-Perm: adjacent corner and edge swap', 'T-Perm：隣接コーナーとエッジ交換'),
                 ['R', 'U', "R'", "U'", "R'", 'F', 'R2', "U'", "R'", "U'", 'R', 'U', "R'", "F'"],
                 "R U R' U' R' F R2 U' R' U' R U R' F'",
                 t('适用于图示的相邻两角交换并伴随棱块换位。先把黄色朝上，核对两角位置后完整执行。',
                   'Use for the pictured adjacent corner swap with its matching edge permutation. Keep yellow on top and verify the corner positions first.',
                   '図の隣接する2コーナー交換とエッジ配置に使います。黄色を上にして、コーナー位置を確認してから実行します。')),
            case(t('U-Perm：三棱循环', 'U-Perm: three-edge cycle', 'U-Perm：3本のエッジ循環'),
                 ['R', "U'", 'R', 'U', 'R', 'U', 'R', "U'", "R'", "U'", 'R2'],
                 "R U' R U R U R U' R' U' R2",
                 t('适用于图示三条顶棱循环、角块已定位的情况。把未对齐的一侧放在背面，再执行公式。',
                   'Use when the three top edges cycle as pictured and the corners are placed. Put the unsolved side at the back before starting.',
                   '図のように3本の上エッジが循環し、コーナーが揃っている場合に使います。未完成の面を後ろにして実行します。')),
        ],
    },
]
