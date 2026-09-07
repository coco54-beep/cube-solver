# 5x5 中心保持配棱 —— 突破记录

## 背景（此前负面结论）
此前在 `W outer W'`(depth 1-2) 宏空间内，中心保持与配对能力不相容：
- inner-slice 配棱必然扰动中心
- 单一 `W outer W'` 从被扰动 stuck 无法恢复中心
- 从深散态中心保持宏配不出棱
- 结论：无法在 depth 1-2 宏空间达成「中心恢复 + 保护组 + 配对增加」

## 本次突破：depth 3 扩展 + 两步成对法

### 1) 中心保持宏扩展到 depth 3
枚举 `2X outer^k 2X'`（k=1..3，中心 color_off 恒 0）：
- `W outer W'`(1-2) 数量 ~72/216，从深散态配不出棱
- **depth 3 得到 3480 个中心保持宏**（compact 快速筛选 color_off==0）
- 从深散态（paired=0）找到能净增配对的宏，如：
  - `2D B D B' 2D'`（0→1）
  - `2L D L2 D' 2L'`、`2L' U L2 U' 2L`

### 2) 关键认知：paired_count 是离散跳变，单动作会扰动中心
- 中心保持的单元是**宏**（`2X outer^k 2X'`），不是单动作
- 评分须用平滑的 `edge_relation`（类型锚定）聚合/rel，而非离散 paired_count

### 3) 两步成对法（数据中心保持）
- **第一步 聚集**：以中心保持宏为动作做单 target beam（compact 态），把 target 三块聚到同一槽（rel 0→3），用时 ~4s。评分用 rel（类型锚定，不看朝向）。
- **第二步 翻转修正**：rel=3 只保证三块同槽（`edge_relation` 类型锚定），
  但 `is_edge_paired` 还要求**朝向一致**（翼块翻转）。找到中心保持宏翻正翼：
  - `2L' B' R2 B 2L`（UF 左翼 U面 B→W，is_edge_paired 变 True）

### 根因
`edge_relation` = 三块同槽（不看朝向）；`is_edge_paired` = 三块同色对 + 朝向一致。
聚到 rel=3 的槽里，翼块可能翻转（贴错面颜色），需翻转修正才成真配对。

### 4) 配棱器结果（中心恒归面）
新 `pair_all_edges` 中心保持版（聚齐 + 翻转修正循环）：
- seed5: paired=1（原 stuck 0）
- seed9: paired=2
- seed11: paired=2
- seed20: paired=1
打破「中心保持配不出棱」负面结论。每条耗时 ~80-100s，配到 1-2 条后卡住。

## 待优化 / 卡点
- **单条成对已可行**（gather+flip，中心恒归面）。
- **多条累积失败（本质障碍）**：配新条必拆已配条。多次尝试（安全宏子集、
  身份锚定 `is_tredge_group_paired` 锁存、换自由切片轴）均无法累积，paired 恒 1。
- **根因**：gather 宏是「全局自由切片」性质，会挪动所有块（含已配对组合），
  无法真正隔离已配对组合。
- **真正需要的宏类型**：**「隔离/转出」宏**——把配好的组合**整体移出当前自由
  切片**（换切片轴到保护区）。这是另一类宏（整组合迁移，保配对），当前宏库
  没有，需全新研究。
- **提速**：全库 3480 宏 beam 搜索太贵；需预筛对本 target 有效的候选宏。
- 成对后 12 条完整达成待「隔离/转出宏」。

## 关键数据
- 中心保持宏（depth≤3）共 3480 个：长度 5 的 3000、长度 4 的 408、长度 3 的 72。
- 配好 1 条后，3385/3480 中心保持宏**保已有配对**（不计数），仅 95 个拆配对。
- 大 beam（width150/depth5）下几乎所有 target 都能聚到 rel=3（只少数 rel=2）。

## ===== 第二阶段：slice-band 安全存储 + 保护兼容规划 =====

