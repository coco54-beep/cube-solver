"""Names for the requested collection; mechanism IDs are language independent."""
from candidate_puzzles import REQUESTED,PENDING

MESSAGES={lang:{'directory.'+e.kind:e.name for e in REQUESTED+PENDING} for lang in ('zh','en','ja')}
MESSAGES['zh'].update({
    'tilted.fixed_core':'中央色面连在固定核心上，不能单独改变核心朝向。请修改标出的中央面姿态；输入已保留。',
    'directory.lanlan_clover_pyraminx':'三叶草金字塔',
    'directory.kairis_star_finder':'Kairis 星寻足球 · 标准120°',
    'directory.vp_clover_dodecahedron':'Clover 十二面体',
    'directory.lanlan_sunflower':'向阳花',
    'directory.lanlan_andromeda':'仙女座',
    'directory.lanlan_butterflower':'蝶恋花',
    'master_clover.deep':'大层',
    'master_clover.shallow':'小层',
    'master_clover.regular_only':'当前双棱花支持常规双层180°状态；变形混转的内部切面尚未核对，输入已保留。',
    'directory.lanlan_hexagram':'六角星金字塔 · 几何模型',
    'directory.megaminx_ball':'五魔球 · D5',
    'directory.aj_curvy_dinominx_4':'AJ 曲线角转 · 四层',
    'aj.error.fixed_centres':'十二个中央色面属于固定核心，请按配色设置检查中央颜色。输入已保留。',
    'aj.error.orbit_parity':'这组棱块的排列不符合角转机构，请检查同一块两侧的颜色。输入已保留。',
    'aj.error.edge_flip':'棱块翻转数量不符合机构约束，请检查两侧颜色。输入已保留。',
    'directory.mf8_bauhinia_minx':'MF8 紫荆花',
    'rex.error.edge_flip':'棱块朝向不符合标准 120° 转动的约束，请检查棱块两侧颜色。输入已保留；混转形状尚不支持。',
    'rex.error.orbit_parity':'这组块的排列不符合标准 120° 转动的约束，请检查块的位置和颜色。输入已保留；混转状态尚不支持。',
    'directory.yeet_ball':'永骏枫叶球',
    'shape.error.corner_twist':'角块的可见朝向不符合还原机构，请检查角块方向。输入已保留。',
    'directory.skewb_rhombic':'四轴斜转十二菱面',
    'directory.rhombic_3':'菱面三阶',
    'directory.rhombic_4':'四阶十二菱面',
    'directory.rhombic_mask_4':'四阶菱边',
    'directory.caneball_4':'四阶八面魔球',
    'directory.jewel_fto':'八轴八面绣球',
    'directory.rua':'十二轴十二菱面 · Rua',
    'directory.helicopter_14':'十二轴十四面体',
    'directory.time_machine':'时间机器 · 数字环',
    'directory.bean_6':'六面旋转魔豆 · 三瓣',
    'directory.bean_10':'十面旋转魔豆 · 五瓣',
    'dial.core':'角块层','dial.ring':'数字环','dial.front':'正面圈','dial.back':'背面圈',
    'dial.number':'数字 {number}','dial.select_number':'选择数字',
    'poly.error.counts_numbers':'颜色或数字的数量不符合此型号，请检查标出的输入。',
    'dial.wing':'翻瓣','dial.rotor':'中央转盘',
    'dial.rotor_front':'正面中央盘','dial.rotor_back':'背面中央盘',
    'dial.twist_hint':'拖动中央旋钮转本面的中央盘，另一面保持；也可选正面／背面中央盘后点转动按钮。',
    'dial.front_side':'正面','dial.back_side':'背面',
    'poly.time_machine_input':'选颜色和数字填扇片，数字自动加一；角块内外两处同步填色。',
    'poly.bean_6_input':'选色后连续点珠，箭头翻面；每圈同色即可，颜色位置不限。',
    'poly.bean_10_input':'选色后连续点珠，箭头翻面；每圈同色即可，颜色位置不限。',
    'mirror_minx.hint':'按实物的高低和形状选择块，圆箭头调整方向，左右箭头逐面观察。每层转 72°。',
    'blanker.hint':'白色外壳的细线为装饰分格，实际按二阶八个角块输入形状和方向。',
    'directory.extended_family':'字母形扩展系列',
    'directory.pentagonal_family':'五边形柱体系列',
    'directory.round_family':'圆柱与球体系列',
    'directory.megaminx':'十二面体系列',
    'directory.fto':'八面体系列',
    'directory.icosahedron':'二十面体系列',
    'directory.bandaged_family':'绑块与连体系列',
    'directory.special':'其他异形',
    'directory.special_hint':'不属于现有系列的独立型号。',
    'directory.minx_order':'{order} 阶五魔方',
    'directory.kilominx_order':'Kilominx · 二阶五魔方',
    'directory.fto_3':'FTO · 三阶八面体',
    'expanded.local_valid':'块和配色检查通过；完整可解性会在求解时核验。',
    'directory.trajber':'Trajber 八面体 · 四阶',
    'expanded.reference_needed':'此型号仍需核对外形与切割结构，暂未开放操作。可提供实物图片或型号页面继续接入。',
    'directory.dogic_i':'Dogic I · 12 色',
    'directory.rubik_cheese':'Rubik Cheese · 两层',
    'directory.dogic_20':'Dogic · 20 色',
    'directory.pentultimate':'Pentultimate · 深切五魔',
    'directory.master_pentultimate':'Master Pentultimate',
    'poly.dogic_i_input':'12 色 Dogic：中央三色小面属于同一块。选色后逐面填色；拧动可选顶角或包含相邻五面的深层。',
    'poly.dogic_20_input':'20 色 Dogic：每个三角面同色。选色后连续点面；顶角与深层分别转动 72°。',
    'poly.siamese_a_input':'A 型共享 1×1×3 连接块。选色后逐面填写；连接块不能被切开转动。',
    'poly.siamese_b_input':'B 型共享 2×1×3 连接块。选色后逐面填写；连接块不能被切开转动。',
    'poly.masterball_input':'八经线、四纬层；每条经线四块同色。纬层转 45°，半球翻转 180°。',
    'poly.rubik_cheese_input':'两层，每层六瓣。顶底各同色、侧面按扇区配色；选色后逐面填写。每层转 60°，半盘翻转 180°。',
    'poly.pyraminx_diamond_input':'六个四色尖块与八个中央三角面；尖块连同相邻四个中央面转动 90°。',
    'poly.cheese_3_input':'三层，每层六瓣。顶底各同色、侧面按扇区配色；选色后逐面填写。每层转 60°，半盘翻转 180°。',
    'container.hint':'按实物选择形状与颜色卡片；圆箭头调整块的朝向，左右箭头逐面观察。',
    'poly.pentagonal_input':'顶底转 72°、侧层翻转 180°。选色后连续填色，左右箭头逐面观察；Professor 的侧面为 5×5 格。',
    'poly.container_input':'选择真实块的形状、颜色和方向；长方体外壳随 Skewb 机构转动。',
})
MESSAGES['en'].update({
    'master_clover.deep':'Large',
    'master_clover.shallow':'Small',
    'master_clover.regular_only':'Master Clover currently supports closed double-layer half-turn states. The internal jumbling cuts are not yet verified. Your input has been kept.',
    'tilted.fixed_core':'The centre panels share a fixed core. Correct the highlighted core pose; your input has been kept.',
    'aj.error.fixed_centres':'The twelve centre panels belong to the fixed core. Check their reference colours. Your input is preserved.',
    'aj.error.orbit_parity':'This edge permutation is incompatible with the corner-turning mechanism. Check both colours of each piece. Your input is preserved.',
    'aj.error.edge_flip':'The edge orientations violate the mechanism constraints. Check both colours. Your input is preserved.',
    'rex.error.edge_flip':'The edge orientations violate the regular 120-degree constraints. Check both colours of the edges. Input is preserved; jumbled shapes are not supported yet.',
    'rex.error.orbit_parity':'This piece permutation violates the regular 120-degree constraints. Check positions and colours. Input is preserved; jumbled states are not supported yet.',
    'shape.error.corner_twist':'The visible corner orientations are incompatible. Check the corners; your input has been kept.',
    'dial.core':'Core','dial.ring':'Number ring','dial.front':'Front loop','dial.back':'Back loop',
    'dial.number':'Number {number}','dial.select_number':'Choose a number',
    'poly.error.counts_numbers':'The colour or number counts do not match this model. Check the highlighted entries.',
    'dial.wing':'Wing flip','dial.rotor':'Central rotor',
    'dial.rotor_front':'Front central rotor','dial.rotor_back':'Back central rotor',
    'dial.twist_hint':'Drag the central knob to turn this side only, or select the front/back rotor and use the turn buttons.',
    'poly.time_machine_input':'Paint ring tiles by colour and number; the number advances. Inner and outer corner surfaces share one colour.',
    'dial.front_side':'Front','dial.back_side':'Back',
    'poly.bean_6_input':'Paint beads; arrows flip sides. Each loop needs one colour; any loop may hold any colour.',
    'poly.bean_10_input':'Paint beads; arrows flip sides. Each loop needs one colour; any loop may hold any colour.',
    'mirror_minx.hint':'Choose pieces by their physical height and shape, rotate their orientation, and observe each face with the arrows. Layers turn 72 degrees.',
    'blanker.hint':'The fine grid on the white shell is decorative. Enter the shapes and orientations of eight physical 2×2 corners.',
    'directory.extended_family':'Letter Extensions',
    'directory.pentagonal_family':'Pentagonal Prisms',
    'directory.round_family':'Cylinders & Spheres',
    'directory.megaminx':'Dodecahedra',
    'directory.fto':'Octahedra',
    'directory.icosahedron':'Icosahedra',
    'directory.bandaged_family':'Bandaged & Siamese',
    'directory.special':'Other Shapes',
    'directory.special_hint':'Independent models outside the existing families.',
    'directory.minx_order':'{order}-layer Megaminx',
    'directory.kilominx_order':'Kilominx · 2 layers',
    'directory.fto_3':'FTO · 3 layers',
    'expanded.local_valid':'Piece colours and orientations checked; full reachability is checked when solving.',
    'directory.trajber':'Trajber’s Octahedron · 4×4',
    'expanded.reference_needed':'The shell and mechanism still need a reference. This model is not playable yet. Please provide a product picture or model page.',
    'poly.dogic_i_input':'12-colour Dogic: the three centre inlays form one piece. Paint each facet; choose a tip or a deep five-face turn.',
    'poly.dogic_20_input':'20-colour Dogic: paint each triangular face. Tips and deep layers turn by 72 degrees.',
    'poly.siamese_a_input':'A shares a 1×1×3 block. Paint each visible face; turns cannot split the connection.',
    'poly.siamese_b_input':'B shares a 2×1×3 block. Paint each visible face; turns cannot split the connection.',
    'poly.masterball_input':'Eight longitudes and four latitude layers. Layers turn 45 degrees; half-ball flips turn 180 degrees.',
    'poly.rubik_cheese_input':'Two layers, six wedges each. Paint the caps and rim stickers. Layers turn 60 degrees; half-cylinders flip 180 degrees.',
    'poly.pyraminx_diamond_input':'Six four-colour tips and eight central triangles. A tip and its four adjacent triangles turn 90 degrees.',
    'poly.cheese_3_input':'Three layers, six wedges each. Paint the caps and rim stickers. Layers turn 60 degrees; half-cylinders flip 180 degrees.',
    'container.hint':'Choose a coloured shape card, rotate the piece, and use the arrows to observe each face.',
    'poly.pentagonal_input':'Caps turn 72 degrees; side layers flip 180 degrees. Select a colour and paint; use arrows for each face. Professor has 5×5 side grids.',
    'poly.container_input':'Enter physical pieces by shape, colour and direction. The rectangular shell follows the Skewb mechanism.',
})
MESSAGES['ja'].update({
    'master_clover.deep':'大層',
    'master_clover.shallow':'小層',
    'master_clover.regular_only':'現在のMaster Cloverは通常の二層180°状態に対応しています。変形の内部切断面は未検証です。入力を保持しました。',
    'tilted.fixed_core':'中央の色面は固定コアにつながっています。強調されたコアの向きを修正してください。入力は保持されています。',
    'directory.aj_curvy_dinominx_4':'AJ 4層カービィ・ディノミンクス',
    'aj.error.fixed_centres':'12個の中央面は固定コアです。基準色を確認してください。入力は保持されています。',
    'aj.error.orbit_parity':'エッジの置換が角回転の条件を満たしません。両面の色を確認してください。入力は保持されています。',
    'aj.error.edge_flip':'エッジの向きが機構の条件を満たしません。入力は保持されています。',
    'directory.mf8_bauhinia_minx':'MF8 バウヒニア',
    'rex.error.edge_flip':'エッジの向きが標準120度回転の条件を満たしません。入力は保持されています。ジャンブリング状態は未対応です。',
    'rex.error.orbit_parity':'ピースの置換が標準120度回転の条件を満たしません。入力は保持されています。ジャンブリング状態は未対応です。',
    'directory.yeet_ball':'YJ アイビーボール',
    'dial.core':'コーナー層','dial.ring':'数字リング','dial.front':'表の輪','dial.back':'裏の輪',
    'dial.number':'数字 {number}','dial.select_number':'数字を選択',
    'poly.error.counts_numbers':'色または数字の数がこのモデルに合いません。強調された入力を確認してください。',
    'dial.wing':'翼の反転','dial.rotor':'中央ローター',
    'dial.rotor_front':'表の中央ローター','dial.rotor_back':'裏の中央ローター',
    'dial.twist_hint':'中央ノブをドラッグすると、この面だけが回ります。表・裏のローターを選び回転ボタンでも操作できます。',
    'poly.time_machine_input':'色と数字でリングを入力。数字は自動で進みます。コーナーの内側と外側の色は連動します。',
    'dial.front_side':'表','dial.back_side':'裏',
    'poly.bean_6_input':'色を選んで玉を入力、矢印で表裏を切替。各輪が単色なら完成で、色の位置は自由です。',
    'poly.bean_10_input':'色を選んで玉を入力、矢印で表裏を切替。各輪が単色なら完成で、色の位置は自由です。',
    'mirror_minx.hint':'実物の高さと形状でピースを選び、向きを調整し、矢印で各面を確認します。各層は72度回転します。',
    'blanker.hint':'白い表面の細線は装飾です。実際には2×2の八つのコーナーの形と向きを入力します。',
    'directory.extended_family':'文字形拡張シリーズ',
    'directory.pentagonal_family':'五角柱シリーズ',
    'directory.round_family':'円柱・球体シリーズ',
    'directory.megaminx':'十二面体シリーズ',
    'directory.fto':'八面体シリーズ',
    'directory.icosahedron':'二十面体シリーズ',
    'directory.bandaged_family':'バンデージ・連結シリーズ',
    'directory.special':'その他の形状',
    'directory.special_hint':'既存シリーズに属さない独立モデルです。',
    'directory.minx_order':'{order}段メガミンクス',
    'directory.kilominx_order':'キロミンクス · 2段',
    'directory.fto_3':'FTO · 3段八面体',
    'expanded.local_valid':'ピースの色と向きを確認しました。到達可能性は求解時に検証します。',
    'directory.trajber':'Trajber 八面体 · 4×4',
    'shape.error.corner_twist':'見えている角の向きが一致しません。角を確認してください。入力は保持されています。',
    'expanded.reference_needed':'外形と切断構造の確認が必要です。まだ操作できません。製品画像か型番ページを提供してください。',
    'poly.dogic_i_input':'12色Dogic。中央の三色面は一つのピースです。色を選んで入力し、頂点または五面を含む深層を回します。',
    'poly.dogic_20_input':'20色Dogic。各三角面の色を入力します。頂点と深層は72度回転します。',
    'poly.siamese_a_input':'Aは1×1×3の連結ブロックを共有します。各面を入力し、連結部分を切り離す回転はできません。',
    'poly.siamese_b_input':'Bは2×1×3の連結ブロックを共有します。各面を入力し、連結部分を切り離す回転はできません。',
    'poly.masterball_input':'経線8区分、緯度4層。各層は45度、半球は180度回転します。',
    'poly.rubik_cheese_input':'各層6個、計2層。上下と側面を単色で入力。層は60度、半円は180度回転します。',
    'poly.pyraminx_diamond_input':'四色の先端6個と中央三角形8個。先端と隣接する中央面4個が90度回転します。',
    'poly.cheese_3_input':'各層6個、計3層。上下と側面を単色で入力。層は60度、半円は180度回転します。',
    'container.hint':'形状と色のカードを選び、ピースの向きを回転し、矢印で各面を確認します。',
    'poly.pentagonal_input':'上下は72度、側層は180度回転。色を選んで連続入力し、矢印で各面を確認します。Professorの側面は5×5です。',
    'poly.container_input':'実物の形状・色・向きを入力します。長方体の外形はSkewb機構と一緒に回転します。',
})

