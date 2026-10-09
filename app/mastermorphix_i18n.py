"""Text for Mastermorphix input; kept separate from the ordinary cube guide."""

ZH = {
    "home.card.morphix.title": "三阶粽子魔方",
    "home.card.n.title": "N 阶魔方",
    "morphix.title": "粽子魔方",
    "morphix.demo": "教学演示",
    "demo.mode.menu.mastermorphix": "三阶粽子魔方 · 演示目录",
    "demo.mode.title.mastermorphix": "粽子魔方 · 教学演示",
    "morphix.reference": "参考拿法：前轴 F 色对 {front} · 上轴 U 色对 {up}",
    "morphix.group.center": "双色中心",
    "morphix.group.corner": "尖角 / 小三角",
    "morphix.group.edge": "单色梯形",
    "morphix.slot": "{kind}  {i}/{total} · {pos}",
    "morphix.progress": "已录入 {done}/26 块",
    "morphix.hint": "点选块；左右箭头切换视角，中间箭头调朝向。灰色未录入，露出的切面自动沿用邻近颜色。",
    "morphix.rotate_hint": "左右箭头切换视角，中间旋转箭头调整块的朝向。青框为当前块，露出的切面自动沿用邻近颜色。",
    "morphix.triangle_hint": "单色小三角无需调整朝向；左右箭头切换视角。青框为当前块，露出的切面自动沿用邻近颜色。",
    "morphix.center_hint": "双色中心已按初始状态预填，请对照实物调整朝向。左右箭头切视角，中间箭头旋转中心。",
    "morphix.color_slot": "颜色 {i}",
    "morphix.restore_preset": "恢复预设",
    "morphix.color_hint": "按四面展开图的 1、2、3、4 选色；青框为当前面，选择已用颜色会交换色位。",
    "morphix.palette": "选择四种颜色",
    "morphix.palette_hint": "先取消不需要的颜色，再按顺序选满四色。点下面的编号色块可自定义颜色。\n应用后会清空当前录入；颜色顺序决定参考拿法。",
    "morphix.custom_color": "自定义颜色",
    "morphix.apply_palette": "应用四色并重新录入",
    "morphix.clear_confirm": "清空录入，并将六个双色中心恢复为初始朝向？",
    "morphix.sample": "查看一组变形打乱示例",
    "morphix.random_loaded": "已生成 {k} 步随机打乱，26 块全部录入，可直接求解；撤销可恢复之前的录入。",
    "morphix.valid": "块的位置、朝向和双色中心已通过校验，可以开始求解。",
    "morphix.error.incomplete": "请录入全部 26 块：6 个双色中心、8 个角块、12 个单色梯形。",
    "morphix.error.duplicate": "有重复或遗漏的角块，请检查三色尖角和单色小三角。",
    "morphix.error.centers": "请按参考拿法匹配六个双色中心；也可以调整四色顺序。",
    "morphix.error.center_parity": "中心朝向与角块位置不一致，请检查双色中心和尖角的录入。",
    "morphix.error.corner_twist": "三色尖角朝向不匹配，请检查颜色的排列方向。",
    "morphix.error.invalid": "块的数量或朝向无法组成可还原状态，请检查梯形的颜色和朝向。",
    "morphix.solving.pieces": "还原尖角、三角和梯形块…",
    "morphix.solving.centers": "校正双色中心，恢复外形…",
    "morphix.solving.optimizing": "比较更短的完整还原方案…",
    "morphix.solving.optimized": "角棱与双色中心的精简还原方案",
    "morphix.help": (
        "教学演示\n顶部的书本图标打开演示目录，按阶段选择案例。演示页左箭头撤回一个动作，"
        "右箭头执行一个动作；播放自动继续，起点按钮从头开始，环形箭头重置视角。"
        "演示使用当前四色配色，不改动录入。\n\n"
        "先辨认转轴\n粽子有四个外表颜色面，但仍有六个转轴。U/D 是上/下轴，"
        "F/B 是前/后轴，R/L 是右/左轴；不是四面金字塔的转法。\n\n"
        "参考拿法\n先选好四种颜色，并按彩色示意图找到前轴 F 和上轴 U 的双色中心。"
        "新建或清空时，六个双色中心会按初始状态预填，方便定位；请按实物调整各中心朝向。"
        "六个双色中心的位置固定，只有朝向会变化。若实物其余轴的色对与示意图不同，"
        "点击顶部色块调整四色顺序。录入过程中保持同一拿法，不要随意转动实物的层。\n\n"
        "按块录入\n点击模型中的块，自动切换对应的输入选项，镜头保持当前视角。"
        "需要录入 6 个双色中心、8 个角块、12 个单色梯形。"
        "角块包含 4 个三色尖角和 4 个单色小三角，它们可以交换位置。"
        "点击 3D 预览中的块选择位置。左右箭头带动画切换观察视角，不会改动录入。"
        "不能直接拖动改变视角；灰色表示尚未确认。\n\n"
        "选择外形与朝向\n点下方形状卡片确认这块的颜色与类型；中间的弯箭头旋转这块的朝向。"
        "双色中心的四张卡片从左到右每次顺时针旋转 90°，中间旋转按钮也按此顺序切换。"
        "梯形有 2 种朝向，三色尖角有 3 种。用左右箭头检查另一侧。"
        "小三角的内部朝向、同色梯形的内部编号会自动匹配，无需猜普通三阶贴纸颜色。\n\n"
        "底部图标\n交叉箭头：随机生成一颗打乱、变形的魔方，自动录入全部 26 块，可直接求解；"
        "垃圾桶：清空；回弯箭头：撤销上次录入或恢复随机打乱前的录入；勾：检查完整性和可还原性；"
        "播放三角：求解并进入逐步还原。还原包含双色中心的校正，兼顾颜色和形状。\n\n"
        "配色\n直接点击顶部编号色块，用选色器选色。四面展开图的 1、2、3、4 对应顶部色位，"
        "图中青框标出当前改色的面，选色时该面会同步预览。选择已用颜色会交换两个色位。"
        "改色会保存配色并保留已录入的块、中心朝向和当前视角。"
        "改色窗口的“恢复预设”可恢复默认红、黄、蓝、绿四色及其顺序，也会保留录入。"
        "这是一套便于辨认块的几何示意模型，曲面弧度和实体品牌可能略有不同。"
    ),
}

