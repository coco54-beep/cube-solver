"""Labels for physical six-view entry, with no hidden piece numbers."""
ZH = {
 'six.title':'六视图录入', 'six.draw_hint':'选颜色，点一个格或拖框圈出同一块的整张面片。',
 'six.reference':'按前→右→后→左→上→下观察；前面朝向固定，不转动层。',
 'six.face_reference':'图上边：{top} · 图右边：{right} · 六个视图保持同一中心',
 'six.empty':'空位', 'six.plastic':'黑色塑料', 'six.unknown':'未录',
 'six.outside':'其余标为空位', 'six.depth_auto':'高度：自动匹配', 'six.depth_level':'高度：从外向内第 {n} 层',
 'six.progress':'已完成 {n}/6 个视图 · ✓匹配并应用', 'six.matching':'正在匹配外形与块位，可取消…',
 'six.incomplete':'青框位置还未录入。录完本面后，可将其余位置标为空位。',
 'six.conflict':'外形、切缝或颜色互相冲突，请检查录入；有青框时从该处检查。',
 'six.ambiguous':'还不能唯一确定块位，请补充青框处高度，并检查同色块之间的切缝。',
 'six.budget':'匹配达到时间上限，草稿已保留。请补充局部高度后重试。',
 'six.cancelled':'已取消匹配，录入草稿保留。', 'six.error':'匹配未完成，录入草稿保留。',
 'six.ok':'已应用六视图。结构匹配通过，尚不代表已证明可解。',
 'six.model_mismatch':'此状态不符合当前型号模型。',
 'six.model_note':'4×4×6 现有机构模型仍需核对；六视图匹配范围以当前模型为准。',
 'six.help':('从正前方开始，在六个平面中照实物录入。\n\n'
             '一个格只代表观察位置，不代表独立块。拖动框出同一张面片；相邻同色面片要分别框选，以保留切缝。横竖长条直接按实物框选，不用猜内部块编号。\n\n'
             '空位是没有魔方的地方；黑色塑料是有实体但没有贴纸；未录表示尚未确认。录完颜色和塑料后，点“其余标为空位”。\n\n'
             '默认自动匹配高度。信息不足时，选中局部色块，再用高度左右箭头指定从外向内的层；点高度文字恢复自动。\n\n'
             '✓在后台匹配六视图，冲突或歧义时保留草稿。颜色与结构匹配成功后才允许拧动或求解。复杂手动状态仍受现有求解器范围限制。'),
}
EN = {
 'six.title':'Six-view entry', 'six.draw_hint':'Choose a colour. Tap a cell or drag around one physical panel.',
 'six.reference':'Observe Front → Right → Back → Left → Up → Down. Keep the front reference; do not turn layers.',
 'six.face_reference':'Image top: {top} · Image right: {right} · Keep the same centre in all views',
 'six.empty':'Empty', 'six.plastic':'Black plastic', 'six.unknown':'Unknown',
 'six.outside':'Mark remaining empty', 'six.depth_auto':'Depth: automatic', 'six.depth_level':'Depth: layer {n} from outside',
 'six.progress':'{n}/6 views complete · ✓ match and apply', 'six.matching':'Matching shape and pieces. You can cancel…',
 'six.incomplete':'The highlighted sample is unknown. After entering panels, mark the rest of the view empty.',
 'six.conflict':'Shape, cuts or colours conflict. Review the input, starting at the highlight if shown.',
 'six.ambiguous':'Piece positions are ambiguous. Add the highlighted depth and check cuts between same-colour panels.',
 'six.budget':'Matching timed out; the draft is kept. Add local depth and retry.',
 'six.cancelled':'Matching cancelled; the draft is kept.', 'six.error':'Matching did not finish; the draft is kept.',
 'six.ok':'Six views applied. Structural matching does not prove solvability.',
 'six.model_mismatch':'This state does not fit the current model.',
 'six.model_note':'The current 4×4×6 mechanism still needs review; matching is limited to this model.',
 'six.help':('Enter what you see in six orthographic views, starting at the front.\n\n'
             'A grid cell is a sample, not a separate piece. Drag around one panel. Draw adjacent same-colour panels separately to record their cut. Rectangles can be horizontal or vertical; no internal piece IDs are needed.\n\n'
             'Empty means no material, plastic means material without a sticker, and unknown means unconfirmed. After entering panels, mark the rest empty.\n\n'
             'Depth is automatic unless needed. Select a region, then use depth arrows to specify a layer from outside; tap the depth label to reset to automatic.\n\n'
             '✓ matches in the background. Conflicts or ambiguity keep the draft. Twisting and solving require a matched state. General manual solving remains limited by the existing solver.'),
}
JA = {
 'six.title':'六方向入力', 'six.draw_hint':'色を選び、タップかドラッグで同じ面片を囲みます。',
 'six.reference':'前→右→後→左→上→下。前方向を基準に保ち、層は回さないでください。',
 'six.face_reference':'図の上：{top} · 図の右：{right} · 六方向で中心をそろえてください',
 'six.empty':'空き', 'six.plastic':'黒い樹脂', 'six.unknown':'未入力',
 'six.outside':'残りを空きにする', 'six.depth_auto':'奥行き：自動', 'six.depth_level':'奥行き：外側から {n} 層目',
 'six.progress':'{n}/6 方向完了 · ✓で照合・適用', 'six.matching':'形とピースを照合中。キャンセルできます…',
 'six.incomplete':'枠内は未入力です。面片を入力後、残りを空きにしてください。',
 'six.conflict':'形・切れ目・色が矛盾しています。枠があればその位置から確認してください。',
 'six.ambiguous':'位置が一意に決まりません。枠内の奥行きと同色面片の切れ目を確認してください。',
 'six.budget':'照合が時間上限に達しました。入力は保持しています。局所の奥行きを補って再試行してください。',
 'six.cancelled':'照合を中止しました。入力は保持しています。', 'six.error':'照合が完了しませんでした。入力は保持しています。',
 'six.ok':'六方向を適用しました。構造の一致は可解性の証明ではありません。',
 'six.model_mismatch':'現在のモデルに一致しない状態です。',
 'six.model_note':'4×4×6 の機構モデルは要確認です。照合は現在のモデルの範囲に限られます。',
 'six.help':('正面から六方向を実物どおり入力します。\n\n'
             'マスは観察位置であり独立したピースではありません。一枚の面片を囲み、同じ色の隣接面片は別々に囲んで切れ目を記録します。内部番号は不要です。\n\n'
             '空き、シールのない黒い樹脂、未入力を区別します。色と樹脂を入力してから残りを空きにします。\n\n'
             '奥行きは通常自動です。必要な部分を選び、矢印で外側からの層を指定できます。奥行き表示を押すと自動に戻ります。\n\n'
             '✓でバックグラウンド照合します。矛盾や曖昧さがあれば入力を保持します。照合完了後に回転・求解できます。複雑な手動求解は既存ソルバーの制限があります。'),
}
MESSAGES = {'zh': ZH, 'en': EN, 'ja': JA}

