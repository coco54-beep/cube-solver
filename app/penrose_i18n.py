"""Three visible colours; ordinary solver identities stay internal."""
MESSAGES = {
 'zh': {
  'penrose.red':'红', 'penrose.blue':'蓝', 'penrose.yellow':'黄',
  'penrose.valid':'颜色、块形与方向匹配通过，可以拧动或求解。',
  'penrose.input_hint':'按实物填红、蓝、黄，块形和方向会自动重建。',
  'penrose.incomplete':'请录完六面的红、蓝、黄；完整块会自动生成对应外形。',
  'penrose.counts':'红、蓝、黄各应为 {count} 格，请检查颜色数量。',
  'penrose.pieces':'有块的颜色组合或方向不符合彭罗斯结构，请检查相邻面。',
  'penrose.unreachable':'颜色分布无法组成可还原的彭罗斯，请检查角块、棱块和中心颜色。',
  'penrose.budget':'块位匹配达到时间上限，录入已保留，请检查颜色后重试。',
 },
 'en': {
  'penrose.red':'Red', 'penrose.blue':'Blue', 'penrose.yellow':'Yellow',
  'penrose.valid':'Colours, shapes and orientations matched. Ready to turn or solve.',
  'penrose.input_hint':'Enter red, blue and yellow; piece shapes and orientations rebuild automatically.',
  'penrose.incomplete':'Enter red, blue and yellow on all six views. Complete pieces acquire their matching shape automatically.',
  'penrose.counts':'Red, blue and yellow must each appear in {count} cells. Check the colour counts.',
  'penrose.pieces':'A piece colour combination or orientation does not fit Penrose. Check adjacent faces.',
  'penrose.unreachable':'These colours cannot form a solvable Penrose. Check corners, edges and centre colours.',
  'penrose.budget':'Piece matching timed out. Your input is kept; check the colours and retry.',
 },
 'ja': {
  'penrose.red':'赤', 'penrose.blue':'青', 'penrose.yellow':'黄',
  'penrose.valid':'色・形・向きが一致しました。回転または求解できます。',
  'penrose.input_hint':'赤・青・黄を入力すると、ピースの形と向きが自動で再構成されます。',
  'penrose.incomplete':'六方向の赤・青・黄を入力してください。完成したピースの形は自動で再構成します。',
  'penrose.counts':'赤・青・黄はそれぞれ {count} マスです。色の数を確認してください。',
  'penrose.pieces':'色の組み合わせまたは向きがペンローズに一致しません。隣接面を確認してください。',
  'penrose.unreachable':'可解なペンローズになりません。角・辺・中心の色を確認してください。',
  'penrose.budget':'照合が時間上限に達しました。入力は保持しています。色を確認して再試行してください。',
 },
}
