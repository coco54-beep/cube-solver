"""摄像头识别界面的多语言文案。"""

MESSAGES = {
    "zh": {
        "input.camera": "拍照识别",
        "camera.title": "{n} 阶 · 拍照识别",
        "camera.capture": "拍照",
        "camera.import": "导入图片",
        "camera.apply": "应用到录入",
        "camera.tip": "把当前面正对取景框方框拍照；用 < > 切换面，屏上会提示转动方向。",
        "camera.face_progress": "{face}({code}) · 已识别 {done}/6",
        "camera.rot_hint": "把魔方{dir}翻转 90°，对准 {face} 面",
        "camera.dir.left": "向左",
        "camera.dir.right": "向右",
        "camera.dir.up": "向上",
        "camera.dir.down": "向下",
        "camera.detected": "已识别 {face} 面",
        "camera.processing": "正在识别…",
        "camera.processing_failed": "识别未完成，请调整取景框后重试",
        "camera.detect_failed": "识别失败：{reason}",
        "camera.no_image": "未能获取图像",
        "camera.loaded": "已载入图片",
        "camera.no_camera": "此设备没有可用相机，请用「导入图片」",
        "camera.applied": "已应用到录入页",
        "camera.pick_file": "选择照片",
        "camera.choose_order": "请选择魔方阶数",
    },
    "en": {
        "input.camera": "Photo scan",
        "camera.title": "{n}×{n} · Photo scan",
        "camera.capture": "Capture",
        "camera.import": "Import image",
        "camera.apply": "Use for input",
        "camera.tip": "Aim the current face into the box and tap Capture; use < / > to switch faces (the screen shows how to turn it).",
        "camera.face_progress": "{face} ({code}) · {done}/6",
        "camera.rot_hint": "Turn the cube {dir} 90° to face {face}",
        "camera.dir.left": "left",
        "camera.dir.right": "right",
        "camera.dir.up": "up",
        "camera.dir.down": "down",
        "camera.detected": "Detected face {face}",
        "camera.processing": "Recognizing…",
        "camera.processing_failed": "Recognition failed. Adjust the guide and retry.",
        "camera.detect_failed": "Detection failed: {reason}",
        "camera.no_image": "No image captured",
        "camera.loaded": "Image loaded",
        "camera.no_camera": "No camera on this device; use Import image.",
        "camera.applied": "Applied to input.",
        "camera.pick_file": "Choose photo",
        "camera.choose_order": "Choose the cube order",
    },
    "ja": {
        "input.camera": "写真で読み取り",
        "camera.title": "{n}×{n} · 写真読み取り",
        "camera.capture": "撮影",
        "camera.import": "画像を読み込む",
        "camera.apply": "入力に反映",
        "camera.tip": "面をガイド枠に合わせて「撮影」。< / > で面を切替（回転方向を表示）。",
        "camera.face_progress": "{face} ({code}) · {done}/6",
        "camera.rot_hint": "キューブを{dir}へ90°回して {face} 面に",
        "camera.dir.left": "左",
        "camera.dir.right": "右",
        "camera.dir.up": "上",
        "camera.dir.down": "下",
        "camera.detected": "{face} 面を認識しました",
        "camera.processing": "認識中…",
        "camera.processing_failed": "認識できませんでした。枠を調整して再試行してください。",
        "camera.detect_failed": "認識に失敗: {reason}",
        "camera.no_image": "画像を取得できません",
        "camera.loaded": "画像を読み込みました",
        "camera.no_camera": "この端末にカメラがありません。「画像を読み込む」を使ってください",
        "camera.applied": "入力画面に反映しました",
        "camera.pick_file": "写真を選ぶ",
        "camera.choose_order": "キューブの段数を選択",
    },
}