### 核心模块（已构建并验证）
- `macro_index.py`：宏效果去重（3480→**526** 唯一效果），全部 center 保持。
  `compatible_storage_mask`/`split_slot_mask` 与真实 Cube **100% 一致**（6312 项、0 不一致）。
- `slice_band.py`：`SliceBand` 活动带，离线计算 work/split/safe_storage_slots。
  例：`2U` 的 safe = `{DB,DF,DL,DR}`（D 层），split = `{BL,BR,FL,FR}`。
- `storage_planner.py`：纯外层 `store_paired_tredge()`，槽图 BFS 把完整组搬到 safe 槽。
  例：`2L` band 下，一步 `('U',)` 把 UF 组搬到 UL（safe），preserved/safe/center 全 True。
- `pairing_transaction.pair_one_protected()`：商店(保护组→safe) + 兼容宏 gather + flip，
  验证 `centers_solved ∧ 保护组全存活 ∧ paired ≥ before+1`。重放一致性 True，~1.5s。

### 主循环累积成功（突破核心瓶颈）
用 `pair_one_protected` 逐步累积，**中心全程归面、保护组全部存活**：
| seed | 最终配对 | 中心 |
|------|---------|------|
| 5  | **10** | True |
| 9  | **8**  | True |
| 11 | **9**  | True |
| 20 | **8**  | True |

从「只能配 1-2 条」到「普遍积累 8-10 条」。最后停在 8-10，剩余 2-4 条即
free-slice 最难的「最后两条/最后一批」，可能需要共享切片的 batch 处理。

### 关键改进点
- 兼容掩码预筛（`candidates_compatible`）替代全库重放 → 单次选择 <2s。
- 宏去重 3480→526 大幅缩小搜索空间。
- 纯外层转出（slice-band safe 存储）是「配好的锁起来」的正确机制，
  而非寻找万能局部宏。



## ===== 第三阶段：batch 共享切片（共享打开切片批次事务）=====

### 核心模型
把闭环宏 W A W' 拆成 open/body/close，让多个 body 共享同一切片：
W body1 [store1] body2 [store2] ... W'，中间状态可乱，只在批次终点一次性验收：
centers_solved ∧ 原保护组全部恢复 ∧ 配对 ≥ before+1。

### 关键原理
- **不可机械拆分拼接**：W A W' + W B W' ≠ W A B W'，因 W' W 抵消后
  B 面对的状态已变。必须通过真实 Cube5 重放重新验证。
- **compact 态不含翼朝向**：paired_home_slots 用「同槽」判配对会高估真实配对
  （翼块翻转时同槽但未真配对），导致紧凑评分排序错位、把有效批次挤出。
  → **不能靠紧凑评分排序选 top，必须真实重放验收每个候选**。

### 里程碑：seed5 9→10 净增 batch 成功
在 9 条保护棱基础上找到净增 batch：
2R U L2 U' 2R'（5 步，单体）→ 重放 **paired=10、center=True、保护组恢复 9/9**。
（另一条 8 步路径：2R F R2 F' U L2 U' 2R'，同样 9→10、保护 9/9。）

### 发现
- seed5（9 条重压）的 9→10 batch 成功，证明共享切片净增机制成立（第一版目标）。

### 进行中 / 卡点
- seed11 7→8 在 depth≤2 穷举(134s)未命中。可能需要：
  ① 加深 depth 但用 target 关系增益筛体控制规模；
  ② 或插入 store（纯外层搬移保护组到 safe 槽）到体序列间；
  ③ 引入纯外层整棱搬移宏。


## ===== ���߽Σ�store-prefix ��ǰ�ݡ����ѽ��seed9 8��9��=====

### ��½
search_store_prefixed_batch��**��ǰ�ݡ�һ���ѹ���������ȫ�ڣ��ٹ� W body W'**��
�� seed9 stuck-at-8 **8��9 �ɹ�**���ط�����һ�£�gate ȫ���㣨paired=9��center=True������ 8/8����
���У�R' U + 2B F' R' F R 2B'��open=2B��store �Σ�R' U��Ϊ�����⣬batch �Σ�2B..2B'�����䣩��

### �Ľ���
- ��ѹ����**������δ�������**����Ϊ�ѹ� 8 �����鲢������Σ���Ŀ�����Ƴ�
  ��ָ�� open/body ���ϵĲ��ֻ�������Ǣ���ֳ���
- ������ԭʼ 8 ���֡�������������ӵ��
- **�ؼ��벻�ǰѲ���ָ��**����һ�������������壬����ָ�� body ��Զ��
  �� 8 ���֣�Ϊ��ָ�� open ��Ӧ�²����ų���

### �½ӿ�
- enumerate_store_paths(cube, group, band, max_depth)��ö��ȫ����ȫ��·��������
  Cube ��֤��
- search_pure_body_batch(..., allowed_open_moves=...)����ֽ�ĳ���� open��
- search_store_prefixed_batch(cube, max_store_depth, max_bodies, pure_limits)��
  ��?����ǰ�ݡ?**true** ���������store_stats�ṹ�֣�StorePrefixStats����
  ���Ѷȡ���prefix/��ȥ�ֺ�̬/��open/������/ʧ��ԭ��/��������

### ���õ����
- seed9 stuck-at-8��JSON �켣+ָ�ƣ�	ests/fixtures/seed9_stuck_at_8.json��
- 	est_edge_batch.py��seed9 �ѱ� 8��9 ���̣� ���أ�+ ���ػ��ң�slow�����̡�
- ȫ�ع� 69 passed ���ٻء�


### seed11 / seed20 �ر��� store-prefix ��δ����
�� seed11��seed20 �ϣ�search_store_prefixed_batch��max_store_depth=4��max_bodies=2����
���� 7��7 �� NO_STORE_PREFIXED_BATCH ��ÿ��~150s��
���� 54 ��ȥ�ֽ�ǰ̬���ף�2B:40 2D:14������� kind �涨�֣����� no_gain/�� 8+�ӻ��
**���ۣ�seed11/20 �ر��� Level 3 ��ǰ�̶� store**��W body1 store1 body2 W'����
�Ѹ��γɵĹ�ϵ��ڲ������ 1 �本。��ǰ̬ store（�ر期��ǰ�貣�Ų�幷 W body W'��
�ڳ���Щ seed ���������㼣��


## ===== 绗笁闃舵缁細Level 3 鎵撳紑鎬?store锛堟悳绱㈡櫤鑳芥€э級=====

### 鏂板锛歴earch_inner_store_batch
缁撴瀯 `W body1 store1 body2 W'`锛歜ody1 鎵撳紑鎬侊紙slice 宸插紑銆佷腑蹇冧笉褰掗潰锛変笅鐢ㄧ函澶栧眰
鎶婃煇涓?*褰撳墠宸查厤缁?*鏁翠綋杞瓨鍒拌鍒囩墖 safe 妲斤紙`require_centers_solved=False`锛夛紝
浣?body2 涓嶆媶瀹冿紝浠庤€岃吘鍑鸿閰嶈嚜鐢卞害銆傛渶鍚庡叧闂?W'锛岀浉瀵?*鍘熷**淇濇姢缁勪簨鍔″師鐐圭湡瀹為獙鏀躲€?
### 鍙傛暟锛堝彲瑁佸壀锛?- `max_store_depth` / `max_bodies_per_open` / `max_store_paths_per_group` / `max_checked`
- `allowed_open_moves`锛氬彧鎼滃彲杈?safe 妲界殑 open锛堢瀛愯瘖鏂樉绀?2B/2D锛夈€?
### 鎼滅储鏅鸿兘鎬у寮?- **鏂扮粍鎴愬紡缁勪紭鍏?*锛氱敤鍧楄韩浠斤紙`middle_piece_id` + `wing_piece_ids`锛夊尯鍒?  銆屽師淇濇姢缁勩€嶄笌銆宐ody1 鏂扮粍鎴愬紡缁勩€嶏紱鏂扮粍姝ｆ槸 Level 3 鎯宠浆鍑烘椿鍔ㄥ尯鐨勫叧绯伙紝鎺掑墠銆?- **body2 鍓灊**锛歜ody2 鑻ヤ笉鎷嗘暎鍒氬瓨鍌ㄧ殑淇濇姢缁勬墠鍊煎緱璇曪紙瀵瑰簲 seed9 鍒嗚В涓繚鎶ょ粍
  涓棿鎬佸彲闄嶅埌 6/8 浣嗗叧闂仮澶嶁€斺€旀晠璇ュ壀鏋濅负鍚彂銆侀潪纭€э級銆?- 澶嶇敤 `b2_open`锛坰tore 鍚?+ body2锛夐伩鍏嶉噸澶嶉噸鏀俱€?
