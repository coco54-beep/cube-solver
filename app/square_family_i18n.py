"""SQ model names, direct piece input and mechanism errors."""
ZH = {
    'directory.sq_family':'SQ 系列', 'directory.square0':'SQ-0', 'directory.square2':'SQ-2',
    'directory.super_square1':'Super SQ-1 · 四层',
    'sq.layer_top':'上层 U', 'sq.layer_bottom':'下层 D',
    'sq.layer_inner_top':'内上层 u', 'sq.layer_inner_bottom':'内下层 d',
    'sq.input':'选位置与对应块；锁定视角后可拖动拧层。已录入 {done}/{total}。',
    'sq.centre_0':'中部／半圆中心：正常', 'sq.centre_1':'中部／半圆中心：翻转',
    'sq.error.incomplete':'请补齐全部层的块；空缺位置可在层图中点选。',
    'sq.error.orbit':'Super SQ-1 的内层和外层块不能互换，请检查录入。',
    'sq.error.quarter':'SQ-0 每层以 90° 为一步，请对齐四个连体块。',
    'sq.error.move':'动作与当前 SQ 型号不匹配。',
    'sq.error.generator':'SQ-2 的交换动作表未能正确生成。',
}
EN = {
    'directory.sq_family':'SQ family', 'directory.square0':'SQ-0', 'directory.square2':'SQ-2',
    'directory.super_square1':'Super SQ-1 · Four layers',
    'sq.layer_top':'Top U', 'sq.layer_bottom':'Bottom D',
    'sq.layer_inner_top':'Inner top u', 'sq.layer_inner_bottom':'Inner bottom d',
    'sq.input':'Pick a position and its piece. Lock the view to drag-turn layers. {done}/{total} entered.',
    'sq.centre_0':'Middle / half-centres: normal', 'sq.centre_1':'Middle / half-centres: flipped',
    'sq.error.incomplete':'Complete all layers. Select empty positions in the layer diagram.',
    'sq.error.orbit':'Super SQ-1 inner and outer pieces cannot exchange orbits.',
    'sq.error.quarter':'SQ-0 layers turn in 90° steps. Align the four joined pieces.',
    'sq.error.move':'This move does not match the selected SQ model.',
    'sq.error.generator':'The SQ-2 exchange table could not be generated.',
}
JA = {
    'directory.sq_family':'SQシリーズ', 'directory.square0':'SQ-0', 'directory.square2':'SQ-2',
    'directory.super_square1':'Super SQ-1 · 4層',
    'sq.layer_top':'上層 U', 'sq.layer_bottom':'下層 D',
    'sq.layer_inner_top':'内上層 u', 'sq.layer_inner_bottom':'内下層 d',
    'sq.input':'位置とパーツを選択。視点固定でドラッグ回転。入力 {done}/{total}。',
    'sq.centre_0':'中層／半円中心：通常', 'sq.centre_1':'中層／半円中心：反転',
    'sq.error.incomplete':'全層のパーツを入力してください。空き位置は層の図で選択できます。',
    'sq.error.orbit':'Super SQ-1の内層と外層のパーツは交換できません。',
    'sq.error.quarter':'SQ-0は90°ずつ回転します。4つの連結パーツを合わせてください。',
    'sq.error.move':'この動作は選択中のSQモデルに対応しません。',
    'sq.error.generator':'SQ-2の交換テーブルを生成できませんでした。',
}
MESSAGES = {'zh':ZH,'en':EN,'ja':JA}
