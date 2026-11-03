"""Original learning routes and mechanically verified examples.

All teaching content is displayed inside the application.
"""
from dataclasses import dataclass
from candidate_puzzles import BY_KIND
from demo.irregular_cases import text


@dataclass(frozen=True)
class Tutorial:
    intro: str
    goals: tuple


def tutorial(kind):
    entry=BY_KIND[kind];kind=entry.kind;m=entry.mechanism
    if kind=='lanlan_master_clover':return Tutorial('双棱花的常规双层模式：十二根棱轴，每根分大层和小层，均转180°。六面各20片；中心小方块与角部小方块属于同一连体实体，不能独立改变位置。本模式的新增弧线依照片重建，尚未认证变形混转的内部切面。',(
        '辨认12个双色大棱、48片小叶片和8个连体角；同一连体角的6个贴片一起确定其颜色和方向。',
        '逐面选色并连续填入120片。中心与角部必须符合连体关系，撤销与配色设置沿用其他魔方的操作。',
        '大层带动连体角和相邻叶片；小层保留连体角，只转大棱及靠近它的小叶片。先按图示匹配三片小叶片再执行循环。',
        '常规状态求解从当前录入计算，不读取打乱记录。变形实物还需等待混转机构完成，不能按软件内部回放就认定实物已验证。'))
    if kind=='lanlan_butterflower':return Tutorial('蝶恋花使用半径1.0的四叶草棱切与浅角切。常规操作为棱转180°、角转120°；换瓣时先将相邻棱转到切线对齐，J约70.529°，补角约109.471°，方向由阻挡检查决定。六面各20片，共120片；一个完整双色块两侧的颜色应一起核对。',(
        '辨认36个双色块、48个单色块；同一块上两种颜色随整块转动。',
        '在三维模型上选色后连续填色，左右箭头逐面观察，撤销保留其他已录入颜色。',
        '变形状态先复形，再整理双色块和角部相关块，最后用单色块循环处理剩余色面。每一步都检查完整实体，不能将约120°的目测角度当作换瓣位置。',
        '求解依据当前颜色与块位计算，不读取打乱历史；不可见的内部材料由外部形状补全并反向回放验证。困难复形可能搜索未完成，此时保留录入。最后核对六面120片。'))
    if kind=='kairis_star_finder':return Tutorial('星寻足球的标准120°模式：三十二面、二十根六边形转轴，共252片。六边形各分六个三角片，五边形各十一片。求解依次处理普通棱、双色翼块、单色三角块和中央面；不读取打乱历史。部分转动及实物内轨尚未验收。',(
        '逐面填色，跨面的双色块需同时核对两侧颜色。',
        '按图示工作位先调棱的位置，成对翻转，再整理翼块。',
        '使用对应轨道的三块循环处理三角片和中央面，完整撤回设置。',
        '逐面验收252片颜色；完整还原实例只适用于它显示的起始状态。'))
    if kind=='lanlan_flower_copter':return Tutorial('花瓣魔方按用户图纸重建圆弧。除棱180°、角120°的常规转动，也支持约70.529°、109.471°的棱准备和60°角转形成突出外形；每一步按完整材料检查阻挡。',(
        '按完整实体辨认八个三色角、十二个双色块和七十二个单色块。一个块的各面分别填色，显示三角网格不是额外色片。',
        '直接从完整配色的模型开始，使用拧动、形变打乱、撤销和重置。没有手工摆块和颜色录入入口。',
        '在转角选项中切换常规动作和形变准备。只有整块避开切面才允许转动，受阻时先撤回或调整邻层。',
        '求解先恢复外形，再整理颜色，不读取打乱历史。三单色块循环只处理图示工作位；复杂复形仍可能超时，状态会保留。'))
    if kind=='lanlan_clover_pyraminx':return Tutorial('以下是十二偏轴去角四面体的内部研究模型，并非已经核对通过的蓝蓝三叶草金字塔。当前截角外壳与实物照片存在明显差别，因此没有放进正式目录；这些练习只验证研究模型。',(
        '四个参考面各十三片，共五十二个色面。辨认十八个双色块、十二个单色块与带四个中央面的固定核心；没有可单独拧动的尖角。',
        '在三维模型上连续填色。需要调整形状时选完整实体，颜色随块移动；确认才应用草稿，取消和撤销保留原来的输入。',
        '两种基准转角约为 67.115° 和 146.443°。每次层转都检查整块是否跨过切面；执行完整的准备、交换与撤回，不能强拧被挡的层。',
        '对齐后用三双色块循环整理图示工作位，再核对四面颜色和形状。求解基于已验证的闭合动作，复杂变形或动作群外的状态仍可能未完成；失败保留输入，不表示实物无解。'))
    if kind=='lanlan_hexagram':return Tutorial('六角星金字塔使用十二根偏轴，两种基准转角约为 67.115° 和 146.443°。它不是普通金字塔，也不是只有三根直角轴的叶片四面体。外壳按四球交集建立曲面近似，实物尺寸与内轨尚待核对。',(
        '四个面各十六片，共六十四个色面。辨认四个三色角、十八个双色块、十二个单色块与带四个中央面的固定核心；曲面显示网格不增加可选小片。',
        '先观察外形与偏轴的对齐。姿态编辑必须选整块，确认前只改变草稿；层转则检查全部材料，受阻时不强拧。',
        '用完整闭合工具恢复外形并搬动块组。两种角度的顺序与工作轴都有要求，不要把双鱼座的配色或块数照搬过来。',
        '外形对齐后核对四面颜色，双色循环可整理图示三个工作块。复杂手动变形仍可能搜索未完成，失败保留输入，不能据此认定实物无解。'))
    if kind=='lanlan_pisces':return Tutorial('双鱼座沿十二根偏轴转动，不能把它当普通斜转魔方。两种基准角约为 67.115° 和 146.443°，单次转动通常会改变外形。当前为分面近似外壳，曲面尺寸与实物内轨尚待核对。',(
        '按完整块辨认四个三色角、十二个双色块与十八个单色块；六个中央色面连在同一固定核心上。共六十个色面，外壳的显示三角网格不增加可选色片。',
        '先核对外形和方向。选中整块后，在形状草稿中调整，颜色随块一起移动；确认才应用，取消保持原输入。物理层转会检查整个实体是否跨过切面。',
        '匹配闭合工具的工作轴后，完整执行准备、交换与撤回。只完成前半段可能仍然变形；不同块组会同时变化，不能把整套工具当一次直接角转。',
        '复形后核对全部六面颜色。三叶片工具只在完整执行后保护其他块；复杂手动变形使用有限时搜索，超时表示本次搜索未完成，不能判定实物无解。'))
    if kind=='mf8_suncube_2':return Tutorial('太阳二号是深切棱转机构，十二个棱转层按 180° 闭合。它与普通 Sun Cube 的面转机构不同；部分棱转可改变外形并打开其他转层。',(
        '六面各二十五片，共一百五十片。模型含一百二十二个可见实体；双色棱、三色角与各类单色小片必须按完整实体录入。',
        '先恢复立方外形。部分准备角 J 约为 70.529°，另一方向为 109.471°；每次转整层前检查所有实体是否避开切面。',
        '组合工具通过部分棱转、半转另一层、再撤回准备来搬动块组。不同大小和轨道的同色小片不能互相冒充，求解需校验完整配色。',
        '检查六面颜色和外形同时完成。当前显示为平面几何模型；复杂多次变形仍可能复形超时，失败保留输入，不能认定实物无解。'))
    if kind=='mf8_twins':return Tutorial('双子星按 pCubes 的 Skewby Twins 分块与动作核对，使用平面切割和倒角几何近似外壳。每面32片、共192片，内外小片可独立交换；支持60°角转及约54.736°、70.529°等棱准备角。',(
        '打开即是完整配色模型，直接拧动或形变打乱。颜色随整块移动，不提供手工摆块和填色。',
        '常规棱半转和角120°用于闭合整理；60°角转和棱准备会改变外形。被完整实体挡住的转层不能强拧。',
        '分别练习三棱准备后转角、两端准备后转棱，再逆序撤回。注意相邻内外片能成为不同颜色，不能把它们合成同色一对。练习只还原展示的起始状态。',
        '整体求解先复形再整理颜色，依据当前状态计算，不读取打乱历史。复杂状态仍可能超时；失败保留模型，不表示实物无解。'))
    if kind=='lanlan_comet_physical':return Tutorial('蓝蓝 Crazy Comet：十二根面轴半转 180°，部分转动能交换翼块并改变外形。十二个大菱色区之外，还有二十四片金色小面，它们跟随转帽移动，并不是固定装饰。',(
        '逐面填入十二色各十一片和金色二十四片，共一百五十六片。一个实体上的不同色面分别填色；金色面和它相邻的两个颜色面属于同一个实体。',
        '先恢复外形。J 约为 70.529°；另一个对齐角为 180°−J。调整形状时选择整块，颜色随块移动，确认前不会改动原输入。',
        '区分十二个单色转帽、二十四个双色翼块、二十四个带金面的三色块和八个普通三色角。混转可交换翼块位置，不能只按普通立方体的二十四种方向检查。',
        '最后检查全部十二个菱色区与金色小面。复杂变形使用有限时复形搜索，未完成会保留输入；软件几何验证不代替实物机构和尺寸验收。'))
    if kind=='planar_rhombic_12':return Tutorial('本款是十二轴菱形体的平面切割研究模型，常规面转为 180°。部分转动可以解锁相邻轴并改变外形；它与 Rua 的切面深度、块数和混转规则不同，也不是用户照片里的蓝蓝十二轴十二面体。',(
        '在三维模型逐面连续上色，每面十一片、共一百三十二片；一个实体的多面颜色分别填写。需要变形时用“调整形状”，确认前只修改草稿。',
        '先检查每个转面的对齐。J 表示约 70.529°；准备两个相邻转面后才能转动某些被阻挡的层，不能看到一个色片就把它单独拧走。',
        '对齐后按单色、双色、三色与四色完整块整理颜色。重复的单色叶片不需要隐藏编号，固定中央面也不能和可移动叶片混为一类。',
        '最后核对菱形十二面体外形与全部颜色。研究模型尚未对应到确切实物；困难变形仍可能复形超时，失败保留输入，不能据此断言实物无解。'))
    if kind=='lanlan_curvy_copter':return Tutorial('魔蝶沿十二条棱轴转动。常规半转为 180°；部分转动会让相邻轴解锁，也可能产生突出块和阻挡。软件曲面按球切近似显示。',(
        '在三维模型上连续填色；变形时用“调整形状”选中整块并修改块位和方向，已有颜色随块移动，确认前不会改动输入。',
        '先恢复立方外形。J 表示约 70.529° 的对齐角，另一基准角是 180°−J；只有完整实体不跨越转动切面时才允许层转。',
        '外形完成后整理棱载体朝向、角块和叶片。同色叶片可互换，录入不需要填写它们的隐藏编号；跨组叶片可用完整混转准备再撤回复形。',
        '最后检查六面全部七十二片、立方外形和棱载体两色。复杂变形复形仍可能搜索超时；超时保留输入，不能据此断言实物无解。'))
    if kind=='megaminx_ball':return Tutorial('十二根五重转轴，每次转 72°；配色却是二十个三角区域。二十个角块各为单色，三十条棱各为双色，十二个转帽中央各有五种颜色。',(
        '按三角色区逐面录入，每色七片，共一百四十片。三角色区的中心不是转轴；实际转轴穿过五色转帽中央。',
        '先按双色棱和单色角的位置整理外围。角块是完整的弧边三角面，不需要录入普通五魔的三色角朝向。',
        '外围完成后检查十二个转帽的五色顺序；中央配色的旋转也需要还原，不能套用普通五魔单色中心的完成条件。',
        '核对二十个三角色区及一百四十片颜色。示例交换子展示相邻转轴的作用，完整解法还会修正转帽中央的方向。'))
    if kind=='aj_curvy_dinominx_4':return Tutorial('二十根顶角轴，各有深、浅两层，每次转 120°；十二个中央色面固定，每面共二十六片。它不是普通四阶五魔方。',(
        '先按固定中央颜色建立十二面配色，辨认同一顶角的内角环和浅角帽；逐面录入每一片实际颜色。',
        '先定向内角环，再定向外角帽。深层同时带动角帽，先做外帽会在内角环调整时被打乱。',
        '整理三十个普通双色棱，位置完成后核对翻棱。两条棱同时翻转时使用图示工具，其他未完成翼棱会随动。',
        '最后整理六十个翼棱。翼棱循环保护已经完成的角环、角帽与普通棱；完整回放后逐面核对。'))
    if kind=='mf8_bauhinia_minx':return Tutorial('紫荆花有20根顶角轴、192片颜色。常规转动为120°；约44.4775°的准备可以解锁相邻重叠转层，产生混转形变，每一步都检查整块及隐藏材料。求解先复形再整理颜色，困难形变仍可能超时。',(
        '先辨认顶角周围的三个面，每次围绕顶角轴转 120°；五边形正面不是转轴。',
        '先排列三十条双色棱，再处理成对翻转的棱。棱的位置正确并不代表两侧颜色朝向也正确。',
        '按类型分开处理大叶片、中央面和小三角，使用对应循环；同色但不同轨道的小块不能互换。',
        '最后逐面核对每面的十六个色面；本页公式只针对所示工作位，准备动作执行后要逆序撤回。'))
    if kind=='yeet_ball':return Tutorial('球形枫叶机构，四个三色转角与六片单色叶片；四根斜轴每次转 120°。外形是球，机构不是普通三阶。',(
        '先认清四个活动三色角和它们周围的叶片。左右箭头只改变观察面，不改变块位。',
        '按三色关系调整四个转角。先观察一次正转与反转，记下相邻叶片的循环方向。',
        '将剩余叶片设置到同一个工作区，使用三叶片循环，再逆序撤回设置。',
        '沿球面核对六个颜色区域，四角与六叶片应同时正确；不要只检查正面。'))
    if kind=='caneball_4':return Tutorial('四阶立方机构、八色分区的多面球。每个三角尖部、棱条和小方片只有一种外观颜色。',(
        '沿切线区分机构角、翼棱和中心；八色按八个空间分区分配，不能按六面普通四阶直接填色。',
        '先用每块的形状与位置组织机械中心，再配翼棱；同色但不同轨道的块不能直接互换。',
        '按四阶核心还原；单色三角角块的三种不可见转向由校验器匹配，不要求录入隐藏编号。',
        '检查八个同色分区以及全部相邻接缝，机械中心、翼棱和角的外壳都应连成球体。'))
    if kind in ('rhombic_3','rhombic_4','rhombic_mask_4'):
        high=entry.n==4
        return Tutorial(f'{entry.n} 阶立方机构，外壳由十二个菱面构成。'+
            ('截去的六个尖部用金色方块标记。' if kind=='rhombic_mask_4' else ''),(
            '沿切线找机构轴：菱面中心的大色块属于机构棱，不能把十二个菱面当成十二个可转面。',
            ('先组成六组机械中心；观察每块的全部色面和接缝。' if high else '先配好一层机构角和棱，用相邻色面接缝核对朝向。'),
            ('配齐十二组翼棱，再完成降阶机构；单独内切片与双层宽转要分清。' if high else '继续完成中层与末层；多色机械中心的方向需要最后单独检查。'),
            '逐面检查菱面和尖部，整段工具结束后应保持其他已完成块；配色设置只改变显示配色。'))
    if kind=='skewb_rhombic':return Tutorial('四轴斜转核心，八个三色块和六个四色块，共十四块。菱面上的四块通过整个机构联动。',(
        '先找一个三色块，观察它与相邻四色块的配色；一张正面不足以确定整块。',
        '以一个三色块为基准整理其余三色块，使用 120°斜转，保持参照关系。',
        '把四色块送回配套位置，再检查它们在菱面上的方向。设置动作与撤回动作要成对执行。',
        '核对十二个菱面，每个物理块的全部贴片都应连续，不把同一块拆开填成两块。'))
    if kind=='jewel_fto':return Tutorial('八个六边形面按 FTO 机构转动 120°；六个金色方形是截平的角，不是独立转盘。',(
        '固定八个面色的邻接参照；金色角不提供原 FTO 的四色朝向信息。',
        '先整理中心三角片，再按两面配色识别十二条棱，保留未完成面作工作区。',
        '使用相邻面设置与撤回整理余下中心和棱。金色角的位置不可仅凭颜色指定。',
        '检查八面及全部接缝；只有一对棱看似互换时，先重新核对整体配色参照。'))
    if kind=='rua':return Tutorial('十二个菱面常规半转180°，约70.5288°及109.4712°的准备可改变外形并解锁其他转层。八个三色角、六个四色角和二十四个单面块分属不同轨道；整块和隐藏材料共同决定是否受阻。',(
        '按整块贴片数区分三色角、四色角与三角单面块；它不是普通十二面五魔。',
        '建立相邻色面参照后整理三色角，再处理四色角的位置和方向。',
        '把未完成三角块设置到同轨道工作位，利用相邻半转及其撤回整理。',
        '逐面检查大四边形与四个小三角，不把分属不同轨道的同色块直接互换。'))
    if kind=='helicopter_14':return Tutorial('十四面直升机有十二条原棱轴，常规半转180°。约70.5288°和109.4712°的准备能解锁混转、产生形变。六个方形面各有四个三角片，八个截角共享一种金色。',(
        '按活动切缝选棱轴；金色三角面没有单独的面转按钮。',
        '建立六面颜色的参照，把方形面的三角块按其合法轨道分组。',
        '在相邻棱轴之间做设置、局部交换与撤回；比较整段动作后的效果。',
        '六个方形面同色，八个金色截角也应回到对应轮廓。金色块之间不要求不可见编号。'))
    if kind=='time_machine':return Tutorial('二阶角块核心配上六个独立十二格数字环。颜色和数字共同决定目标。',(
        '区分内侧角块与外侧数字扇片，固定上下前后颜色参照。',
        '先完成二阶角块。角块层每次转九十度，会带动相邻数字环的一半。',
        '数字环每格三十度；用准备、三循环和撤回准备动作整理颜色与数字。',
        '逐面检查每个颜色的十二个数字顺序，以及内侧四个角面的颜色。'))
    if m=='dial_beans':return Tutorial('双面魔豆：每圈十颗珠子，每圈同色即完成，不限定各圈颜色的位置。滚珠、翻瓣与中央转盘是三种不同动作。',(
        '固定正反面和瓣的位置，逐圈录入颜色；两侧都要观察。',
        '沿单圈滚动珠子，外瓣翻转一百八十度交换两侧的五颗珠子。',
        '正面、背面中央盘独立转动，只把本面每瓣内侧的三颗珠子送到邻瓣；另一面与两颗过渡珠保持。',
        '选择最接近当前状态的环色分配，用八步三珠循环整理余珠；两侧每圈同色即可停止。'))
    if m=='extended':
        from cube.letter_cube import EXTENSIONS
        return Tutorial(f'{entry.name}：三阶核心加 {len(EXTENSIONS[kind])} 个方向的扩展层。先辨认三阶核心，再处理扩展块。',(
            '观察三阶核心的角、棱与中心；扩展中心与核心相连，不能把外观格数当阶数。',
            '先对齐需要转动的扩展平面。转层必须完整，不能穿过尚未对齐的扩展块。',
            '还原三阶核心时，记录扩展层的配色与朝向；三阶核心完成不代表外壳已经完成。',
            '通过准备动作、交换与撤回准备动作整理扩展块，最后检查全部外伸面与轮廓。'))
    if m=='siamese':
        overlap='1×1×3' if kind.endswith('_a') else '2×1×3'
        return Tutorial(f'{entry.name} 共享 {overlap} 连接块。两侧各有核心，不能切开共享块。',(
            '先找到两个核心和共同连接区，固定连接区作为观察参照。',
            '只使用当前核心不碰连接区的转层；两侧的同名转面需要分开辨认。',
            '逐侧整理角块与棱块，使用受限转层的准备动作把目标送到可操作位置。',
            '检查第二侧时同时核对第一侧与连接区。A 型与 B 型的可转层不同。'))
    if kind=='trajber':return Tutorial('四阶核心、八面体外壳；尖部并不是三阶固定面心。',(
        '辨认四阶中心组、翼棱和机构角块，按真实内层与外层选轴。',
        '拼合六组机械中心；最后两组用机构角块的配色校对位置，避免中心方案错配。',
        '配齐各组翼棱，再按降阶后的三阶机构还原，保留完整八面体外壳观察。',
        '检查四阶特殊情况及中心方向；最终八面和尖部都应接齐。'))
    if kind.startswith('dodecahedron_'):
        order=entry.n
        return Tutorial(f'十二面体外壳承载普通 {order} 阶机构；十二个外观面不是十二个转轴。',(
            '沿切缝辨认机构角块'+('、棱块和中心。' if order==3 else '，同一个角块可能承载多个外观色面。'),
            '以相邻外观面的接缝为参照完成第一层角块，不仅比较单张贴片颜色。',
            '按对应机构整理'+('中层棱和末层棱角。' if order==3 else '末层角的位置与方向。'),
            '核对十二面体轮廓与每条公共色边'+('，必要时修正机械中心的朝向。' if order==3 else '。')))
    if kind=='pyraminx_diamond':return Tutorial('六个四色尖块与八个中央三角面，最小角转为 90°。',(
        '辨认带多色的尖块和中央三角面，选择一个尖块作为配色参照。',
        '先校对尖块的朝向；转尖块时相邻中央三角面也会一起移动。',
        '把中央三角面送到所属的三组相邻颜色之间，处理剩余循环。',
        '检查六个尖块及八个面；不要使用 Skewb Diamond 的 120°转法。'))
    if kind=='pyraminx_crystal':return Tutorial('深切十二面体：20 个角与 30 条棱，面转 72°。',(
        '以一个角为起点，按相邻配色完成首面五个角的位置与方向。',
        '插入首面棱块，逐步完成相邻层；每次插入后检查已完成区域。',
        '整理末层角，再排列末层棱，保留用于准备动作的未完成区域。',
        '最后修正棱朝向。成对反向的棱需要保留两次设置动作之间的对应关系。'))
    if kind=='starminx_i':return Tutorial('Starminx I 是面转72°的深切十二面体，双色棱与单色块分属不同轨道。',(
        '先观察一个五边形轴的移动范围；深切会同时影响相邻面，按高亮的整层操作。',
        '建立十二色相邻关系，先整理双色棱的位置与方向，保留未完成侧作为准备区。',
        '区分各组单色块，用本例循环工具整理；相同颜色不代表同一种形状或轨道。',
        '完整执行设置、循环和逆设置，最后逐面核对颜色及所有切缝。'))
    if kind=='rediminx':return Tutorial('Rediminx 使用顶点转120°的十二面体机构，外表面中央凸起。',(
        '观察转动一个顶点时的棱循环，确认与实物是同一种角转机构。',
        '围绕一个面完成棱，再扩展到相邻面，保留一块未完成区域作缓冲。',
        '用两相邻顶点的交换子处理局部循环；准备动作结束后要原路撤回。',
        '处理末面棱的排列与方向，并检查固定中心和顶点配色。'))
    if kind in ('pentultimate','master_pentultimate'):
        master=kind.startswith('master')
        return Tutorial(('多层深切' if master else '过核心深切')+'十二面体。每次转动影响多个外观面。',(
            '观察深切层的实际移动范围，先确认每个转轴的层号。',
            '选定参考配色，分辨'+('中心、内棱及外围块的独立轨道。' if master else '深切后移动的块，保持整体配色关系。'),
            '在未完成区域设置目标，用局部交换与其逆操作保留已完成部分。',
            '逐轨道核对剩余排列与朝向；下方完整回放会从独立合法打乱生成可核验解法。'))
    if m=='dogic':
        twenty=kind=='dogic_20'
        return Tutorial(('20 色版与 12 色版采用同一套切割、八十个实体块和十二根转轴，只将二十个三角面各涂一种颜色。中央三块嵌色同色，仍能看到 Y 形塑料间隔。' if twenty else
                         '12 色版与 20 色版切割相同；中央三色三角形是一块，三块嵌色之间可见 Y 形塑料，但不能分别转动。顶角按周围中央颜色配对。'),(
            '分别观察小顶角转动与包含五个完整面的深层转动，二者均为 72°。',
            '逐面整理中央块和相邻小三角'+('，按面色区分目标。' if twenty else '，先匹配顶角与中央三色块的相邻关系。'),
            '保留未完成的面作为缓冲，使用准备动作和局部循环整理余块。',
            '核对'+('20 个完整单色面。' if twenty else '12 组顶角颜色与所有中央三色块的朝向。')))
    if kind=='container':return Tutorial('魔盒使用 Skewb 核心；侧面中心的方向也属于还原目标。',(
        '以白／黄中心定位，先完成同一侧的四角，并检查相邻角的颜色关系。',
        '把六个中心送回正确位置；剩一对中心时要引入另一对共同处理。',
        '调整另一侧角的朝向，检查同色角有没有放到错误的高度或位置。',
        '修正四个侧面中心方向，最终同时恢复配色和长方体外形。'))
    if m=='cheese':return Tutorial(f'{entry.n} 层圆饼，每层六瓣；水平层转 60°，半盘翻转 180°。',(
        '先辨认上下层与侧面的配色；它不是早期只有一层的 Rubik’s Cheese。',
        '用半盘翻转把瓣块送入正确水平层'+('，先处理中央层再检查顶底。' if entry.n==3 else '，同时观察顶底颜色。'),
        '旋转水平层调整瓣块的相邻关系，再用设置—翻转—撤回整理剩余块。',
        '检查最后一对瓣块、每层侧色顺序和顶底配色，不能只看轮廓。'))
    if kind=='masterball':return Tutorial('八条经线、四个纬层；纬层转 45°，半球翻转 180°。',(
        '用半球翻转配合纬层移动，把所有块送入所属纬层。',
        '在一对相对纬层中设置相邻交换，先完成其中一层再处理另一层。',
        '用同样方式处理剩余两纬层；暂时移开的块要随准备动作撤回。',
        '对齐四个纬层，检查每条经线的颜色及图案方向。'))
    if m=='prism':return Tutorial(f'{entry.name}：{entry.n} 个水平层；顶底转 72°，侧向半转 180°。',(
        '分别观察水平转层与侧向翻转，核对实物的层数及侧面切线。',
        '先把块分回所属的水平轨道'+('，整理内部中心条。' if entry.n>=4 else '。'),
        '按相邻侧色组合块，用准备动作和局部循环整理未完成区域。',
        '处理末层排列并核对上下五边形及全部侧面；'+('Professor 还要检查两种侧向切深。' if entry.n==5 else '不套用圆圈或星形柱体的额外转法。')))
    if kind=='master_brilic':return Tutorial('Crystal 深切机构增加浅层，需分别处理中心、组合棱与降阶核心。',(
        '先按 Brilic／Crystal 的邻接关系整理中心。',
        '将相同配色的边块组合为三块一组，检查组合方向。',
        '组合完成后按五魔核心还原，避免拆开已经完成的组合。',
        '检查浮动块及剩余方向；完整状态回放会单独核验额外轨道。'))
    if kind=='blanker':return Tutorial('外观像白色三阶，实际是八个不等形角块的二阶机构。',(
        '沿真实活动缝辨认八块；白面上的装饰线不产生额外可转小块。',
        '以大块与小块的高度为参照，配齐第一层轮廓。',
        '按二阶方式排列其余角块，再调整朝向；操作中外形会继续变化。',
        '检查六面平整、活动缝闭合，不用无法观察的内部虚拟颜色判断。'))
    if m=='mirror_minx':
        corner_only=entry.n==2
        return Tutorial('用高低、轮廓和接缝代替颜色识别五魔机构。',(
            '找到高度与邻接形状可辨认的参考角，固定观察方向。',
            '逐个配齐首面五角'+('。本型号只有角块，不安排棱和中心步骤。' if corner_only else '，随后插入配套棱块并完成相邻区域。'),
            '排列末面的角'+('，再调整角朝向。' if corner_only else '与棱，保留未完成面作缓冲。'),
            '核对全壳高低与相邻边缘'+('。' if corner_only else '，最后检查中心的几何朝向。')))
    raise KeyError(kind)


