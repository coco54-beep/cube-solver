"""教学案例文本的英文 / 日文翻译表。

以 demo/cases.py 中的中文原文为键，避免改动案例数据结构；公式（moves）
不翻译。未收录的字符串原样返回。
"""

_EN = {
    # ---- 2 阶 ----
    "还原第一层（底层角块）": "Solve the first layer (bottom corners)",
    "2 阶只有 8 个角块。先选定一面为白底，把白角块归位并使侧面颜色与"
    "相邻四个侧面颜色一致，即完成第一层。先把白角转到其正确位置上方，"
    "再按下述公式插入。":
        "A 2×2 has only 8 corners. Pick a white bottom face, place each white "
        "corner correctly, and match the side colors with the four adjacent "
        "faces to finish the first layer. Bring a white corner above its target "
        "slot, then insert it with a formula below.",
    "顶面翻色（OLL）": "Orient the last face (OLL)",
    "第一层完成后，把顶面 4 个角块翻成黄色（或所选顶色）。2 阶无棱块，"
    "只需处理角块朝向；学会小鱼公式即可应对所有情况。":
        "After the first layer, orient the 4 top corners so the top becomes "
        "yellow (or your chosen top color). A 2×2 has no edges, so you only "
        "orient corners; the Sune formula handles every case.",
    "顶角归位（PLL）": "Permute the last corners (PLL)",
    "顶面全黄后，只需调整四个角块的侧面颜色，使其与所在面一致，即完成还原。"
    "用一个交换相邻两角的公式即可。":
        "Once the top is all yellow, only the side colors of the four corners "
        "need fixing; one formula that swaps two adjacent corners is enough.",
    "2-1 白面朝右": "2-1 White faces right",
    "公式 2-1：(R U R')": "Formula 2-1: (R U R')",
    "白色朝右，先转右层": "White faces right; turn the right layer first",
    "2-2 白面朝前": "2-2 White faces front",
    "公式 2-2：(F'U'F)": "Formula 2-2: (F'U'F)",
    "白色朝前，先转前层": "White faces front; turn the front layer first",
    "2-3 白面在顶层": "2-3 White on the top layer",
    "公式 2-3：(R U R') U' (R U R')": "Formula 2-3: (R U R') U' (R U R')",
    "白角在顶层侧面先替换下来": "A white corner on the top side: replace it down first",
    "3-1 小鱼（顺）": "3-1 Sune (clockwise)",
    "公式 3-1：R U R' U R U2 R'": "Formula 3-1: R U R' U R U2 R'",
    "顺时针小鱼，翻角成全黄": "Clockwise Sune; twists corners to all yellow",
    "3-2 小鱼（逆）": "3-2 Anti-Sune (counter-clockwise)",
    "公式 3-2：R U2 R' U' R U' R'": "Formula 3-2: R U2 R' U' R U' R'",
    "逆时针小鱼": "Counter-clockwise Sune",
    "3-3 顶面一点黄": "3-3 Only one yellow on top",
    "小鱼 ×2": "Sune ×2",
    "顶面只有一个黄角时连做两次小鱼": "With only one yellow corner, do Sune twice",
    "4-1 交换角块": "4-1 Swap corners",
    "公式 4-1：R' F R' B2 R F' R' B2 R2": "Formula 4-1: R' F R' B2 R F' R' B2 R2",
    "只调整顶角位置": "Permutes the top corners only",

    # ---- 3 阶 ----
    "底棱归位（底部架十字）": "Place the bottom edges (build the bottom cross)",
    "以白为底。把四个白棱转到顶面与黄中心同面，转动上层使侧面颜色"
    "对到对应中心（蓝/红/橙/绿），再转 180° 放到底部。注意相对顺序："
    "白红在白蓝右、白橙在白蓝左、白绿在白蓝对面。":
        "Work with white on the bottom. Bring the four white edges to the top "
        "face next to the yellow center, turn the top layer so each side color "
        "matches its center (blue/red/orange/green), then turn 180° down to the "
        "bottom. Mind the order: white-red right of white-blue, white-orange "
        "left of white-blue, white-green opposite white-blue.",
    "底角归位（第一层角块）": "Place the bottom corners (first-layer corners)",
    "目标角块先调至其正确位置的正上方，看白色朝何方判断是哪种情况"
    "（2-1~2-5）。不必死记，理解「把白角与底棱连成 1×1×2 整体再归位」。":
        "Move a target corner directly above its correct slot and read which way "
        "white faces to decide the case (2-1 to 2-5). Don't memorize blindly; "
        "understand “join the white corner to a bottom edge as a 1×1×2 block, "
        "then place it”.",
    "中棱归位（中层棱块）": "Place the middle edges",
    "中层四个棱块复原。3-1/3-2 是两种常见情形；若棱块在中间层但方向反"
    "（图 301），先用 3-1 或 3-2 把它换到顶层，再插回正确位置。":
        "Solve the four middle-layer edges. 3-1/3-2 are the two common cases; "
        "if an edge is in the middle layer but flipped (fig. 301), first use "
        "3-1 or 3-2 to move it to the top, then insert it correctly.",
    "顶棱面位（顶层十字）": "Orient the top edges (top cross)",
    "只用公式 4 即可完成顶部十字。按情况用 1 次（4-1 一字）、2 次（4-2）"
    "或 3 次（4-3）。做前注意上层位置，把已面位的棱转到左上/右上。":
        "Formula 4 alone builds the top cross. Use it 1 time (4-1 line), 2 times "
        "(4-2) or 3 times (4-3) as needed. Before each, rotate the top layer so "
        "the oriented edges sit at the upper-left/upper-right.",
    "顶角面位（顶层角块翻色）": "Orient the top corners",
    "顶层架十字后，把四角翻成顶面全黄。若已有一角黄面在前右，看是 5-1"
    "或 5-2；其它情况先把一个角面位，再照图示处理（如 503：5-2→U2→5-1）。":
        "After the top cross, twist the four corners until the top is all "
        "yellow. If one corner is already yellow at front-right, pick 5-1 or "
        "5-2; otherwise orient one corner first, then follow the figure "
        "(e.g. 503: 5-2→U2→5-1).",
    "顶角归位（顶层角块位置）": "Permute the top corners",
    "让四个角块另外两面的颜色与所在面的中心块一致，即完成角块归位。":
        "Make the other two side colors of the four corners match the adjacent "
        "centers, completing corner permutation.",
    "顶棱归位（顶层棱块位置）": "Permute the top edges",
    "让四个棱块另一面的颜色与所在面的中心块一致，即全部还原。":
        "Make the other side color of each of the four edges match the center of "
        "its face; the cube is then fully solved.",
    "白蓝棱块（顶面已对位）": "White-blue edge (aligned on top)",
    "公式 1-1：F2": "Formula 1-1: F2",
    "顶层对位后 180° 放到底部": "After aligning on top, turn 180° down to the bottom",
    "白红棱块（从右层下来）": "White-red edge (bring down from the right)",
    "公式 1-2：R2": "Formula 1-2: R2",
    "白红需放白蓝右边": "White-red goes to the right of white-blue",
    "棱块先到顶面再对位": "Send the edge to the top, then align",
    "公式 1-3：F R U R' U' F'": "Formula 1-3: F R U R' U' F'",
    "先上顶面，再对侧色放下": "Go up to the top first, then drop with the side color aligned",
    "2-1 白色朝右": "2-1 White faces right",
    "白色朝右，第一步转右层": "White faces right; first turn the right layer",
    "2-2 白色朝前": "2-2 White faces front",
    "白色朝前，第一步转前层": "White faces front; first turn the front layer",
    "2-3 用两次 2-1": "2-3 Do 2-1 twice",
    "用两次 2-1：(R U R') U' (R U R')": "Do 2-1 twice: (R U R') U' (R U R')",
    "角块在顶层侧面": "Corner on the top side",
    "2-4 用两次 2-2": "2-4 Do 2-2 twice",
    "用两次 2-2：(F'U'F) U (F'U'F)": "Do 2-2 twice: (F'U'F) U (F'U'F)",
    "角块在顶层另一侧": "Corner on the other side of the top",
    "2-5 用三次 2-1": "2-5 Do 2-1 three times",
    "用三次 2-1：(R U R') U' (R U R') U' (R U R')":
        "Do 2-1 three times: (R U R') U' (R U R') U' (R U R')",
    "角块方向特殊": "Corner has an unusual orientation",
    "3-1 棱块需向右": "3-1 Edge must go right",
    "公式 3-1：U R U' R' U' F' U F": "Formula 3-1: U R U' R' U' F' U F",
    "先右后前，插向右前": "Right then front; insert to the front-right",
    "3-2 棱块需向左": "3-2 Edge must go left",
    "公式 3-2：U' F' U F U R U' R'": "Formula 3-2: U' F' U F U R U' R'",
    "先后右，插向左前": "Front then right; insert to the front-left",
    "图 301 棱块方向反": "Fig. 301 Edge is flipped",
    "先做 3-1 换到顶层": "Do 3-1 to move it to the top",
    "把反了的棱换到顶层再插回": "Move the flipped edge up, then insert it back",
    "4-1 一字": "4-1 Line",
    "公式 4：F R U R' U' F'（用 1 次）": "Formula 4: F R U R' U' F' (once)",
    "顶面黄成一字": "Top yellow forms a line",
    "4-2 拐角": "4-2 Corner (L-shape)",
    "公式 4 用 2 次（中间转 U）": "Formula 4 twice (turn U in between)",
    "顶面黄成拐角": "Top yellow forms an L",
    "4-3 点": "4-3 Dot",
    "公式 4 用 3 次（中间转 U）": "Formula 4 three times (turn U in between)",
    "顶面只有一个黄点": "Only one yellow dot on top",
    "5-1 小鱼（顺）": "5-1 Sune (clockwise)",
    "公式 5-1：R U R' U R U2 R'": "Formula 5-1: R U R' U R U2 R'",
    "5-2 小鱼（逆）": "5-2 Anti-Sune (counter-clockwise)",
    "公式 5-2：R U2 R' U' R U' R'": "Formula 5-2: R U2 R' U' R U' R'",
    "图 503 特殊": "Fig. 503 Special case",
    "先反小鱼，转上层再正小鱼": "Anti-Sune, turn U, then Sune",
    "6-1 交换角块": "6-1 Swap corners",
    "公式 6-1：R' F R' B2 R F' R' B2 R2": "Formula 6-1: R' F R' B2 R F' R' B2 R2",
    "只调整角块位置": "Permutes the corners only",
    "7-1 三棱循环": "7-1 3-edge cycle",
    "公式 7-1：F2 U L R' F2 L' R U F2": "Formula 7-1: F2 U L R' F2 L' R U F2",
    "完成还原": "Cube solved",

    # ---- 4 阶 ----
    "完成六面中心块": "Solve the six face centers",
    "先把黄、白两面中心拼好（保持不破坏），再把黄白放左右两侧，"
    "用 Rw/Lw 系列公式完成蓝红绿橙四面。注意配色：上黄下白、前蓝后绿、"
    "左橙右红。":
        "First pair the yellow and white centers (without breaking them), place "
        "yellow/white on the left and right, then use Rw/Lw formulas to finish "
        "the blue, red, green and orange centers. Mind the color scheme: yellow "
        "up/white down, blue front/green back, orange left/red right.",
    "完成 12 对棱块": "Pair all 12 edges",
    "只需掌握一个拼棱公式：先让一对棱同在上或同在下，上两层往右错开，"
    "做一次原地翻棱公式，再返回。左右两侧一上一下时先翻棱再拼棱。":
        "You only need one pairing formula: put a pair of edges both on top or "
        "both on the bottom, shift the top two layers to the right, do one "
        "in-place flip formula, then return. When the two sides are one up/one "
        "down, flip first, then pair.",
    "当作三阶完成": "Finish as a 3×3",
    "中心与棱都配对后，4 阶等效 3 阶，直接用三阶复原公式完成。":
        "Once centers and edges are paired, the 4×4 is a 3×3; finish it with 3×3 algorithms.",
    "特殊情况处理": "Special cases",
    "降到三阶后可能出现 P 特（对棱换）与 O 特（单棱翻），用对应公式修复。":
        "After reduction to 3×3, a P-parity (opposite-edge swap) or O-parity "
        "(single flipped edge) may appear; fix it with the matching formula.",
    "图101 中心在右上": "Fig.101 Center at upper-right",
    "公式：Rw U Rw'（即 r U r'）": "Formula: Rw U Rw' (i.e. r U r')",
    "右侧用右手转上来，再转到左侧": "Turn the right up with your right hand, then to the left",
    "图102 中心在左上": "Fig.102 Center at upper-left",
    "公式：Rw U' Rw'（即 r U' r'）": "Formula: Rw U' Rw' (i.e. r U' r')",
    "右手转上来，再转回左侧": "Turn up with the right hand, then back to the left",
    "图103 左侧中心": "Fig.103 Left-side center",
    "公式：Lw' U Lw（即 l' U l）": "Formula: Lw' U Lw (i.e. l' U l)",
    "左侧用左手转上来": "Turn the left up with your left hand",
    "图104 左侧中心": "Fig.104 Left-side center",
    "公式：Lw' U' Lw（即 l' U' l）": "Formula: Lw' U' Lw (i.e. l' U' l)",
    "左手转上来再转回": "Turn up with the left hand, then back",
    "图105 同侧在右": "Fig.105 Same side, on the right",
    "公式：Rw U2 Rw'（即 r U2 r'）": "Formula: Rw U2 Rw' (i.e. r U2 r')",
    "同侧在右，右侧先上": "Both on the right; turn the right up first",
    "图106 同侧在左": "Fig.106 Same side, on the left",
    "公式：Lw' U2 Lw（即 l' U2 l）": "Formula: Lw' U2 Lw (i.e. l' U2 l)",
    "同侧在左，左侧先上": "Both on the left; turn the left up first",
    "图201 原地翻棱公式": "Fig.201 In-place edge flip formula",
    "原地翻棱：R U R' F R' F' R": "In-place flip: R U R' F R' F' R",
    "右侧棱块原地翻转（练 100 遍）": "Flips the right edge in place (practice 100 times)",
    "图203 拼棱公式": "Fig.203 Edge-pairing formula",
    "拼棱：Uw'（R U R' F R' F' R）Uw": "Pairing: Uw' (R U R' F R' F' R) Uw",
    "上两层错开 → 翻棱 → 返回": "Shift the top two layers → flip → return",
    "图205 一上一下": "Fig.205 One up, one down",
    "先翻棱再拼棱": "Flip first, then pair",
    "左一上一下：先翻棱再对棱": "One up/one down on the left: flip, then pair",
    "三阶小鱼公式": "3×3 Sune formula",
    "三阶小鱼：R U R' U R U2 R'": "3×3 Sune: R U R' U R U2 R'",
    "当三阶用七步法还原": "Solve as a 3×3 with the seven-step method",
    "图401 对棱换（P特）": "Fig.401 Opposite-edge swap (P-parity)",
    "对棱换：Uw2（MR2 U2）2 MR2 Uw2": "Opposite swap: Uw2 (MR2 U2)2 MR2 Uw2",
    "P特公式": "P-parity formula",
    "图402 单棱翻（O特）": "Fig.402 Single-edge flip (O-parity)",
    "单棱翻：O 特公式（可动画版）": "Single flip: O-parity formula (animatable)",
    "单独一条棱被翻": "A single edge is flipped",

    # ---- 5 阶 ----
    "完成六面中心块（3×3，有固定中心）": "Solve the six centers (3×3, with a fixed center)",
    "五阶每面中心是 3×3=9 个色块，中间那格是固定的中心点，锚定了配色"
    "（上黄下白 / 前蓝后绿 / 左橙右红）。因此五阶要先把各面的 9 块中心按"
    "颜色归面；靠内两层宽转（小写 l/r/u/d/f/b）一次可带动两条中线上的"
    "中心块，这是四阶（每面 2×2 四块、无固定中心）所没有的。":
        "Each 5×5 center is 3×3 = 9 facelets; the middle one is a fixed center "
        "that anchors the color scheme (yellow up/white down, blue front/green "
        "back, orange left/red right). So first sort each face's 9 center pieces "
        "by color; a wide turn of the inner two layers (lowercase l/r/u/d/f/b) "
        "moves center pieces on two midlines at once—something the 4×4 "
        "(2×2 = 4 pieces per face, no fixed center) cannot do.",
    "完成 12 对三块棱（中棱 + 2 翼）":
        "Pair all 12 three-piece edges (mid-edge + 2 wings)",
    "五阶每条棱由 1 个中棱 + 2 块翼棱组成（共 3 块），四阶每条棱只有 2 块翼棱。"
    "所以五阶配棱要多拼中棱：先用宽层把中棱与两翼错开对齐，再做一次原地翻棱"
    "把翼翻正，最后宽层返回——把三块收成一条逻辑棱。":
        "A 5×5 edge has 1 mid-edge + 2 wings (3 pieces), while a 4×4 edge has "
        "only 2 wings. So 5×5 pairing must also handle the mid-edge: use a wide "
        "turn to offset and align the mid-edge with the two wings, do one "
        "in-place flip to turn the wings over, then wide-turn back—collecting "
        "the three pieces into one logical edge.",
    "当作三阶完成（与四阶一致）": "Finish as a 3×3 (same as 4×4)",
    "中心与 12 条三块棱都配对后，五阶就等效一个 3×3，直接用三阶复原公式"
    "完成；此阶段的 O 特 / P 特公式也与四阶完全相同。这里放一个示意案例。":
        "Once the centers and the 12 three-piece edges are paired, the 5×5 is "
        "equivalent to a 3×3; finish with 3×3 algorithms. The O-parity/P-parity "
        "formulas at this stage are identical to the 4×4. One demo case is shown "
        "here.",
    "图501 转正中心/中线块": "Fig.501 Bring center/midline pieces into place",
    "公式：Lw U Lw'（即 l U l'）": "Formula: Lw U Lw' (i.e. l U l')",
    "左侧宽层带中心块上来": "The left wide layer brings center pieces up",
    "图502 中心块组循环": "Fig.502 3-cycle of center pieces",
    "三次 Lw' U2 Lw 让中心块三循环": "Three times Lw' U2 Lw cycles the center pieces",
    "把 3×3 中心块按色归面": "Sort the 3×3 center pieces by color",
    "图503 中心在左右侧": "Fig.503 Center on the left/right",
    "公式：Rw U' Rw'（即 r U' r'）": "Formula: Rw U' Rw' (i.e. r U' r')",
    "右侧宽层回带中心块": "The right wide layer brings center pieces back",
    "图511 翻正棱块朝向": "Fig.511 Fix the edge orientation",
    "把翼翻到与中棱同向（关键）": "Flip the wings to match the mid-edge (key step)",
    "图513 拼一条三块棱": "Fig.513 Pair one three-piece edge",
    "Uw'（R U R' F R' F' R）Uw": "Uw' (R U R' F R' F' R) Uw",
    "宽层错开 → 翻棱 → 返回": "Wide-turn offset → flip → return",
    "图515 中棱先归位": "Fig.515 Place the mid-edge first",
    "先放中棱再配两翼": "Place the mid-edge, then pair the two wings",
    "五阶多出的中棱步骤": "The extra mid-edge step unique to 5×5",
}


