"""Actions for complete, state-specific restoration demonstrations."""
MESSAGES={
    'zh':{
        'demo.complete':'完整还原演示',
        'demo.complete_mode':'{order}阶 · 完整还原',
        'demo.my_input':'按我的录入还原',
        'demo.preparing_complete':'正在为真实打乱生成完整还原步骤…',
        'demo.complete_failed':'这次完整还原演示未生成：{detail}',
        'demo.route':'原创分步教程',
        'demo.chapter_play':'打开本章演示',
        'demo.original_credit':'本应用原创 · 按本型号机构编写，公式与三维案例逐项核验。',
        'demo.close':'关闭',
    },
    'en':{
        'demo.complete':'Complete solution demo',
        'demo.complete_mode':'{order}×{order} · Complete solution',
        'demo.my_input':'Solve my entered puzzle',
        'demo.preparing_complete':'Preparing a complete solution for a real scramble…',
        'demo.complete_failed':'The complete solution demo could not be prepared: {detail}',
        'demo.route':'Original step-by-step guide',
        'demo.chapter_play':'Open chapter example',
        'demo.original_credit':'Written for this model. Formulas and 3D examples are independently checked.',
        'demo.close':'Close',
    },
    'ja':{
        'demo.complete':'完全復元デモ',
        'demo.complete_mode':'{order}×{order} · 完全復元',
        'demo.my_input':'入力した状態を復元',
        'demo.preparing_complete':'スクランブルからの完全な復元手順を準備しています…',
        'demo.complete_failed':'完全復元デモを準備できませんでした：{detail}',
        'demo.route':'オリジナル手順ガイド',
        'demo.chapter_play':'章のデモを開く',
        'demo.original_credit':'本モデル用の教材です。手順と3D例を個別に確認しています。',
        'demo.close':'閉じる',
    },
}

_MEDIA={
 'chapters':('章节 {i}/{total}','Sections {i}/{total}','区間 {i}/{total}'),
 'chapter_list':('章节目录 · 点击跳转','Sections · Tap to seek','区間一覧・タップで移動'),
 'speed':('动作 {speed}×','Moves {speed}×','動作 {speed}×'),
 'first_actions':('本段开始依次执行：{moves}。先看清模型标记的转轴与层。','The first moves are {moves}. Follow the highlighted axis and layer.','最初の手順は {moves}。モデルの軸と層を確認してください。'),
 'clockwise':('顺时针','clockwise','時計回り'), 'counterclockwise':('逆时针','counterclockwise','反時計回り'),
 'face_action':('从{face}面观察，转动该侧第 1–{layers} 层{direction} {angle}°；保持示例握法。','Looking at {face}, turn layers 1–{layers} {direction} {angle}°; keep the example grip.','{face}面から見て1–{layers}層を{direction}に{angle}°回します。持ち方を保ってください。'),
 'axis_action':('动作 {move}：沿模型标记的实际转轴与层操作，完成后核对相邻块的接缝。','Move: {move}. Use the marked physical axis and layer, then check adjacent seams.','動作 {move}。モデルの軸と層に沿って回し、隣接ピースの境界を確認してください。'),
 'estimated_length':('预计片长约 {minutes} 分 {seconds} 秒；按当前动作速度，旁白生成后更新。','Estimated video length: {minutes}m {seconds}s at this speed; narration timing is provisional.','動画の長さ目安：{minutes}分{seconds}秒。音声生成後に更新します。'),
 'eta_pending':('剩余导出时间：正在测量当前设备速度…','Export time remaining: measuring this device…','残り書き出し時間を測定中…'),
 'eta':('预计剩余约 {minutes} 分 {seconds} 秒（随设备负载更新）','About {minutes}m {seconds}s remaining (updates with device load)','残り約 {minutes}分{seconds}秒（負荷に応じて更新）'),
 'loading_course':('正在载入并核验完整实例课程…','Loading and verifying the full worked course…','完全復元例を読み込み、検証しています…'),
 'fixed_course':('完整实例课程（固定起始状态）','Full worked course (fixed start)','完全復元例（固定の初期状態）'),
 'previous':('上一段','Previous section','前の区間'),
 'next':('下一段','Next section','次の区間'),
 'voice_off':('旁白：关','Narration: off','音声：オフ'),
 'voice_on':('旁白：开','Narration: on','音声：オン'),
 'speaking':('正在讲解本段，听完后继续播放…','Narrating this section; playback will follow…','区間の説明後に再生を続けます…'),
 'voice_missing':('系统语音不可用。请在系统设置中安装本课程语言的语音，再重试；也可关闭旁白播放。','System voice unavailable. Install a voice for the course language, or turn narration off.','対応するシステム音声をインストールするか、音声をオフにしてください。'),
 'export':('导出视频','Export video','動画を書き出す'),
 'export_hint':('导出三维步骤、章节字幕和进度。完整课程会保留全部动作，长解需要较长时间；导出时可取消。中文原创课程使用中文系统语音。','Exports the 3D moves, section captions and progress. Every move is retained; long courses take time. Cancel anytime. Original Chinese courses use a Chinese system voice.','3D手順と字幕を書き出します。長い例も全手順を保持します。途中で中止できます。中国語教材は中国語音声を使います。'),
 'with_voice':('包含系统旁白','Include system narration','システム音声を含める'),
 'full':('导出完整案例','Export full case','例全体を書き出す'),
 'current':('只导出当前段','Export current section','現在の区間のみ'),
 'preparing':('正在准备旁白 {i}/{total}…','Preparing narration {i}/{total}…','音声を準備中 {i}/{total}…'),
 'rendering':('正在导出：第 {i}/{total} 步','Exporting move {i}/{total}','書き出し中 {i}/{total}'),
 'encoding':('正在完成视频文件…','Finalizing video…','動画を仕上げています…'),
 'finished':('视频已导出：\n{path}','Video exported:\n{path}','保存しました：\n{path}'),
 'failed':('视频导出失败：{detail}','Video export failed: {detail}','動画を書き出せませんでした：{detail}'),
 'cancelled':('已取消视频导出','Video export cancelled','書き出しを中止しました'),
 'save':('另存到手机','Save on phone','端末に保存'),
 'saved':('已保存到选择的位置','Saved to the selected location','選択した場所に保存しました'),
 'backend_missing':('找不到视频编码器；桌面版需要可用的 FFmpeg。','Video encoder unavailable; desktop export requires FFmpeg.','動画エンコーダーがありません。PC版には FFmpeg が必要です。'),
}
for _key,_values in _MEDIA.items():
 for _lang,_value in zip(('zh','en','ja'),_values):MESSAGES[_lang]['media.'+_key]=_value

for _lang,_step,_prefix in (('zh','逐步讲解','第 {i} 步。'),('en','Explain each move','Move {i}. '),('ja','一手ずつ解説','第 {i} 手。')):
    MESSAGES[_lang]['media.voice_step']=_step
    MESSAGES[_lang]['media.step_voice']=_prefix

for _lang,_value in (('zh','章节讲解'),('en','Chapter voice'),('ja','章の解説')):
    MESSAGES[_lang]['media.voice_on']=_value