# 拍照后的操作与识别失败时的可执行提示。
for _lang, _text in {
    "zh": {
        "camera.tip": "正对当前面拍照；用左右箭头换面，并按提示翻转魔方。",
        "camera.edit_tip": "拖动四角对齐；点小魔方改色，左右箭头演示翻面",
        "camera.import_failed": "无法读取这张照片，请重新选择",
        "camera.rotate": "旋转照片",
        "camera.recheck": "按框识别",
        "camera.edit_color": "选择该格颜色",
        "camera.corrected": "当前面的颜色已修正",
        "camera.reason.adjust": "请拖动四角对齐魔方面，再按框识别",
        "camera.reason.partial": "部分颜色不确定，请点色格修正，或调整四角",
        "camera.permission": "请允许使用相机；也可以导入图片",
    },
    "en": {
        "camera.tip": "Photograph the current face straight on. Use the arrows and follow the turn directions.",
        "camera.edit_tip": "Align the corners; tap the cube to edit colors. Arrows show how to turn it.",
        "camera.import_failed": "Could not read this photo. Please choose it again.",
        "camera.rotate": "Rotate photo",
        "camera.recheck": "Scan selection",
        "camera.edit_color": "Choose cell color",
        "camera.corrected": "Current face colors corrected.",
        "camera.reason.adjust": "Align the four corners with the face, then scan the selection.",
        "camera.reason.partial": "Some colors are uncertain. Tap cells to correct them or adjust the corners.",
        "camera.permission": "Allow camera access, or import an image.",
    },
    "ja": {
        "camera.tip": "面を正面から撮影してください。矢印で面を切り替え、表示の方向に回します。",
        "camera.edit_tip": "四隅を面に合わせ、ミニキューブで色を修正。矢印で回し方を表示します。",
        "camera.import_failed": "写真を読み込めません。もう一度選択してください。",
        "camera.rotate": "写真を回転",
        "camera.recheck": "枠内を認識",
        "camera.edit_color": "マスの色を選択",
        "camera.corrected": "現在の面の色を修正しました。",
        "camera.reason.adjust": "四隅を面に合わせて、枠内を認識してください。",
        "camera.reason.partial": "不確かな色があります。マスの色か四隅を修正してください。",
        "camera.permission": "カメラの使用を許可するか、画像を読み込んでください。",
    },
}.items():
    MESSAGES[_lang].update(_text)


for _lang, _text in {
    'zh': {
        'camera.choose_puzzle': '选择要拍照识别的魔方',
        'camera.ordinary': '普通魔方',
        'camera.limit': '拍照识别仅支持五阶及以下',
        'camera.shape_title': '{name} · {n} 阶 · 拍照识别',
        'camera.surface_tip': '对齐各顶点和切线；点小模型改色。近似色可用取色校准',
        'camera.surface_progress': '{face} · 已识别 {done}/{total}',
        'camera.face_number': '第 {number} 面',
        'camera.surface_turn': '跟随小模型整体翻转，对准{face}',
        'camera.surface_partial': '请对齐顶点和切线，再按框识别；不确定的颜色可取色校准或点模型修正',
        'camera.calibrate': '取色校准',
        'camera.calibrate_choose': '选择要校准的颜色',
        'camera.sample_prompt': '点照片中属于 {number} 号颜色的色块内部',
        'camera.sample_dark': '这里太暗，请点色块内部，避开黑色切缝',
        'camera.calibrated': '已校准，并更新已拍各面；手动改色已保留',
        'camera.complete_first': '潘多拉请先完成六面颜色；点小模型补齐空白',
        'camera.invalid_input': '颜色或块的组合不合法，请检查各面朝向和颜色',
    },
    'en': {
        'camera.choose_puzzle': 'Choose a puzzle to scan',
        'camera.ordinary': 'Standard cube',
        'camera.limit': 'Photo scanning supports orders up to five',
        'camera.shape_title': '{name} · Order {n} · Photo scan',
        'camera.surface_tip': 'Align vertices and cuts. Tap the model to edit; calibrate similar colors.',
        'camera.surface_progress': '{face} · {done}/{total} faces',
        'camera.face_number': 'Face {number}',
        'camera.surface_turn': 'Follow the model turn to {face}',
        'camera.surface_partial': 'Align vertices and cuts, then scan. Calibrate colors or tap the model to correct them.',
        'camera.calibrate': 'Calibrate',
        'camera.calibrate_choose': 'Choose a color to calibrate',
        'camera.sample_prompt': 'Tap inside a sticker with color {number} in the photo',
        'camera.sample_dark': 'Too dark. Tap inside a sticker, away from black cuts.',
        'camera.calibrated': 'Colors updated on stored photos; manual edits kept.',
        'camera.complete_first': 'Complete all six Pandora faces; tap the model to fill missing colors.',
        'camera.invalid_input': 'Invalid color or piece combination. Check face orientation and colors.',
    },
    'ja': {
        'camera.choose_puzzle': '読み取るパズルを選択',
        'camera.ordinary': '通常のキューブ',
        'camera.limit': '写真読み取りは5段以下に対応',
        'camera.shape_title': '{name} · {n}段 · 写真読み取り',
        'camera.surface_tip': '頂点と切れ目を合わせ、モデルで色を修正。似た色は校正できます。',
        'camera.surface_progress': '{face} · 認識済み {done}/{total} 面',
        'camera.face_number': '第{number}面',
        'camera.surface_turn': 'モデルに合わせて全体を回し、{face}を正面に',
        'camera.surface_partial': '頂点と切れ目を合わせて認識。色の校正またはモデルで修正できます。',
        'camera.calibrate': '色を校正',
        'camera.calibrate_choose': '校正する色を選択',
        'camera.sample_prompt': '写真内の{number}番の色のステッカー内部をタップ',
        'camera.sample_dark': '暗すぎます。黒い切れ目を避けて色面をタップしてください。',
        'camera.calibrated': '撮影済みの色を更新しました。手動修正は保持されます。',
        'camera.complete_first': 'パンドラの6面を完成してください。モデルで空欄を補えます。',
        'camera.invalid_input': '色またはピースの組合せが不正です。面の向きと色を確認してください。',
    },
}.items():
    MESSAGES[_lang].update(_text)