EN = {
    "home.card.morphix.title": "Mastermorphix",
    "home.card.n.title": "N×N Cube",
    "morphix.title": "Mastermorphix",
    "morphix.demo": "Teaching demos",
    "demo.mode.menu.mastermorphix": "Mastermorphix · Demo catalog",
    "demo.mode.title.mastermorphix": "Mastermorphix · Teaching demos",
    "morphix.reference": "Hold: F center colors {front} · U center colors {up}",
    "morphix.group.center": "Two-color centers",
    "morphix.group.corner": "Tips / triangles",
    "morphix.group.edge": "Single-color wedges",
    "morphix.slot": "{kind}  {i}/{total} · {pos}",
    "morphix.progress": "{done}/26 pieces entered",
    "morphix.hint": "Tap a piece. Side arrows change the view; center arrow rotates the piece. Gray: unconfirmed; exposed cuts inherit nearby colors.",
    "morphix.rotate_hint": "Side arrows change the view; center arrow rotates the piece. Cyan: selected; exposed cuts inherit nearby colors.",
    "morphix.triangle_hint": "Single-color triangles need no orientation adjustment. Use side arrows to change the view. Exposed cuts inherit nearby colors.",
    "morphix.center_hint": "Centers start with preset colors and orientations. Match the real puzzle; side arrows change the view, center arrow rotates the center.",
    "morphix.color_slot": "Color {i}",
    "morphix.restore_preset": "Restore defaults",
    "morphix.color_hint": "Match colors to faces 1–4 in the net. Cyan outlines the current face; existing colors swap slots.",
    "morphix.palette": "Choose four colors",
    "morphix.palette_hint": "Deselect unwanted colors, then select four in order. Tap a numbered swatch for a custom color.\nApplying colors clears the current input and sets the reference orientation.",
    "morphix.custom_color": "Custom color",
    "morphix.apply_palette": "Apply colors and start new input",
    "morphix.clear_confirm": "Clear input and restore the six preset centers?",
    "morphix.sample": "Load a scrambled shape example",
    "morphix.random_loaded": "Loaded a {k}-move scramble with all 26 pieces. Ready to solve; undo restores the previous input.",
    "morphix.valid": "Pieces and center orientations are valid. Ready to solve.",
    "morphix.error.incomplete": "Enter all 26 pieces: 6 centers, 8 corners and 12 wedges.",
    "morphix.error.duplicate": "A corner is repeated or missing. Check tips and small triangles.",
    "morphix.error.centers": "Match the centers to the reference axes, or adjust the color order.",
    "morphix.error.center_parity": "Center orientations and corner positions disagree. Check your input.",
    "morphix.error.corner_twist": "Check the color orientation of the three-color tips.",
    "morphix.error.invalid": "Piece counts or wedge orientations cannot form a solvable state.",
    "morphix.solving.pieces": "Restoring tips, triangles and wedges…",
    "morphix.solving.centers": "Correcting centers and restoring the shape…",
    "morphix.solving.optimizing": "Comparing shorter complete solutions…",
    "morphix.solving.optimized": "Compacted piece and center solution",
    "morphix.help": (
        "Teaching demos\nThe book icon opens the case catalog. Left undoes one move; right performs one move. "
        "Play continues automatically, Start restarts the case, and the circular arrow resets the view. "
        "Demos use your four colors and preserve input.\n\n"
        "Reference orientation\nThe four-color tetrahedron has six 3x3 turn axes: U/D, F/B and R/L. "
        "New input or clearing presets all six centers as landmarks. Adjust their orientations to match the real puzzle. "
        "Match the F and U center color pairs to the reference preview. If other pairs differ, "
        "adjust the color selection order. Keep the same physical hold during input.\n\n"
        "Piece input\nEnter 6 two-color centers, 8 corners (4 three-color tips and 4 small triangles), "
        "and 12 single-color wedges. Tap a piece in 3D to switch input options while keeping the camera fixed. "
        "The side arrows animate view changes without changing input. Dragging cannot change the view. "
        "Gray means unconfirmed. Choose a shape card and use the curved arrow to match orientation. "
        "Center cards run left to right in clockwise 90-degree steps, matching the center arrow. "
        "Wedges have 2 orientations, tips 3. Use side arrows to inspect another side. "
        "Invisible triangle twists and identical wedge identities are assigned automatically.\n\n"
        "Controls\nShuffle generates a scrambled, shape-changed puzzle and fills all 26 pieces, ready to solve. "
        "Trash clears input; undo restores the previous input; check validates; play solves and opens "
        "step playback, including center orientation correction. Tap a top swatch to open the color picker. "
        "The tetrahedron net numbers 1–4 match the top swatches. Cyan outlines the current face; its color previews as you choose. "
        "Choosing an existing color swaps slots. Color edits are saved and preserve the entered pieces, center orientations and view. "
        "Restore defaults in the color editor restores red, yellow, blue and green in that order while preserving input. "
        "The geometry is schematic; curvature may differ from your brand."
    ),
}