_JA = {
    # ---- 2 阶 ----
    "还原第一层（底层角块）": "1層目を揃える（下層コーナー）",
    "2 阶只有 8 个角块。先选定一面为白底，把白角块归位并使侧面颜色与"
    "相邻四个侧面颜色一致，即完成第一层。先把白角转到其正确位置上方，"
    "再按下述公式插入。":
        "2×2はコーナーが8つだけ。白を底面に決め、白コーナーを正しい位置に"
        "戻し、側面の色を隣り合う4面と揃えれば1層目完成。白コーナーを"
        "定位置の真上へ運び、下の式で入れます。",
    "顶面翻色（OLL）": "上面の向きを揃える（OLL）",
    "第一层完成后，把顶面 4 个角块翻成黄色（或所选顶色）。2 阶无棱块，"
    "只需处理角块朝向；学会小鱼公式即可应对所有情况。":
        "1層目完成後、上面の4コーナーを黄（または選んだ上面色）にします。"
        "2×2はエッジがなくコーナーの向きだけを扱えばよく、スーネの式で"
        "全パターンに対応できます。",
    "顶角归位（PLL）": "上面コーナーの位置合わせ（PLL）",
    "顶面全黄后，只需调整四个角块的侧面颜色，使其与所在面一致，即完成还原。"
    "用一个交换相邻两角的公式即可。":
        "上面が全て黄になったら、4コーナーの側面の色を揃えるだけ。"
        "隣り合う2コーナーを交換する式1つで完了します。",
    "2-1 白面朝右": "2-1 白が右向き",
    "公式 2-1：(R U R')": "式 2-1：(R U R')",
    "白色朝右，先转右层": "白が右向き。まず右層を回す",
    "2-2 白面朝前": "2-2 白が前向き",
    "公式 2-2：(F'U'F)": "式 2-2：(F'U'F)",
    "白色朝前，先转前层": "白が前向き。まず前層を回す",
    "2-3 白面在顶层": "2-3 白が上層にある",
    "公式 2-3：(R U R') U' (R U R')": "式 2-3：(R U R') U' (R U R')",
    "白角在顶层侧面先替换下来": "上層側面の白コーナーを先に降ろす",
    "3-1 小鱼（顺）": "3-1 スーネ（時計回り）",
    "公式 3-1：R U R' U R U2 R'": "式 3-1：R U R' U R U2 R'",
    "顺时针小鱼，翻角成全黄": "時計回りのスーネ。コーナーを全て黄に",
    "3-2 小鱼（逆）": "3-2 アンチスーネ（反時計回り）",
    "公式 3-2：R U2 R' U' R U' R'": "式 3-2：R U2 R' U' R U' R'",
    "逆时针小鱼": "反時計回りのスーネ",
    "3-3 顶面一点黄": "3-3 上面に黄が1つ",
    "小鱼 ×2": "スーネ ×2",
    "顶面只有一个黄角时连做两次小鱼": "上面に黄コーナーが1つならスーネを2回",
    "4-1 交换角块": "4-1 コーナーを交換",
    "公式 4-1：R' F R' B2 R F' R' B2 R2": "式 4-1：R' F R' B2 R F' R' B2 R2",
    "只调整顶角位置": "上面コーナーの位置だけ調整",

    # ---- 3 阶 ----
    "底棱归位（底部架十字）": "底エッジを揃える（底面クロス）",
    "以白为底。把四个白棱转到顶面与黄中心同面，转动上层使侧面颜色"
    "对到对应中心（蓝/红/橙/绿），再转 180° 放到底部。注意相对顺序："
    "白红在白蓝右、白橙在白蓝左、白绿在白蓝对面。":
        "白を底に。4つの白エッジを上面で黄センターと同じ面へ持って行き、"
        "上層を回して側面の色を対応するセンター（青/赤/橙/緑）に合わせ、"
        "180°回して底へ。順序に注意：白赤は白青の右、白橙は白青の左、"
        "白緑は白青の反対。",
    "底角归位（第一层角块）": "底コーナーを揃える（1層目のコーナー）",
    "目标角块先调至其正确位置的正上方，看白色朝何方判断是哪种情况"
    "（2-1~2-5）。不必死记，理解「把白角与底棱连成 1×1×2 整体再归位」。":
        "目標コーナーを定位置の真上へ運び、白がどの向きかで場合分け"
        "（2-1〜2-5）。丸暗記は不要で、「白コーナーと底エッジを"
        "1×1×2のブロックとしてまとめて入れる」と理解しましょう。",
    "中棱归位（中层棱块）": "中エッジを揃える（中層のエッジ）",
    "中层四个棱块复原。3-1/3-2 是两种常见情形；若棱块在中间层但方向反"
    "（图 301），先用 3-1 或 3-2 把它换到顶层，再插回正确位置。":
        "中層の4エッジを揃えます。3-1/3-2が代表的な2ケース。中層にあるが"
        "向きが逆のエッジ（図301）は、まず3-1か3-2で上層へ出し、"
        "正しい位置に入れ直します。",
    "顶棱面位（顶层十字）": "上エッジの向き（上面クロス）",
    "只用公式 4 即可完成顶部十字。按情况用 1 次（4-1 一字）、2 次（4-2）"
    "或 3 次（4-3）。做前注意上层位置，把已面位的棱转到左上/右上。":
        "式4だけで上面クロスが作れます。状況に応じて1回（4-1 一文字）、"
        "2回（4-2）、3回（4-3）。各回の前に上層を回し、向きが合った"
        "エッジを左上/右上へ。",
    "顶角面位（顶层角块翻色）": "上コーナーの向き（上面コーナー反転）",
    "顶层架十字后，把四角翻成顶面全黄。若已有一角黄面在前右，看是 5-1"
    "或 5-2；其它情况先把一个角面位，再照图示处理（如 503：5-2→U2→5-1）。":
        "上面クロス後、4コーナーを上面が全て黄になるまで反転。前右に黄の"
        "コーナーが1つあれば5-1か5-2。それ以外はまず1コーナーを揃え、"
        "図に従います（例 503：5-2→U2→5-1）。",
    "顶角归位（顶层角块位置）": "上コーナーの位置合わせ",
    "让四个角块另外两面的颜色与所在面的中心块一致，即完成角块归位。":
        "4コーナーの上面以外の2色を隣接センターの色に合わせれば、"
        "コーナーの位置合わせ完了。",
    "顶棱归位（顶层棱块位置）": "上エッジの位置合わせ",
    "让四个棱块另一面的颜色与所在面的中心块一致，即全部还原。":
        "4エッジのもう一方の色を各面のセンターに合わせれば、全体が揃います。",
    "白蓝棱块（顶面已对位）": "白青エッジ（上面で位置合わせ済み）",
    "公式 1-1：F2": "式 1-1：F2",
    "顶层对位后 180° 放到底部": "上面で合わせたら180°回して底へ",
    "白红棱块（从右层下来）": "白赤エッジ（右層から降ろす）",
    "公式 1-2：R2": "式 1-2：R2",
    "白红需放白蓝右边": "白赤は白青の右へ",
    "棱块先到顶面再对位": "エッジを先に上面へ上げてから合わせる",
    "公式 1-3：F R U R' U' F'": "式 1-3：F R U R' U' F'",
    "先上顶面，再对侧色放下": "先に上面へ上げ、側面色を合わせて降ろす",
    "2-1 白色朝右": "2-1 白が右向き",
    "白色朝右，第一步转右层": "白が右向き。最初に右層を回す",
    "2-2 白色朝前": "2-2 白が前向き",
    "白色朝前，第一步转前层": "白が前向き。最初に前層を回す",
    "2-3 用两次 2-1": "2-3 2-1を2回",
    "用两次 2-1：(R U R') U' (R U R')": "2-1を2回：(R U R') U' (R U R')",
    "角块在顶层侧面": "コーナーが上層側面",
    "2-4 用两次 2-2": "2-4 2-2を2回",
    "用两次 2-2：(F'U'F) U (F'U'F)": "2-2を2回：(F'U'F) U (F'U'F)",
    "角块在顶层另一侧": "コーナーが上層の反対側",
    "2-5 用三次 2-1": "2-5 2-1を3回",
    "用三次 2-1：(R U R') U' (R U R') U' (R U R')":
        "2-1を3回：(R U R') U' (R U R') U' (R U R')",
    "角块方向特殊": "コーナーの向きが特殊",
    "3-1 棱块需向右": "3-1 エッジを右へ",
    "公式 3-1：U R U' R' U' F' U F": "式 3-1：U R U' R' U' F' U F",
    "先右后前，插向右前": "右→前の順に、右前へ挿入",
    "3-2 棱块需向左": "3-2 エッジを左へ",
    "公式 3-2：U' F' U F U R U' R'": "式 3-2：U' F' U F U R U' R'",
    "先后右，插向左前": "前→右の順に、左前へ挿入",
    "图 301 棱块方向反": "図301 エッジの向きが逆",
    "先做 3-1 换到顶层": "3-1で上層へ出す",
    "把反了的棱换到顶层再插回": "逆のエッジを上層へ出して入れ直す",
    "4-1 一字": "4-1 一文字",
    "公式 4：F R U R' U' F'（用 1 次）": "式4：F R U R' U' F'（1回）",
    "顶面黄成一字": "上面の黄が一文字",
    "4-2 拐角": "4-2 L字",
    "公式 4 用 2 次（中间转 U）": "式4を2回（間にU）",
    "顶面黄成拐角": "上面の黄がL字",
    "4-3 点": "4-3 点",
    "公式 4 用 3 次（中间转 U）": "式4を3回（間にU）",
    "顶面只有一个黄点": "上面に黄の点が1つ",
    "5-1 小鱼（顺）": "5-1 スーネ（時計回り）",
    "公式 5-1：R U R' U R U2 R'": "式 5-1：R U R' U R U2 R'",
    "顺时针小鱼，翻角成全黄": "時計回りのスーネ。コーナーを全て黄に",
    "5-2 小鱼（逆）": "5-2 アンチスーネ（反時計回り）",
    "公式 5-2：R U2 R' U' R U' R'": "式 5-2：R U2 R' U' R U' R'",
    "图 503 特殊": "図503 特殊",
    "先反小鱼，转上层再正小鱼": "アンチスーネ→U→スーネ",
    "6-1 交换角块": "6-1 コーナーを交換",
    "公式 6-1：R' F R' B2 R F' R' B2 R2": "式 6-1：R' F R' B2 R F' R' B2 R2",
    "只调整角块位置": "コーナーの位置だけ調整",
    "7-1 三棱循环": "7-1 3エッジ循環",
    "公式 7-1：F2 U L R' F2 L' R U F2": "式 7-1：F2 U L R' F2 L' R U F2",
    "完成还原": "完成",

    # ---- 4 阶 ----
    "完成六面中心块": "6面のセンターを揃える",
    "先把黄、白两面中心拼好（保持不破坏），再把黄白放左右两侧，"
    "用 Rw/Lw 系列公式完成蓝红绿橙四面。注意配色：上黄下白、前蓝后绿、"
    "左橙右红。":
        "まず黄と白のセンターを揃え（崩さないよう保持）、黄白を左右に置き、"
        "Rw/Lw系の式で青赤緑橙の4面を完成。配色に注意：上黄下白、"
        "前青後緑、左橙右赤。",
    "完成 12 对棱块": "12組のエッジを揃える",
    "只需掌握一个拼棱公式：先让一对棱同在上或同在下，上两层往右错开，"
    "做一次原地翻棱公式，再返回。左右两侧一上一下时先翻棱再拼棱。":
        "ペアリングの式を1つ覚えれば十分：1組のエッジを上同士または下同士に"
        "し、上2層を右へずらし、その場反転の式を1回行い、戻します。"
        "左右が上下一つずつのときは先に反転してからペアリング。",
    "当作三阶完成": "3×3として完成",
    "中心与棱都配对后，4 阶等效 3 阶，直接用三阶复原公式完成。":
        "センターとエッジが揃えば4×4は3×3相当。3×3の公式で完成させます。",
    "特殊情况处理": "特殊ケースの処理",
    "降到三阶后可能出现 P 特（对棱换）与 O 特（单棱翻），用对应公式修复。":
        "3×3に縮約後、Pパリティ（対エッジ交換）やOパリティ（単エッジ反転）が"
        "現れることがあり、対応する式で修復します。",
    "图101 中心在右上": "図101 センターが右上",
    "公式：Rw U Rw'（即 r U r'）": "式：Rw U Rw'（すなわち r U r'）",
    "右侧用右手转上来，再转到左侧": "右手で右を上げ、左へ回す",
    "图102 中心在左上": "図102 センターが左上",
    "公式：Rw U' Rw'（即 r U' r'）": "式：Rw U' Rw'（すなわち r U' r'）",
    "右手转上来，再转回左侧": "右手で上げ、左へ戻す",
    "图103 左侧中心": "図103 左側のセンター",
    "公式：Lw' U Lw（即 l' U l）": "式：Lw' U Lw（すなわち l' U l）",
    "左侧用左手转上来": "左手で左を上げる",
    "图104 左侧中心": "図104 左側のセンター",
    "公式：Lw' U' Lw（即 l' U' l）": "式：Lw' U' Lw（すなわち l' U' l）",
    "左手转上来再转回": "左手で上げて戻す",
    "图105 同侧在右": "図105 同じ側が右",
    "公式：Rw U2 Rw'（即 r U2 r'）": "式：Rw U2 Rw'（すなわち r U2 r'）",
    "同侧在右，右侧先上": "同側が右。まず右を上げる",
    "图106 同侧在左": "図106 同じ側が左",
    "公式：Lw' U2 Lw（即 l' U2 l）": "式：Lw' U2 Lw（すなわち l' U2 l）",
    "同侧在左，左侧先上": "同側が左。まず左を上げる",
    "图201 原地翻棱公式": "図201 その場反転の式",
    "原地翻棱：R U R' F R' F' R": "その場反転：R U R' F R' F' R",
    "右侧棱块原地翻转（练 100 遍）": "右エッジをその場で反転（100回練習）",
    "图203 拼棱公式": "図203 ペアリングの式",
    "拼棱：Uw'（R U R' F R' F' R）Uw": "ペアリング：Uw'（R U R' F R' F' R）Uw",
    "上两层错开 → 翻棱 → 返回": "上2層をずらす → 反転 → 戻す",
    "图205 一上一下": "図205 上下一つずつ",
    "先翻棱再拼棱": "先に反転してからペアリング",
    "左一上一下：先翻棱再对棱": "左で上下一つずつ：反転してからペアリング",
    "三阶小鱼公式": "3×3スーネの式",
    "三阶小鱼：R U R' U R U2 R'": "3×3スーネ：R U R' U R U2 R'",
    "当三阶用七步法还原": "3×3として七手順法で揃える",
    "图401 对棱换（P特）": "図401 対エッジ交換（Pパリティ）",
    "对棱换：Uw2（MR2 U2）2 MR2 Uw2": "対エッジ交換：Uw2（MR2 U2）2 MR2 Uw2",
    "P特公式": "Pパリティの式",
    "图402 单棱翻（O特）": "図402 単エッジ反転（Oパリティ）",
    "单棱翻：O 特公式（可动画版）": "単エッジ反転：Oパリティの式（アニメ可）",
    "单独一条棱被翻": "1本のエッジだけが反転",

    # ---- 5 阶 ----
    "完成六面中心块（3×3，有固定中心）":
        "6面のセンターを揃える（3×3・固定センターあり）",
    "五阶每面中心是 3×3=9 个色块，中间那格是固定的中心点，锚定了配色"
    "（上黄下白 / 前蓝后绿 / 左橙右红）。因此五阶要先把各面的 9 块中心按"
    "颜色归面；靠内两层宽转（小写 l/r/u/d/f/b）一次可带动两条中线上的"
    "中心块，这是四阶（每面 2×2 四块、无固定中心）所没有的。":
        "5×5の各面センターは3×3＝9ピースで、中央は配色を決める固定センター"
        "（上黄下白/前青後緑/左橙右赤）。まず各面の9センターを色ごとに"
        "揃えます。内側2層のワイド回転（小文字 l/r/u/d/f/b）は2本の中線上の"
        "センターを同時に動かせ、これは4×4（各面2×2の4ピース、固定センター"
        "なし）にはない違いです。",
    "完成 12 对三块棱（中棱 + 2 翼）":
        "12組の3ピースエッジを揃える（中エッジ＋2ウィング）",
    "五阶每条棱由 1 个中棱 + 2 块翼棱组成（共 3 块），四阶每条棱只有 2 块翼棱。"
    "所以五阶配棱要多拼中棱：先用宽层把中棱与两翼错开对齐，再做一次原地翻棱"
    "把翼翻正，最后宽层返回——把三块收成一条逻辑棱。":
        "5×5のエッジは中エッジ1＋ウィング2の3ピース、4×4はウィング2のみ。"
        "そのため5×5のペアリングは中エッジの処理が加わります：ワイド回転で"
        "中エッジと2ウィングをずらして合わせ、その場反転を1回してウィングを"
        "正し、最後にワイド回転で戻し、3ピースを1本の論理エッジにまとめます。",
    "当作三阶完成（与四阶一致）": "3×3として完成（4×4と同じ）",
    "中心与 12 条三块棱都配对后，五阶就等效一个 3×3，直接用三阶复原公式"
    "完成；此阶段的 O 特 / P 特公式也与四阶完全相同。这里放一个示意案例。":
        "センターと12本の3ピースエッジが揃えば5×5は3×3相当。3×3の公式で"
        "完成します。この段階のOパリティ/Pパリティの式も4×4と完全に同じ"
        "です。ここでは1例だけ示します。",
    "图501 转正中心/中线块": "図501 センター/中線ピースを正す",
    "公式：Lw U Lw'（即 l U l'）": "式：Lw U Lw'（すなわち l U l'）",
    "左侧宽层带中心块上来": "左ワイド層でセンターピースを上げる",
    "图502 中心块组循环": "図502 センターピースの3循環",
    "三次 Lw' U2 Lw 让中心块三循环": "Lw' U2 Lw を3回でセンターが3循環",
    "把 3×3 中心块按色归面": "3×3センターを色ごとに揃える",
    "图503 中心在左右侧": "図503 センターが左右側",
    "公式：Rw U' Rw'（即 r U' r'）": "式：Rw U' Rw'（すなわち r U' r'）",
    "右侧宽层回带中心块": "右ワイド層でセンターピースを戻す",
    "图511 翻正棱块朝向": "図511 エッジの向きを正す",
    "把翼翻到与中棱同向（关键）": "ウィングを中エッジと同じ向きに（重要）",
    "图513 拼一条三块棱": "図513 3ピースエッジを1本作る",
    "Uw'（R U R' F R' F' R）Uw": "Uw'（R U R' F R' F' R）Uw",
    "宽层错开 → 翻棱 → 返回": "ワイドでずらす → 反転 → 戻す",
    "图515 中棱先归位": "図515 中エッジを先に帰位",
    "先放中棱再配两翼": "中エッジを先に置き、2ウィングをペアリング",
    "五阶多出的中棱步骤": "5×5だけの中エッジ手順",
}


_TABLES = {"en": _EN, "ja": _JA}


def translate(text, lang):
    """把案例中文原文翻译为目标语言；未收录或非中文时原样返回。"""
    if not isinstance(text, str):
        return text
    table = _TABLES.get(lang)
    if not table:
        return text
    return table.get(text, text)