ZH.update({
 'poly.cuboid_input':'按实体色块逐面录入。固定外形长方体支持从当前状态求解；可变形型号使用六视图。',
 'six.model_note':'4×4×6 使用四阶核心与独立外层延伸件，外层完整时才可单独转动。',
 'cuboid.extension_layer':'独立外层', 'cuboid.core_layers':'核心外侧 {i} 层',
 'cuboid.search_budget':'计算达到本次时间上限，录入已保留。复杂迷彩和 4×4×2 状态可能需要更多时间；这不表示无解。',
 'cuboid.identity_conflict':'块的颜色或方向存在冲突，请检查录入。',
 'cuboid.identity_unreachable':'当前颜色、块位或朝向不符合此型号，请核对录入。',
 'cuboid.identity_ambiguous':'块位仍有歧义，请在六视图补充局部高度与切缝。',
 'cuboid.identity_budget':'匹配达到时间上限，请补充局部高度后重试。',
 'cuboid.identity_incomplete':'请先完整录入六视图。',
 'cuboid.core_replay_failed':'核心解法未通过校验，录入已保留。',
 'cuboid.replay_failed':'解法未通过完整回放校验，录入已保留。',
})
EN.update({
 'poly.cuboid_input':'Enter the physical panels face by face. Fixed cuboids solve from the entered state; shape-changing models use six views.',
 'six.model_note':'4×4×6 uses a four-order core with separate extensions. An outer layer turns independently only when complete.',
 'cuboid.extension_layer':'Independent outer layer', 'cuboid.core_layers':'Outer {i} core layer(s)',
 'cuboid.search_budget':'The calculation reached its time limit; your input is kept. Complex Camouflage and 4×4×2 states may take longer. This does not mean unsolvable.',
 'cuboid.identity_conflict':'Piece colours or orientations conflict. Review the input.',
 'cuboid.identity_unreachable':'The colours, positions or orientations do not fit this model. Review the input.',
 'cuboid.identity_ambiguous':'Positions are ambiguous. Add local depth and cuts in the six views.',
 'cuboid.identity_budget':'Matching timed out. Add local depth and retry.',
 'cuboid.identity_incomplete':'Complete the six views first.',
 'cuboid.core_replay_failed':'Core replay did not pass validation. Your input is kept.',
 'cuboid.replay_failed':'Full solution replay did not pass validation. Your input is kept.',
})
JA.update({
 'poly.cuboid_input':'実物の面片を一面ずつ入力します。固定形状は入力状態から求解し、変形モデルは六方向を使います。',
 'six.model_note':'4×4×6 は四階コアと独立した延長部を使用し、外層がそろった時だけ単独で回転できます。',
 'cuboid.extension_layer':'独立した外層', 'cuboid.core_layers':'コアの外側 {i} 層',
 'cuboid.search_budget':'計算が時間上限に達しました。入力は保持しています。複雑な迷彩・4×4×2 はさらに時間が必要な場合があります。解なしという意味ではありません。',
 'cuboid.identity_conflict':'色または向きが矛盾しています。入力を確認してください。',
 'cuboid.identity_unreachable':'色・位置・向きがこのモデルに一致しません。入力を確認してください。',
 'cuboid.identity_ambiguous':'位置が曖昧です。六方向で局所の奥行きと切れ目を補ってください。',
 'cuboid.identity_budget':'照合が時間上限に達しました。局所の奥行きを補って再試行してください。',
 'cuboid.identity_incomplete':'先に六方向を入力してください。',
 'cuboid.core_replay_failed':'コアの再生検証に失敗しました。入力は保持しています。',
 'cuboid.replay_failed':'解法全体の再生検証に失敗しました。入力は保持しています。',
})

ZH['six.help'] = ZH['six.help'].replace('复杂手动状态仍受现有求解器范围限制。',
 '长方体支持从输入状态求解。复杂迷彩和 4×4×2 采用 45 秒限时搜索；可取消，超时保留录入，不表示无解。')
EN['six.help'] = EN['six.help'].replace('General manual solving remains limited by the existing solver.',
 'Cuboids solve from the entered state. Complex Camouflage and 4×4×2 use a cancellable 45-second search. A timeout keeps the input and does not mean unsolvable.')
JA['six.help'] = JA['six.help'].replace('複雑な手動求解は既存ソルバーの制限があります。',
 '入力状態から求解します。複雑な迷彩・4×4×2 は45秒の探索を行います。中止でき、時間切れでも入力は保持し、解なしとは判定しません。')