### 缁撴灉锛歴eed11/20 7鈫? 浠嶆湭鍛戒腑
瀵?seed11/20 娴嬭瘯锛坰tore-prefix 鍏虫€佷笌 inner-store 鎵撳紑鎬佸潎璇曪級锛?- store-prefix锛堝叧鎬侊級锛?4 涓幓閲嶅墠缂€鎬侊紙2B:40 / 2D:14锛夛紝best_paired_after=7锛屽叏 no_gain銆?- inner-store 鎵撳紑鎬侊紙max_store_depth=3銆佸叏 open / 鑱氱劍 2B/2D銆乵ax_checked=46080銆?15s锛夛細NO_INNER_STORE_BATCH銆?- inner-store 鎵撳紑鎬侊紙max_store_depth=4锛岃仛鐒?2B/2D锛宮ax_checked=60000銆?64s锛夛細NO_INNER_STORE_BATCH銆?- 鏅鸿兘鎼滅储锛堟柊缁勪紭鍏?+ body2 鍓灊锛宮ax_checked=80000銆?15s锛夛細NO_INNER_STORE_BATCH銆?
**缁撹**锛氬湪褰撳墠 `W body1 store1 body2 W'` 缁撴瀯 + 鐜版湁浣撳簱涓嬶紝seed11/20 鐨?7鈫? 鏄?纭钩鍙版湡锛涙毚鍔?鏅鸿兘鎼滅储绌洪棿杩囧ぇ鏃犳硶绌峰敖锛屼笖璇ョ粨鏋勫眰绾у緢鍙兘涓嶈冻浠ヨ閰嶃€?seed5(9鈫?0 绾綋) 涓?seed9(8鈫? store-prefix) 宸茬ǔ瀹氫氦浠樺苟鏈夋祴璇曪紝鍏朵綑锛坰eed11/20锛?闇€寮曞叆鏇存繁/鏇磋冻鐨勬満鍒讹紙澶?store銆佹洿瓒充綋搴撱€佹垨鎹?slice 杞磋閰嶏級锛屽綋鍓嶅垪涓哄紑鏀鹃毦棰樸€?


## ===== 第四阶段：物理动作语义审计 + 确定性 + 合法 free-slice Gate 1（最新更正）=====

### 1. 更正「内层切片改善配对」的结论（关键纠错）
早期「3X 内层切片能改善配对」的结果**无效**，因为 `3X / 4X / 5X` 在当前 Cube5 引擎中会
**移动 6 个固定面心**（物理动作语义审计证实：`3R/3L/3U/3D/3F/3B/4X/5X` 均移动 4 个固定面心；
仅 `1X` 外层与 `2X` 两层宽转保持不变）。该结果来自**非法动作进入 compact 搜索空间**，
不构成实体 5×5 的可行性证据。正式 free-slice 后续**只使用固定面心不变的 1X/2X 动作**。

- 已从 `compact_state._make_move_tables` 清除 `3X` 内层切片动作，正式搜索动作集固定为 **36 个 1X/2X** 动作。
- 硬测试：`tests/test_move_physical_semantics.py`（断言 1X/2X 与合法切片原语 `2R R'` 等保留固定面心；3X/4X/5X 移动固定面心）。
- 遗留文件 `solver/edge5/free_slice_pair.py`（依赖 3X）已标注 HISTORICAL / INVALID，未被任何正式模块导入。