def lessons(kind,n):
    """Prepared mechanical exercises, explicitly distinct from a full solve.

    Each exercise records its actual starting state and independently replays
    the displayed restoration. A shape-changing turn is never assumed legal.
    """
    from demo.expanded_support import make_cube,legal_moves
    from demo.solutions import inverse_demo_move
    entry=BY_KIND[kind];kind=entry.kind;guide=tutorial(kind);base=make_cube(kind,n)
    options=legal_moves(base)
    first=options[0]
    second=next((m for m in options if getattr(m,'axis',m)!=getattr(first,'axis',first)),options[-1])
    if kind in ('lanlan_flower_copter','lanlan_butterflower'):second=next(m for m in options if m.axis>=12)
    if kind=='lanlan_master_clover':second=next(m for m in options if m.layer==1)
    if entry.mechanism=='extended':
        first=next(m for m in options if m.layer==0)
        second=next(m for m in options if m.layer==1)
    elif hasattr(base,'geometry'):
        g=base.geometry
        second=next((m for m in options if g.spec.order(m.axis)!=g.spec.order(first.axis)),second)
    def exercise(zh,en,forward,tip):
        initial=base.clone()
        for move in forward:initial.apply_move(move)
        word=tuple(inverse_demo_move(m,base) for m in reversed(forward))
        replay=initial.clone()
        for move in word:replay.apply_move(move)
        if not replay.is_solved():raise ValueError('Teaching exercise did not restore its model')
        if isinstance(first,str):notation=' '.join(word)
        else:
            from demo.irregular_cases import token
            g=base.geometry
            notation='  '.join(token(m,g.spec) for m in word)
        return {'name':text(zh,en),'initial':initial,'moves':word,'show_all':True,
                'text':notation,'tip':text(tip,'Compare this prepared example with the learning route. Match its start before following the moves.'),
                'teaching_kind':'mechanics','reference_ids':()}
    cases=[exercise('练习一：辨认第一类转层','Exercise 1: identify the first turn',(first,),guide.goals[0]),
           exercise('练习二：辨认另一类转层','Exercise 2: identify another turn',(second,),guide.goals[1])]
    if kind=='helicopter_14':
        from cube.helicopter_14_aligned import generators
        exchange=next(w for p,w in generators() if len(w)==5)
        cases.append(exercise('混转准备与复形','Preparation and shape restoration',exchange[:2],
            '先把两端棱转到切线对齐位置，观察突出形状，再逆序撤回。金色截角跟随实体移动，没有单独的金色面转。'))
    if kind=='lanlan_butterflower':
        from cube.butterflower_aligned import generators
        exchange=generators()[20][1]
        cases.append(exercise('换瓣准备与复形','Petal alignment and shape restoration',exchange[:2],
            '两根相邻棱分别到达切线对齐位置，观察突出形状；逆序撤回即可复形，不能用目测120°强转。'))
        cases.append(exercise('完整换瓣与撤回','Petal exchange and undo',exchange,
            '按准备、棱半转、逆序撤回的整段动作交换花瓣。每一步由完整实体检查阻挡，角转仍为120°。'))
    if kind in ('bean_6','bean_10'):
        from cube.dial_beans import petals
        from cube.polyhedral import Move
        p=petals(kind)
        for side in range(2):
            axis=3*p+side
            cases.append(exercise('正面中央盘' if side==0 else '背面中央盘',
                'Front central rotor' if side==0 else 'Back central rotor',
                (Move(axis,0,base.geometry.spec.step(axis)),),
                '只转当前面的中央盘，观察另一面和过渡珠保持。'))
    if kind in ('lanlan_pisces','lanlan_hexagram','lanlan_clover_pyraminx'):
        if kind=='lanlan_pisces':from cube.pisces_aligned import generators
        elif kind=='lanlan_clover_pyraminx':from cube.clover_pyraminx_aligned import generators
        else:from cube.hexagram_aligned import generators
        word=generators()[0][1]
    elif entry.mechanism=='shape' and entry.n==4:
        word=('r','U',"r'","U'")
    else:
        word=(first,second,inverse_demo_move(first,base),inverse_demo_move(second,base))
    try:
        last=exercise('练习三：准备、交换与撤回','Exercise 3: setup and restoration',word,
                      '观察整段完成后的块位与方向。这是本例的局部练习，不代表任意打乱都只需这几步。')
    except ValueError:
        # Some extensions have no full outer plane after a core turn.
        # A short valid core sequence demonstrates setup without forcing a cut.
        last=exercise('练习三：核心层与扩展块','Exercise 3: the core and extensions',(second,second),guide.goals[2])
    cases.append(last)
    result=[{'title':text('本型号的转层与局部练习','Model-specific turns and local exercises'),
             'desc':text(guide.intro+' 完整方法见“原创分步教程”；本页练习仅恢复所示起始状态。',
                         'Read the original in-app guide for the method. These local exercises restore their displayed starting states.'),
             'cases':cases}]
    algorithms=[]
    def formula(zh,en,word,tip):
        # Here word is the displayed formula; construct its matching case.
        forward=tuple(inverse_demo_move(m,base) for m in reversed(word))
        item=exercise(zh,en,forward,tip);item['teaching_kind']='formula'
        return item
    if kind=='lanlan_master_clover':
        from cube.master_clover_aligned import leaf_tool,expand
        virtual,slots=leaf_tool();changed=tuple(base.geometry.stickers[s].piece for s in slots)
        item=formula('三小叶片循环','Three-wing cycle',expand(virtual),
            '本项目从双层动作中验证的三循环：匹配图示三片，按标出的棱轴与大层、小层完成全部动作，其他块末态保持；这里只还原图示准备状态。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=changed,
                    reference_cube=base.clone(),tutorial_targets={p:str(i+1) for i,p in enumerate(changed)})
        algorithms.append(item)
    if kind=='mf8_twins':
        from cube.polyhedral import Move
        word=(Move(0,0,180.),Move(12,0,120.),Move(0,0,-180.))
        algorithms.append(formula('棱设置、角转与撤回','Edge setup, corner turn and undo',word,
            '先按图示棱轴半转，再将目标角层转120°，最后撤回棱设置；逐步观察完整块的联动。'))
        from cube.twins_pcubes_aligned import generators
        rows=generators()
        for size,title in ((7,'三棱准备与角层交换'),(9,'两端准备与内外片交换')):
            word=next(w for p,w in rows if len(w)==size)
            algorithms.append(formula(title,'Prepared piece exchange',word,
                '按标出的轴完成所有准备，再转动目标层，最后依次收回。逐步观察内外小片的颜色如何分开；不要跳过中间的准备动作。'))
    if kind=='aj_curvy_dinominx_4':
        from solver.rex_dodecahedron import prepared
        order,macros,flip_word,flip_base=prepared(kind,n)
        from solver.polyhedral import piece_orbits
        orbits=piece_orbits(kind,n)
        for i in order:
            word,cycle=macros[i]
            item=formula('双色棱调位' if len(orbits[i])==30 else '翼棱循环',
                         'Edge positions' if len(orbits[i])==30 else 'Wing cycle',word,
                         '匹配图示三个工作块，执行完整循环。前面已完成的角块保持；普通棱调位时尚未完成的翼棱可以变化。')
            item.update(reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(cycle)})
            algorithms.append(item)
        item=formula('双棱翻转','Flip two edges',flip_word,
                     '两条普通棱同时翻转时使用本例；位置和全部角帽保持，未完成的翼棱可以变化。设置动作完成后必须逆序撤回。')
        item.update(reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(flip_base)})
        algorithms.append(item)
    if kind in ('mf8_bauhinia_minx','kairis_star_finder'):
        from solver.rex_dodecahedron import prepared
        order,macros,flip_word,flip_base=prepared(kind,n)
        names=({3:('棱块调位','Edge positions'),0:('双色翼块循环','Two-colour wing cycle'),
                1:('单色三角循环','Triangle cycle'),2:('中央面循环','Centre cycle')}
               if kind=='kairis_star_finder' else
               {0:('棱块调位','Edge positions'),1:('大叶片循环','Large-petal cycle'),
                3:('中央面循环','Centre cycle'),2:('小三角循环','Small-triangle cycle')})
        for i in order:
            word,cycle=macros[i];zh,en=names[i]
            item=formula(zh,en,word,'先匹配图示工作位。完整执行后，先前阶段的色面保持；尚未完成的其他类型可能随之改变。')
            item.update(reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(cycle)})
            algorithms.append(item)
        item=formula('双棱翻转','Flip two edges',flip_word,
            '两条棱位置正确但两侧颜色相反时，匹配图示工作位。公式翻转这两条棱，保持全部棱的位置；尚未完成的单色块会变化。')
        item.update(reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(flip_base)})
        algorithms.append(item)
    if kind in ('lanlan_flower_copter','lanlan_butterflower'):
        if kind=='lanlan_butterflower':
            from solver.butterflower import _profile
            from cube.butterflower_aligned import expand,AlignedButterflower as AlignedFlowerCopter
        else:
            from solver.flower_copter import _profile
            from cube.flower_copter_aligned import expand,AlignedFlowerCopter
        from cube.polyhedral import Move
        from solver.polyhedral import apply_word
        g=AlignedFlowerCopter().geometry
        data=_profile.data()
        tools=data.get('leaf_stages',[]) or [record for row in data['transversals'] for record in row.values()
               if sum(i!=j for i,j in enumerate(record['permutation']))==3
               and all(len(g.pieces[g.stickers[i].piece])==1 for i,j in enumerate(record['permutation']) if i!=j)]
        # A peeled stage may also move an as-yet-unsolved leaf orbit. The
        # isolated three-piece lesson must preserve ALL other fields.
        tools=[r for r in tools if sum(i!=j for i,j in enumerate(apply_word(g,tuple(Move(*m) for m in r['word']))))==3]
        row=min(tools,key=lambda r:len(r['word']))
        virtual=tuple(Move(*m) for m in row['word'])
        action=apply_word(g,virtual)
        changed=tuple(sorted({base.geometry.stickers[i].piece for i,j in enumerate(action) if i!=j}))
        if len(changed)!=3 or any(len(base.geometry.pieces[h])!=1 for h in changed):
            raise ValueError('Flower tool must cycle exactly three single-colour pieces')
        item=formula('三叶片循环','Three-leaf cycle',expand(virtual),
                     '匹配图示三个单色工作块，完成全部动作后只循环这三块。其他块末态保持；逆向循环请倒序逐步取反，设置动作也要撤回。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=changed,
                    reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(changed)})
        algorithms.append(item)
    if kind=='lanlan_pisces':
        from cube.pisces_aligned import generators
        action,word=next((a,w) for a,w in generators() if sum(a[i]!=i for i in range(len(a)))==3)
        changed=tuple(sorted({base.geometry.stickers[i].piece for i in range(len(action)) if action[i]!=i}))
        if len(changed)!=3 or any(len(base.geometry.pieces[h])!=1 for h in changed):
            raise ValueError('Pisces leaf tool changed another type of piece')
        item=formula('三叶片循环','Three-leaf cycle',word,
            '先匹配图示三个单色工作块，完整执行全部动作。结束后只循环这三块，三色角、双色块与其他单色块保持；设置动作要逆序撤回。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=changed,
                    reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(changed)})
        algorithms.append(item)
    if kind in ('lanlan_hexagram','lanlan_clover_pyraminx'):
        if kind=='lanlan_clover_pyraminx':from cube.clover_pyraminx_aligned import generators
        else:from cube.hexagram_aligned import generators
        def moved(action):
            return tuple(sorted({base.geometry.stickers[i].piece for i in range(len(action)) if action[i]!=i}))
        action,word=next((a,w) for a,w in generators()
                         if len(moved(a))==3 and all(len(base.geometry.pieces[h])==2 for h in moved(a)))
        changed=moved(action)
        item=formula('三双色块循环','Three two-colour pieces',word,
            '先匹配图示三个双色工作块的位置与朝向，完整执行全部动作。结束后只循环这三块，其他块保持；准备动作必须逆序撤回。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=changed,
                    reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(changed)})
        algorithms.append(item)
    if kind=='yeet_ball':
        # Verified on the complete mechanism: corners stay fixed and exactly
        # three single-colour leaves cycle, not just a visual colour effect.
        from solver.polyhedral import apply_word
        word=(first,second,inverse_demo_move(first,base),inverse_demo_move(second,base))
        effect=apply_word(base.geometry,word)
        cycle=tuple(p for p,slots in enumerate(base.geometry.pieces)
                    if any(effect[i]!=i for i in slots))
        if len(cycle)!=3 or any(len(base.geometry.pieces[p])!=1 for p in cycle):
            raise ValueError('Ivy ball teaching formula must cycle three leaves only')
        item=formula('三叶片循环','Three-leaf cycle',word,
            '先匹配本例三个工作叶片的位置。完整执行后仅循环这三片，四个三色角保持；设置动作要逆序撤回。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=cycle,
                    reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(cycle)})
        algorithms.append(item)
    if kind in ('lanlan_curvy_copter','planar_rhombic_12','lanlan_comet_physical','mf8_suncube_2'):
        if kind=='mf8_suncube_2':
            from cube.suncube_aligned import generators
        elif kind=='lanlan_comet_physical':
            from cube.lanlan_comet_aligned import generators
        elif kind=='planar_rhombic_12':
            from cube.comet_aligned import generators
        else:
            from cube.copter_aligned import generators
        word=next(w for action,w in generators() if len(w)==5)
        algorithms.append(formula('混转准备、交换与复形','Jumble, exchange and restore shape',word,
            '先按本例工作轴完成两次部分转动，再半转目标棱，最后撤回两次准备。每一步都经过完整实体阻挡检查；不要在其他起始形状上强拧。'))
    if kind in ('megaminx_ball','skewb_rhombic','jewel_fto','rua','helicopter_14'):
        # An independently constructed commutator, shown with its complete
        # actual effect. It is not advertised as an isolated three-cycle.
        word=(first,second,inverse_demo_move(first,base),inverse_demo_move(second,base))
        algorithms.append(formula('相邻轴交换子与撤回','Adjacent-axis commutator',word,
            '先匹配本例的所有受影响块。此工具展示两个相邻轴的交换子，不承诺只改变三块。'))
    if kind=='helicopter_14':
        from cube.helicopter_14_aligned import generators
        exchange=next(w for p,w in generators() if len(w)==5)
        algorithms.append(formula('两端准备、棱交换与复形','Prepared edge exchange',exchange,
            '将两端棱分别转到标出的准备角，半转目标棱，再按相反顺序收回。观察三角色片跨越普通半转的分组；每一步均需避开完整实体。'))
    if entry.mechanism=='dial_beans':
        from solver.dial_beans import primitive
        word,cycle=primitive(base)
        item=formula('原创工具：三块循环','Original tool: three-piece cycle',word,
                     '本段只循环三个编号工作位，其余角块、数字或滚珠在末态保持。设置后完整执行，再逆序撤销设置。')
        item.update(original=True,teaching_kind='original_formula',cycle_pieces=cycle,
                    reference_cube=base.clone(),tutorial_targets={p:str(j+1) for j,p in enumerate(cycle)})
        algorithms.append(item)
    if hasattr(base,'cubies'):
        # Selected by their complete piece effects, independently of any
        # outside tutorial: [R U R^-1, D] is an isolated corner cycle.
        cycle=('R','U',"R'",'D','R',"U'","R'","D'")
        twist=("F'",'R','U',"R'",'D','R',"U'","R'","D'",'F',"U'",'D','R','U',"R'","D'",'R',"U'","R'",'U')
        algorithms.append(formula('原创核心工具：角块三循环','Core tool: three-corner cycle',cycle,
            '本段循环三个机构角块，其他机构块在末态保持。以真实角块的轮廓和方向对照起始模型。'))
        direction=formula('原创核心工具：两角方向修正','Core tool: paired corner orientation',twist,
            '本段保留块的位置，仅成对调整机构角的朝向；先匹配图示的可见外形，再逐步执行。')
        if not direction['initial'].is_solved():algorithms.append(direction)
        if entry.n==4:
            algorithms.append(formula('原创内切片准备练习','Inner-slice setup exercise',
                ('r',"R'",'U','R',"r'","U'"),
                'r R\' 是单独内切片。比较整段前后的中心组与翼棱；这段是准备练习，不承诺仅改变三块。'))
    elif kind=='container':
        from solver.fisher_skewb import prepared
        from cube.polyhedral import Move
        from cube.mastermorphix import IDENTITY
        from cube.mirror_pyraminx import placements
        record=prepared()
        invisible=sum(1<<i for i,h in enumerate(record['homes'])
                      if len({base.appearance(h,f) for f in placements(3,h,h,'skewb')})==1)
        for mask,atoms in sorted(record['finishers'].items(),key=lambda row:len(row[1])):
            visible=int(mask)&~invisible
            if visible.bit_count()!=1:continue
            word=tuple(Move(*m) for m in atoms)
            item=formula('侧面中心方向修正','Correct a side-centre orientation',word,
                         '适用于图中仅侧中心方向不齐的情况；完整执行公式后其他可见块保持原样。')
            initial=item['initial']
            changed=[p for p,c in initial.pieces.items() if initial.appearance(c.home,c.frame)!=initial.appearance(p,IDENTITY)]
            if len(changed)==1 and all(c.home==p for p,c in initial.pieces.items()):
                algorithms.append(item);break
    if algorithms:
        result.append({'title':text('机构公式与适用状态','Formulas and their matching states'),
                       'desc':text('先比对起始形状、块位与朝向，再执行完整公式。学习路线中的阶段不等于这段公式的全部效果。',
                                   'Match the starting shape, positions and orientations before executing the complete formula.'),
                       'cases':algorithms})
    from pathlib import Path
    import json
    from cube.polyhedral import Move
    data=json.loads((Path(__file__).parent/'data'/'expanded_macros.json').read_text(encoding='utf-8'))
    originals=[]
    for i,record in enumerate(data['models'].get(entry.kind,()),1):
        word=tuple(Move(*m) for m in record['word'])
        item=formula(f'原创三块循环 · 工具 {i}',f'Original three-piece cycle {i}',word,
            '①②③是三个工作位置。先把目标设置到相同位置和朝向，执行完整公式，再逆序撤销设置动作；其他块在整段结束后保持原状。')
        item.update(teaching_kind='original_formula',reference_ids=(),
                    original=True,cycle_pieces=tuple(record['pieces']),
                    reference_cube=base.clone(),
                    tutorial_targets={p:str(j+1) for j,p in enumerate(record['pieces'])})
        # Validate the stated effect, not just inverse-word closure.
        effect=base.clone()
        for move in word:effect.apply_move(move)
        if entry.mechanism=='extended':
            from cube.mastermorphix import IDENTITY
            changed={p for p,frame in enumerate(effect.frames) if frame!=IDENTITY}
        else:
            from solver.polyhedral import apply_word
            action=apply_word(base.geometry,word)
            changed={p for p,slots in enumerate(base.geometry.pieces) if any(action[s]!=s for s in slots)}
        if changed!=set(record['pieces']):raise ValueError('Original teaching formula changed an outside piece')
        originals.append(item)
    if originals:
        result.append({'title':text('原创方法：设置—三块循环—撤销设置','Original method: setup, cycle, undo setup'),
            'desc':text('先看编号工作位；同一工具只处理它能到达的同类块。完整公式只改变图示三块，不能省略中间步骤。',
                        'Match the numbered slots. This complete tool cycles only the three indicated pieces. Do not omit intermediate moves.'),
            'cases':originals})
    return result