# Curved edge-turning observation controls; no permanent instruction panel.
for lang,values in {
 'zh':('魔蝶 · 球切模型','调整形状','只调整选中块','按机构转动整层','自定角度','角块','棱载体','叶片','层转请选择 1～12 棱轴。','形状仍未匹配到可复形状态；输入已保留，可调整或重试。','块位重叠或朝向不符，请检查所调整的块。','打乱计算超时，原输入已保留。'),
 'en':('Curvy Copter · spherical profile','Adjust shape','Selected piece only','Turn a whole layer','Custom angle','Corner','Edge carrier','Leaf','Choose edge axis 1–12 for a layer turn.','Shape restoration did not finish. Input is preserved; adjust it or retry.','Overlapping positions or incompatible orientations; check edited pieces.','Scramble timed out. Your input is preserved.'),
 'ja':('Curvy Copter','形状の調整','選択ピースのみ','層を回す','角度を指定','コーナー','エッジ軸','葉片','層回転には1～12の棱軸を選んでください。','復形は未完了です。入力を保持しました。調整または再試行できます。','位置の重なりまたは向きの不一致を確認してください。','スクランブルがタイムアウトしました。入力は保持されています。'),
}.items():
 for key,value in zip(('directory.lanlan_curvy_copter','copter.shape','copter.single','copter.layer','copter.custom','copter.corner','copter.carrier','copter.leaf','copter.edge_axis','copter.shape_unresolved','copter.invalid_shape','copter.scramble_timeout'),values):
  MESSAGES[lang][key]=value