### 2. 确定性结论
`pair_all_protected` 及宏观配棱器对**相同输入、相同预算、相同宏顺序**是完全确定的：
相同 seed 重放得到相同 `paired` 计数与绝对相同的动作序列（跨进程、跨 `PYTHONHASHSEED` 均一致）。
早期观察到的「同 seed 出现 7~10 波动」来自**不同 scramble 生成器**，而非配棱器本身不确定。

- 硬测试：`tests/test_protected_pairing_determinism.py`（同一轨迹多次调用结果一致）。

### 3. Gate 1 准确后置条件（合法 free-slice 插翼）
从受控分散态（目标中棱 home、目标翼-a 分散到别的工作带槽）出发，单条 `W + outer + W'` 宏
（仅 1X/2X）把目标翼聚到目标中棱槽。后置条件为：

```text
relation >= 2
centers_are_color_solved == True
fixed centers preserved == True
real Cube5 replay matches  （只含 1X/2X，全部合法）
```

- 例：`2F U F' U' 2F'`（rel 聚集、中心归面、固定面心保持）。
- 硬测试：`tests/test_freeslice_legal_gate.py`（4 组 target/entry 组合）。
- 注意：`relation >= 2` 只是「同槽聚合」的抽象分值，**不等于真实配对**（翼朝向仍由真实 `Cube5`
  用 `is_edge_paired` 判定），不能据此宣称完整配成一条 tredge。

### 4. Gate 2 完成（固定工作布局 + 纯外层定位表）
实现 `solver/edge5/freeslice_layout.py`：固定工作槽 = `UF`，入口槽 = `UR`（其右翼位），
并离线预计算**纯外层（仅 1X）定位表**：

- `middle_to_work`: 任一位置的下标 -> 纯外层序列（把该位置的中棱 piece 送入工作槽）。
- `wing_to_entry`: 任一翼位置的下标 -> 纯外层序列（把该位置的翼 piece 送入入口翼位）。

**关键认知（实证）**：在中心归面的 5x5 上，只有外层 1X 动作保持 `centers_are_color_solved`；
所有宽转 2X 都会破坏中心归面。故「定位 setup」只用纯外层 1X（天然保持中心与固定面心），
真正的 free-slice 用 `2X + outer + 2X'`（关切片时恢复中心）。

> **更正（Gate 3 实证，见第 5 节）**：Gate 2 原选自由切片 `2U`，但实证发现 `2U` 的 F-band
> 无法组装 UF 工作槽；**天然自由切片应为 `2F`**（循环 F-band：UF↔FR↔DF↔FL）。Gate 3 已把
> `build_layout()` 默认 `open_move` 由 `"2U"` 改为 `"2F"`（close=`"2F'"`），name 改为 `"uf-f-band"`。

b 定位表以「位置下标」为键（纯外层是纯位置置换、与 piece 身份无关，对任意 piece 均正确）。
硬测试 `tests/test_freeslice_layout_gate.py`（11 项）覆盖：12 中棱起始位、24 翼起始位、
3 个固定背景态、原式与逆式、确定性、全部纯外层且真实 Cube5 重放一致。

### 5. Gate 3 完成（确定性原子插翼 + 自由切片切换 2F + 朝向推迟）
实现 `solver/edge5/atomic_insert.py`：`middle_wing_relation_real`/`insert_wing_atomic`/
`AtomicWingInsertResult` 及关系等级常量（REL_SCATTERED=0/REL_SAME_SLOT=1/REL_COMBO=2/REL_ORIENTED=3）。
组装宏 body 确定为 **`2F U F' U' 2F'`**（rel≥2 位置组合、关切片恢复中心、固定面心保持）。