# Ordinary cubes calibrate all six colors using the actual stickers.
for _lang, _text in {
    'zh': {
        'camera.sample_color_prompt': '点照片中{color}色块的内部，避开反光和切缝',
        'camera.color_W': '白色', 'camera.color_Y': '黄色', 'camera.color_R': '红色',
        'camera.color_O': '橙色', 'camera.color_B': '蓝色', 'camera.color_G': '绿色',
    },
    'en': {
        'camera.sample_color_prompt': 'Tap inside a {color} sticker, away from glare and cuts',
        'camera.color_W': 'white', 'camera.color_Y': 'yellow', 'camera.color_R': 'red',
        'camera.color_O': 'orange', 'camera.color_B': 'blue', 'camera.color_G': 'green',
    },
    'ja': {
        'camera.sample_color_prompt': '反射と切れ目を避け、写真の{color}ステッカー内部をタップ',
        'camera.color_W': '白', 'camera.color_Y': '黄色', 'camera.color_R': '赤',
        'camera.color_O': 'オレンジ', 'camera.color_B': '青', 'camera.color_G': '緑',
    },
}.items():
    MESSAGES[_lang].update(_text)

for _lang, _text in {
    'zh': {
        'camera.color_number': '{number}号色',
        'camera.palette_hint': '按钮底色就是对应颜色',
        'camera.calibration_retry': '样本不清楚或与其他颜色太接近，请避开反光和切缝重新取色',
    },
    'en': {
        'camera.color_number': 'Color {number}',
        'camera.palette_hint': 'Each button background shows its corresponding color.',
        'camera.calibration_retry': 'Sample unclear or too similar to another color. Resample away from glare and cuts.',
    },
    'ja': {
        'camera.color_number': '{number}番の色',
        'camera.palette_hint': 'ボタンの背景が対応する色です。',
        'camera.calibration_retry': '色が不明瞭か他の色に近すぎます。反射と切れ目を避けて再採取してください。',
    },
}.items():
    MESSAGES[_lang].update(_text)


for _lang, _text in {
    'zh': {
        'camera.reset_calibration': '恢复默认', 'camera.calibration_reset': '已恢复默认取色',
        'camera.cancel_scan': '取消识别', 'camera.scan_cancelled': '已取消识别，照片与已确认颜色已保留',
        'camera.locating': '正在定位', 'camera.reading': '正在取色', 'camera.recalibrating': '正在更新各面',
        'camera.uncertain': '本面还有 {count} 块颜色不确定，已用橙色边框标出；点击小模型修正',
    },
    'en': {
        'camera.reset_calibration': 'Reset colors', 'camera.calibration_reset': 'Default color references restored.',
        'camera.cancel_scan': 'Cancel scan', 'camera.scan_cancelled': 'Scan cancelled. Photo and confirmed colors kept.',
        'camera.locating': 'Locating face', 'camera.reading': 'Reading colors', 'camera.recalibrating': 'Updating faces',
        'camera.uncertain': '{count} uncertain stickers on this face have orange outlines. Tap the model to correct.',
    },
    'ja': {
        'camera.reset_calibration': '初期色に戻す', 'camera.calibration_reset': '標準の色基準に戻しました。',
        'camera.cancel_scan': '認識を取消', 'camera.scan_cancelled': '認識を取消しました。写真と確定済みの色は保持されます。',
        'camera.locating': '面を検出中', 'camera.reading': '色を認識中', 'camera.recalibrating': '各面を更新中',
        'camera.uncertain': 'この面の{count}個の色が不確定です。オレンジの枠をモデル上でタップして修正してください。',
    },
}.items():
    MESSAGES[_lang].update(_text)