for lang,title,piece in (
 ('zh','平面十二轴菱形体','实体块 {number}'),
 ('en','Planar 12-Axis Rhombic Puzzle','Piece {number}'),
 ('ja','平面カット十二軸菱形パズル','ピース {number}')):
 MESSAGES[lang]['directory.planar_rhombic_12']=title
 MESSAGES[lang]['comet.piece']=piece

for lang,value in (
 ('zh','本次搜索未在时限内完成。输入已保留，可以重试或修改。'),
 ('en','Search did not finish within this run. Input is preserved; retry or edit it.'),
 ('ja','今回の探索は時間内に完了しませんでした。入力を保持しました。再試行または修正できます。')):
 MESSAGES[lang]['comet.timeout']=value

for lang,title in (('zh','蓝蓝十二轴十二面体 · Crazy Comet'),('en','LanLan Crazy Comet'),('ja','LanLan Crazy Comet')):
 MESSAGES[lang]['directory.lanlan_comet_physical']=title

for lang,title in (('zh','双子星'),('en','Twins'),('ja','MF8 Twins')):
 MESSAGES[lang]['directory.mf8_twins']=title

for lang,title in (('zh','太阳二号 · 棱转几何模型'),('en','SunCube II · edge-turning profile'),('ja','SunCube II · 棱回転モデル')):
 MESSAGES[lang]['directory.mf8_suncube_2']=title