#### 5.1 自由切片切换为 2F（Gate 3 实证）
Gate 2 原选 `open_move="2U"`，但实证发现 **`2U` 无法组装 UF 工作槽**（F-band 循环为
UF↔UR↔UB↔UL，与 `2F`（UF↔FR↔DF↔FL）不同）；**`2F` 才是 UF 工作槽的天然自由切片**。
Gate 3 已切 `build_layout()` 默认 `open_move="2F"`（close=`"2F'"`），name=`"uf-f-band"`。
重建 `2F` 布局验证：joint_setup coverage **264/288**；staging=(DF,DL,DR,FL,FR,UF,UL,UR)、
storage(safe)=(BL,BR,DB,DF,FL,FR,UB,UF)、entry=UR。

#### 5.2 关系等级语义（edge_relation）
`relation` 是“三块同槽”的抽象分值（类型锚定，**不看朝向**），`is_edge_paired` 才要求
“三块同色对 + 朝向一致”。故插翼宏先保证 **rel=2（同槽位置组合）**，朝向一致性推迟到
rel=3（第二翼到位时的 tredge 完成）。

#### 5.3 朝向一致性推迟决策（用户裁定）
rel=2（中棱+单翼）**无法可靠做到朝向一致**（骨架 526 宏库也无法翻转）；用户裁定：
**保持 rel=2，朝向推迟到 rel=3（完整 tredge，第二翼到位时强制）**。故 rel=2 阶段
`orientation_consistent` 允许为 False。Gate 1 强化为：初始 rel<目标（分散双翼）且成功需
严格真实提升（`controlled_start` 现把**两翼都散置**，初始 n_same==0 → rel<2）。

#### 5.4 能力边界
Gate 1~4 分别证明合法 free-slice 插翼原语存在、固定布局+纯外层定位表可用、**确定性原子
插翼（rel≥2、中心恢复）**可行、**部分组合存储（store+survival+recoverable）**可行；
但**尚未证明**可保护累积到 12 条。后续 Gate 依次为：
Gate 5 完整配成一条 → Gate 6 保护式梯度 1→2→4→6→8→10 →
Gate 7 最后两棱与奇偶。

### 6. Gate 4 完成（部分组合存储 store + survival only）
实现 `solver/edge5/store_partial.py`：`store_partial_combo`/`combo_survives_free_slice`/
`safe_untouched_slots`/`StorePartialResult` 及错误码。freeslice_layout 新增
`relocate_middle_to_pos`（把中棱 piece 移到任意目标中棱位的纯外层 BFS）。

#### 6.1 关键实证
- **纯外层单步永远把同槽「中棱+翼」带在一起**（同槽保持不变）→ 适合整体搬运部分组合。
- `insert_wing_atomic` 产出的组合落在**入口槽 UR**；单步 `R` 即可把它搬到 `BR`（safe-untouched，
  不被 2F 触碰），组合 rel≥2、中心/固定面心均保持。（`U'` 可搬到 `UB`。）
- **存储目标槽 = storage_slots − staging_slots**（= {BL,BR,DB,UB}），即开/关切片
  `2F` 都完全保留且不触碰的槽。

#### 6.2 Gate 4 三件套（用户裁定 store + survival only）
1. **store**：`store_partial_combo` 用纯外层把组合整体搬到 safe-untouched 槽，验证
   rel≥2 且同槽、中心归面、6 固定面心保持、真实重放一致、不改写输入、确定性。
2. **survival**：`combo_survives_free_slice` 证明该存储组合在「对其它 piece 做一次
   free-slice 开/关循环（open+outer+close）」后仍存活（rel≥2 且同槽）——因目标槽不被
   `2F` 触碰而天然成立。
3. **recoverable**：`relocate_middle_to_pos` 能把组合整体搬回工作带（第一关系可恢复）。

#### 6.3 明确留给 Gate 5
「同一 tredge 的第二翼插入（把存储组的**中棱**带回工作槽并插翼-B）会**拆散**部分组合
（seed 11 实测 relA 降到 0）」，且部分 seed（5）命中结构性 `JOINT_SETUP_UNREACHABLE`。
这是 Gate 5「完整配成一条三块棱」的核心难题，Gate 4 不处理。
Gate 4 测试：`tests/test_freeslice_store_partial_gate.py`（30 passed, 1 skipped）。