JA = dict(EN, **{
    "home.card.morphix.title": "マスターモルフィックス",
    "home.card.n.title": "N×N キューブ",
    "morphix.title": "マスターモルフィックス",
    "morphix.demo": "解説デモ",
    "demo.mode.menu.mastermorphix": "マスターモルフィックス · デモ一覧",
    "demo.mode.title.mastermorphix": "マスターモルフィックス · 解説デモ",
    "morphix.reference": "持ち方：F の色 {front} · U の色 {up}",
    "morphix.group.center": "2色のセンター",
    "morphix.group.corner": "頂点 / 小三角",
    "morphix.group.edge": "単色の台形",
    "morphix.progress": "入力済み {done}/26 ピース",
    "morphix.palette": "4色を選択",
    "morphix.custom_color": "カスタムカラー",
    "morphix.apply_palette": "色を適用して再入力",
    "morphix.hint": "ピースを選択。左右の矢印は視点、中央の矢印は向きを変更します。灰色は未入力、露出した切断面は隣接する色を引き継ぎます。",
    "morphix.rotate_hint": "左右の矢印で視点、中央の矢印で向きを変更します。水色の枠は選択中、露出した切断面は隣接する色を引き継ぎます。",
    "morphix.triangle_hint": "単色の小三角は向きの調整が不要です。左右の矢印で視点を変更します。露出した切断面は隣接する色を引き継ぎます。",
    "morphix.center_hint": "センターは初期状態で入力済みです。実物に合わせて向きを調整してください。左右の矢印は視点、中央はセンターを回転します。",
    "morphix.color_slot": "色 {i}",
    "morphix.restore_preset": "初期配色に戻す",
    "morphix.color_hint": "展開図の1～4に合わせて色を選択。水色の枠は現在の面です。使用中の色は位置を交換します。",
    "morphix.palette_hint": "不要な色を解除し、順番に4色を選択します。番号付きの色を押すとカスタムカラーを選べます。\n適用すると入力がクリアされ、基準の持ち方が変わります。",
    "morphix.clear_confirm": "入力をクリアし、6個のセンターを初期状態に戻しますか？",
    "morphix.sample": "変形したスクランブル例を読み込む",
    "morphix.random_loaded": "{k}手のスクランブルを生成し、26ピースを入力しました。復元できます。取り消しで以前の入力に戻せます。",
    "morphix.valid": "位置と向きが正しい状態です。復元を開始できます。",
    "morphix.error.incomplete": "26ピースすべてを入力してください：センター6、コーナー8、台形12。",
    "morphix.error.duplicate": "コーナーに重複または不足があります。頂点と小三角を確認してください。",
    "morphix.error.centers": "センターの色を基準の軸に合わせるか、4色の選択順を調整してください。",
    "morphix.error.center_parity": "センターの向きとコーナーの位置が一致していません。入力を確認してください。",
    "morphix.error.corner_twist": "3色の頂点の色の向きを確認してください。",
    "morphix.error.invalid": "ピース数または台形の向きが復元可能な状態になっていません。",
    "morphix.help": (
        "解説デモ\n本のアイコンで例の一覧を開きます。左矢印は1動作戻し、右矢印は1動作進めます。"
        "再生は自動で続行、開始は例を最初に戻し、円形矢印は視点を戻します。"
        "選択した4色を使い、入力を保持します。\n\n"
        "基準の持ち方\n色の面は4つですが、回転軸はU/D、F/B、R/Lの6つです。"
        "新規入力、クリア時には6個のセンターが初期状態で入力されます。実物に合わせて向きを調整してください。"
        "FとUの2色センターを参考図に合わせてください。他の色の組が違う場合は、"
        "4色の選択順を変えます。入力中は実物の持ち方を維持してください。\n\n"
        "ピース入力\n2色センター6個、コーナー8個（3色の頂点4個と小三角4個）、"
        "単色の台形12個を入力します。3D上のピースをタップすると入力候補が自動で切り替わり、視点は変わりません。"
        "左右の矢印で視点をアニメーションで切り替えます。入力は変わりません。ドラッグでは視点を変更できません。"
        "灰色は未確認です。形のカードを選び、曲がった矢印で向きを合わせます。"
        "センターの4枚のカードは左から時計回りに90度ずつ回転し、中央の回転ボタンも同じ順序です。"
        "台形は2方向、頂点は3方向です。左右の矢印で裏側を確認できます。"
        "見えない小三角の向きと同色の台形の内部番号は自動で割り当てます。\n\n"
        "操作\n交差する矢印は変形したスクランブルを生成し、26ピースを入力します。すぐに復元できます。"
        "ごみ箱はクリア、戻る矢印は以前の入力に戻す、チェックは検証、再生は復元です。"
        "復元には2色センターの向きの修正も含まれます。上部の色をタップしてカラーピッカーで選べます。"
        "展開図の1～4は上部の色番号に対応し、水色の枠は現在の面です。選ぶ色は図に反映されます。"
        "使用中の色は位置を交換します。配色は保存され、ピース、センターの向き、視点は保持されます。"
        "色の編集画面の初期配色ボタンで赤、黄、青、緑の順に戻せます。入力は保持されます。"
        "表示は模式的な形です。曲面の形状は実物のブランドと異なる場合があります。"
    ),
    "morphix.solving.pieces": "ピースを復元中…",
    "morphix.solving.centers": "センターの向きと形を復元中…",
    "morphix.solving.optimizing": "より短い復元手順を比較中…",
    "morphix.solving.optimized": "ピースとセンターの簡略化された復元手順",
})
MESSAGES = {"zh": ZH, "en": EN, "ja": JA}