for lang,message in (
 ('zh','回放未完成，当前进度已保留。可以重试或返回修改。'),
 ('en','Playback did not finish. Your current position is preserved; retry or return to edit.'),
 ('ja','再生は未完了です。現在位置を保持しました。再試行または入力の修正ができます。')):
 MESSAGES[lang]['poly.playback_failed']=message

for lang,message in (
 ('zh','当前已验证的动作尚不能完成此状态。输入已保留，可重试或继续修改；这不表示实物无解。'),
 ('en','The verified tools do not yet cover this state. Your input is preserved; retry or edit it. This does not prove the physical puzzle unsolvable.'),
 ('ja','確認済みの手順ではこの状態を解決できません。入力は保持されています。実物が解けないという意味ではありません。')):
 MESSAGES[lang]['tilted.group_unresolved']=message


for lang,title,message in (
 ('zh','花瓣魔方','此姿态需要先恢复外形；当前状态已保留，可以继续转动或重试求解。'),
 ('en','Flower Copter','Restore the shape first. The current state is preserved; continue turning or retry solving.'),
 ('ja','Flower Copter','まず形状を戻してください。現在の状態は保持されています。回転を続けるか求解を再試行できます。')):
 MESSAGES[lang]['directory.lanlan_flower_copter']=title
 MESSAGES[lang]['flower.regular_only']=message