### 6.5 Gate 5 完成（完整配成一条 + 完成类型分类）
实现 `solver/edge5/complete_tredge.py`：`completion_goal_states`/`find_partial_wing_setup`/
`complete_tredge`/`describe_partial`/`TredgeCompletionKind`/`CompleteTredgeResult` 及错误码。

#### 6.5.1 scatter 根因 = 目标槽枚举不完整（已解决）
`completion_goal_states` 原先只枚举 {UF,BL,BR,DB,UB} 5 个 partial_slot，导致 `NO_GOAL_COMPLETED`
（18 个 seed）。展开到**全部 12 逻辑槽 × 24 翼入口**后：
- `NO_GOAL_COMPLETED` **18 → 0**；
- seed 11（原 NO_GOAL）现在在 **UL** 槽配齐（旧枚举不含 UL）；
- 可评估样本（有部分组合）成功率 30 → 40 / 59。

#### 6.5.2 完成类型分类（`TredgeCompletionKind`）
区分 `VALID`（三块同槽 + 朝向一致，可注册保护组）/ `FLIPPED`（位置装配完成但整体翻转，
位置动作保留、交 Gate 5b）/ `POSITIONAL_ONLY` / `NOT_COMPLETED`。翻转组**不得**直接注册为
`ProtectedTredge`（`is_edge_paired` 要求朝向一致），需 `FlippedTredge` 独立类型，待
Gate 5b 修正后才升级为 `ProtectedTredge`。

#### 6.5.3 能否用现有单装配/宏库修正翻转？（已证不能）
对翻转样本，在任何合法 free-slice 轴 (2F/2B/2R/2L/2U/2D) × 任何插翼本体 × 任何槽/入口下，
单次装配都得到翻转结果（41 次"同槽"命中全部 `is_edge_paired==False`）；单次 free-slice 环
（2U/2R 带，≤3 外层）亦不能翻转；现有 `build_macro_index(3)`（526 宏，len≤5）也无法修正。

#### 6.5.4 翻转签名统一（`SINGLE_TREDGE_FLIP`）
`flip_signature` 把翻转棱共轭归一化到槽 frame：edge_type（当前均为 {G,W}）+ 每片相对槽两面的
朝向符号。全部 14 个翻转 sample 归一化为**恰好两个等价模式** `-++` 与 `+--`（绕槽轴 180° 旋转
共轭），均表示**中棱朝向与两翼相反**。⇒ 需要一个**参数化双棱宏（含旋转共轭）**即可修正全部。
**严谨表述**：这是"在单 tredge 装配 + 中心保持宏空间内无法修正"，并非已从完整合法移动群
群论证明的不可修正奇偶；需借用第二条未配对棱（缓冲棱）做双棱修正（Gate 5b），真正无缓冲的
最后两棱奇偶留 Gate 7。

#### 6.5.5 冻结的翻转 fixtures
`tests/fixtures/edge5/gate5b/flip_seed{7,19,23,2,4,51}.json`：覆盖 `UR`/`DF`/`UL` 输出槽、
`FLIP_FIX_UNAVAILABLE`/`FLIP_FIX_FAILED`、两种模式；含完整生成轨迹（scramble/center/gate3/
gate4/setup/insert）+ state_fingerprint，重建一致。Gate 5 测试：
`tests/test_freeslice_complete_tredge_gate.py`。

Gate 5 提交：`3c6e101`（全槽 scatter 修复 + core）、`875370f`（完成类型分类）。


### 7. 关于「9→12 硬不变量」的严谨化
「9→12 无法跨越」**并非已被证明的数学硬不变量**。更严谨表述：
在当前合法动作集、宏库与搜索预算下，最后 3~5 条需要非单调、多步穿谷及专用最后两棱处理；
现有贪婪、beam 与双向 BFS 未能稳定跨越。除非给出群论证明，否则不宣称其为数学上的硬不变量。