for lang,message in (
 ('zh','此姿态需要先恢复外形；当前状态已保留，可以继续转动或重试求解。'),
 ('en','Restore the shape first. The current state is preserved; continue turning or retry solving.'),
 ('ja','まず形状を戻してください。現在の状態は保持されています。回転を続けるか求解を再試行できます。')):
 MESSAGES[lang]['twins.regular_only']=message

for lang,message in (
 ('zh','这是旧双子星模型或不同半径的存档，不能套用到新CAD布局。请按新模型重新录入；旧文件未被修改。'),
 ('en','This save belongs to the old Twins model or another radius. Re-enter it on the new CAD layout; the old file is unchanged.'),
 ('ja','旧モデルまたは別の半径の保存状態です。新しいCADモデルで入力し直してください。旧ファイルは変更していません。')):
 MESSAGES[lang]['twins.legacy_entry']=message

for lang,short,detail in (
 ('zh','待接入','已收录参考图。\n模型、录入、拧动与求解功能尚未开放。'),
 ('en','Coming later','Reference image included.\nModel, entry, turning and solving are not available yet.'),
 ('ja','準備中','参考画像を収録しています。\nモデル・入力・回転・求解はまだ利用できません。')):
 MESSAGES[lang]['expanded.pending_short']=short
 MESSAGES[lang]['expanded.pending_detail']=detail
