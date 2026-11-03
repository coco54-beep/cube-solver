"""Original, mechanism-specific worked examples for the remaining catalogue.

Prepared examples have a documented starting state and an independently replayed
answer. They are demonstrations of that state, not an arbitrary-state solver.
"""
from functools import lru_cache
from random import Random

from demo.irregular_cases import text

SPECIAL = frozenset(('pentacle','ghost','ghost_pyramid','mirror_pyraminx','mirror_skewb',
                     'circle_2','o2','ancient_coin','camouflage_3','mirror_camouflage_3','floppy_133','square0','square2','super_square1',
                     'tangram','tangram_extreme'))


def supports(kind,n):
    from cube.bandaged_cube import KINDS
    from cube.appearance import PENROSE
    return (kind in SPECIAL or kind in KINDS or kind in PENROSE or
            kind in ('axis','windmill','fisher') and n==4 or
            kind.startswith(('mixup_','crazy_','cuboid_')) or n>=6)


def supports_mode(mode):
    return supports('cube',mode) if isinstance(mode,int) else (
        isinstance(mode,tuple) and supports(*mode))


def entry_screen(kind,n):
    if not supports(kind,n):return None
    from cube.bandaged_cube import KINDS
    from cube.appearance import PENROSE
    if kind=='cube' or kind in KINDS or kind in PENROSE:return 'InputScreen'
    if kind.startswith('mixup_'):return 'MixupInputScreen'
    if kind.startswith('tangram'):return 'ArticulatedEntryScreen'
    if kind.startswith('cuboid_') or kind in ('camouflage_3','mirror_camouflage_3','floppy_133'):
        return 'CuboidSixViewScreen' if make_cube(kind,n).can_change_shape else 'PolyhedralScreen'
    return {'ghost':'GhostScreen','ghost_pyramid':'GhostPyramidScreen',
            'mirror_pyraminx':'MirrorPyraminxScreen','mirror_skewb':'MirrorSkewbScreen',
            'pentacle':'PentacleScreen','square0':'SquareFamilyScreen',
            'square2':'SquareFamilyScreen','super_square1':'SquareFamilyScreen',
            'mastermorphix':'MastermorphixScreen','mirror':'MirrorScreen',
            'axis':'ShapeCubeScreen','windmill':'ShapeCubeScreen','fisher':'ShapeCubeScreen'}.get(kind,
            'CuboidSixViewScreen' if kind=='camouflage_3' else 'PolyhedralScreen')


def open_tutorial(screen):
    if not screen.entry_can_edit():return
    cube=getattr(screen,'_cube',None)
    if cube is None:
        from kivy.app import App
        cube=App.get_running_app().cube
    kind=getattr(cube,'puzzle_kind','cube');n=cube.n
    if not supports(kind,n):return
    mode=n if kind=='cube' else (kind,n)
    screen.manager.get_screen('DemoMenuScreen').set_mode(mode)
    screen.manager.current='DemoMenuScreen'


def make_cube(kind,n):
    from cube.bandaged_cube import KINDS,BandagedCube
    from cube.appearance import PENROSE,with_appearance
    from demo.cases import TEACHING_COLORS
    if kind in KINDS:return BandagedCube.solved(kind)
    if kind=='cube' or kind in PENROSE:
        from cube.cube2 import Cube2
        from cube.cube3 import Cube3
        from cube.cube4 import Cube4
        from cube.cube5 import Cube5
        from cube.cube_n import CubeN
        cube=({2:Cube2,3:Cube3,4:Cube4,5:Cube5}[n].solved(TEACHING_COLORS)
              if n<=5 else CubeN.solved(n))
        return with_appearance(cube,kind if kind!='cube' else None)
    if kind.startswith('mixup_'):
        from cube.mixup import MixupCube
        return MixupCube(kind)
    if kind.startswith('tangram'):
        from cube.articulated import ArticulatedCube
        return ArticulatedCube(kind)
    if kind.startswith('cuboid_') or kind in ('camouflage_3','mirror_camouflage_3','floppy_133'):
        from cube.cuboid import CuboidCube
        return CuboidCube.solved(kind)
    if kind=='circle_2':
        from cube.circle_cube import Circle2Cube
        return Circle2Cube()
    if kind=='pentacle':
        from cube.pentacle import PentacleCube
        return PentacleCube.solved()
    if kind in ('square0','square2','super_square1'):
        from cube.square_family import SquareFamilyCube
        return SquareFamilyCube.solved(kind)
    if kind in ('axis','windmill','fisher'):
        from cube.shape_cube import AxisCube,WindmillCube,FisherCube
        return {'axis':AxisCube,'windmill':WindmillCube,'fisher':FisherCube}[kind].solved(n=n)
    if kind in ('ghost','mirror','mastermorphix'):
        if kind=='ghost':from cube.ghost import GhostCube as cls
        elif kind=='mirror':from cube.mirror import MirrorCube as cls
        else:from cube.mastermorphix import MastermorphixCube as cls
        return cls.solved(n=n)
    if kind in ('ghost_pyramid','mirror_pyraminx','mirror_skewb'):
        if kind=='ghost_pyramid':from cube.ghost_pyramid import GhostPyramidCube as cls
        elif kind=='mirror_pyraminx':from cube.mirror_pyraminx import MirrorPyraminxCube as cls
        else:from cube.mirror_skewb import MirrorSkewbCube as cls
        return cls.solved(n=n)
    from cube.polyhedral import PolyhedralPuzzle
    return PolyhedralPuzzle(kind,n)


def view_class(cube):
    kind=getattr(cube,'puzzle_kind','cube')
    if kind.startswith(('mixup_','tangram')):
        from renderer.articulated_view import ArticulatedView
        return ArticulatedView
    if kind=='pentacle':
        from renderer.pentacle_view import PentacleView
        return PentacleView
    if kind.startswith('cuboid_') or kind in ('camouflage_3','mirror_camouflage_3','floppy_133'):
        from renderer.cuboid_view import CuboidView
        return CuboidView
    if kind in ('ghost_pyramid','mirror_pyraminx','mirror_skewb'):
        if kind=='ghost_pyramid':from renderer.ghost_pyramid_view import GhostPyramidView as cls
        elif kind=='mirror_pyraminx':from renderer.mirror_pyraminx_view import MirrorPyraminxView as cls
        else:from renderer.mirror_skewb_view import MirrorSkewbView as cls
        return cls
    if kind in ('square0','square2','super_square1'):
        from renderer.square_family_view import SquareFamilyView
        return SquareFamilyView
    if hasattr(cube,'cubies'):
        from renderer.mastermorphix_view import cube_view_class_for
        return cube_view_class_for(cube)
    from renderer.polyhedral_view import PolyhedralView
    return PolyhedralView


def inverse(move,cube):
    if isinstance(move,str):
        if getattr(cube,'puzzle_kind',None)=='ghost':
            from cube.ghost import inverse_move
            return inverse_move(move)
        from demo.cases import inverse_move_str
        return inverse_move_str(move)
    if getattr(cube,'puzzle_kind',None) in ('square0','square2','super_square1'):
        return move.inverse()
    return move.inverse(cube.geometry.spec.turn_order)


def notation(move,cube):
    kind=getattr(cube,'puzzle_kind','cube')
    if isinstance(move,str):
        if move.startswith('@G'):
            from cube.ghost import custom_move
            _,layer,angle=custom_move(move)
            return f'对齐层 {layer+1}: {angle:+g}°'
        if move.startswith('@F:'):return '翻转轴 '+move[3:]
        return move
    if kind in ('square0','square2','super_square1'):return str(move)
    if kind=='pentacle':
        angle=move.amount%360
        if angle>180:angle-=360
        return f'{"圆盘" if move.layer==0 else "整层"} {move.axis+1}: {angle:+g}°'
    if move.__class__.__name__=='PyramidAlignment':return f'开合: {move.angle:+g}°'
    from demo.irregular_cases import token
    return token(move,cube.geometry.spec)


def candidates(cube):
    from cube.polyhedral import Move
    kind=getattr(cube,'puzzle_kind','cube')
    if kind=='ghost':
        if cube.n==1:return tuple('@F:'+str(i) for i in range(1,6))
        return tuple(cube.alignment_moves())+('R','U','F',"R'","U'","F'")
    if kind=='ghost_pyramid':
        return ((cube.alignment_move(),) if abs(cube.phase)>1e-8 else ()) + tuple(
            Move(a,l,1) for a,bands in enumerate(cube.geometry.layers) for l,b in enumerate(bands) if b)
    if kind in ('square0','square2','super_square1'):
        from cube.square_family import SquareFamilyMove
        return tuple(SquareFamilyMove(a,p,cube.layer_count) for a in range(cube.layer_count)
                     for p in (1,2,3,6,9,10,11))+(SquareFamilyMove(cube.layer_count,1,cube.layer_count),)
    if hasattr(cube,'cubies'):
        moves=('R','U','F',"R'","U'","F'",'R2','U2','F2','L','D','B')
        return moves+(('2R','2U','2F','Rw','Uw') if cube.n>=4 else ())
    if hasattr(cube,'moves'):return tuple(cube.moves())
    g=cube.geometry
    if kind=='pentacle':return cube.moves()
    return tuple(Move(a,l,p*g.spec.step(a)) for a,bands in enumerate(g.layers)
                 for l,b in enumerate(bands) if b for p in (1,-1,2))


def family(kind,n):
    if kind=='mirror_camouflage_3':return 'mirror_camouflage_3'
    if kind=='floppy_133':return 'floppy_133'
    if kind.startswith('mixup_'):return 'mixup_plus' if '_plus_' in kind else 'mixup'
    if kind.startswith('tangram'):return kind
    if kind.startswith('crazy_'):return 'crazy'
    if kind.startswith('cuboid_'):return 'cuboid'
    if kind.startswith('penrose_'):return 'penrose'
    if kind=='ghost' and n==1:return 'ghost_floppy'
    if kind in ('axis','windmill','fisher'):return 'shape_cube'
    from cube.bandaged_cube import KINDS
    if kind in KINDS:return 'bandaged'
    if kind in ('square0','square2','super_square1'):return 'square'
    if kind in ('mirror_pyraminx','mirror_skewb'):return 'silver_poly'
    if n>=6:
        return {'megaminx':'high_minx','pyraminx':'high_tetra','moyu':'high_tetra',
                'skewb':'high_skewb','dino':'high_dino','mirror':'high_mirror',
                'mastermorphix':'high_morphix'}.get(kind,'high_order')
    return kind


# Each profile describes the existing physical model, its useful work order,
# the completion check, and the particular mistake this lesson must avoid.
PROFILES={
 'mirror_camouflage_3':('银色贴面随实体移动；按大小、台阶和黑色塑料辨认块，不能用六面颜色辨位。',
                        '先找不穿过连块的合法切面，再逐步恢复偏移外壳；完成时六个银色表面应重新连成平面。',
                        '用六视图记录实际可见轮廓，遮挡部分由实体匹配恢复；银色面与裸露塑料不能混淆。'),
 'floppy_133':('普通软魔方有四条可转边，每次只翻转180°，始终保持1×3×3外形。',
               '先观察边层翻转如何交换角块，再复原侧边与正反面颜色。',
               '这款不允许超级软魔方的90°变形动作；逐面填色后检查30个实体贴面。'),
 'mixup':('先分清角块、棱块与中心块；中层45°转动可让棱与中心交换位置。',
          '先对齐可转切面，恢复能够按普通层转动的形状，再处理对应三阶或四阶块位。',
          '每次核对块的实体边界；334、344及四阶只执行模型允许的角度，不能跨块硬转。'),
 'mixup_plus':('除角、棱、中心，还要跟踪内棱及内棱两侧方向；两块内棱可能同向或反向。',
               '先恢复切面对齐，再核对内棱、中心和棱的组合，最后进入普通层的还原。',
               '内棱属于实体块，颜色面不一定共面；不能把交换到棱位的中心误当成棱。'),
 'tangram':('以实际斜切片的边界辨认块；颜色跟随实体片移动。',
            '按模型标注轴观察斜切片换位，先匹配当前块的位置，再核对各面的颜色。',
            '外观看似普通三阶，但案例使用本型号的实体片与转动规则，不能套普通方块图。'),
 'tangram_extreme':('先看斜切片形状，再看朝向与颜色；同色但不同轮廓的片不能互换判断。',
                    '逐步恢复斜切片的位置和方向，最后核对轮廓拼接和颜色；每步都可旋转模型观察。',
                    '只对上颜色仍可能方向错误；用黑色接缝与相邻斜边检查片的朝向。'),
 'pentacle':('观察圆盘、圆盘分片和外角块；内部支撑不作为彩色棱块录入或还原。区分圆盘自由转动与对齐后转层。',
             '需要整层转动时先对齐相关圆盘，使五角星的切边连成直线；转层后重新检查切线。',
             '圆盘的任意角度不能当成整层自由度；本例通过软件模型切线检查，当前实物外形仍在复核。'),
 'ghost':('以块的形状和大小辨位；普通幽灵外形还带有水平错层，先找能对齐的层。',
          '先把错层对齐到机械位置，再还原块位；最后收回各层错角，检查目标外形。',
          '非对齐时不要跨轴转动；一阶幽灵使用五条翻转轴，不能按普通一阶立方体处理。'),
 'ghost_floppy':('中央五边形固定，周围有五条180°翻转轴；靠轮廓、边块和角块的朝向辨位。',
                 '先按模型的1—5轴编号看清一次翻转带动哪些块，再逐步调整相邻角块的位置与朝向。',
                 '这款没有多层幽灵的水平错层对齐动作；最后检查外框闭合和各块正反面，不能当普通一阶立方体。'),
 'ghost_pyramid':('先分清外壳闭合外形与内部机械对齐位置；开合本身也是一个动作。',
                  '打开到允许转动的对齐位置，调整实体块，再把开合层闭合到目标外形。',
                  '闭合时其他转轴可能锁住；不能忽略开合角度，只核对块的轮廓。'),
 'silver_poly':('银色没有六面颜色提示，靠块的外形、尺寸以及接缝辨认位置和方向。',
                '先认清本型号的转轴，跟踪模型中移走的块，再检查它回到对应轮廓的位置。',
                '镜面金字塔的三角转动和镜面斜转的角轴不能混用；本例使用对应的实体模型。'),
 'circle_2':('外层角块与面内圆块是两套可动部分，圆圈不是固定装饰线。',
             '分别观察外层与内圆动作怎样改变块位，最后同时核对内圆和外层的颜色。',
             '只看外层颜色会漏掉内圆状态；动作旁标注轴和层，注意转动的是哪部分。'),
 'crazy':('先核对该行星哪些面带固定圆、哪些面圆块随层转；以本型号的实际分块为准。',
          '分别跟踪圆内、圆外块，再恢复各组位置；完整动作结束后检查已还原部分。',
          '八大行星的固定面配置不同；不要照抄另一颗行星的圆块运动。'),
 'cuboid':('先辨认长宽高和实际块边界，动作按对应轴、层和允许角度标注。',
           '会变形的型号先恢复可对齐的形状，再处理层内块位与颜色；不变形型号直接核对各面。',
           '长方体不保证每轴都能90°转；只有不切穿实体块的动作才会进入演示。'),
 'camouflage_3':('彩色贴片和黑色塑料共同描述实体；被遮住的部分不能误判断成更小的块。',
                 '先认出真实连块边界与可转层，逐步恢复位置和外形，再核对彩色贴片。',
                 '本例保留真实黑色实体和遮挡，转动整只模型核对相邻面，不按可见格数猜块大小。'),
 'o2':('区分圆形切线内外的独立部分，跟踪真实分块与面色。',
        '先看模型标注的切面与角度，再跟踪局部换位；最后核对圆内外的颜色连续性。',
        '圆形图案不是贴纸装饰；案例播放的是本型号实际可动分区。'),
 'ancient_coin':('沿古钱币切线辨认独立分区，先看块界再看颜色。',
                  '按标注转轴调整分区，跟踪相邻切线的衔接，再核对各面的颜色。',
                  '不要把中心图案当成固定方块；以模型显示的实体边界和可转层为准。'),
 'penrose':('弯曲的外表面可能跨越机械面；同一个视觉颜色区域不一定是同一种机械块。',
             '用真实棱的弯曲轮廓和角块位置辨位，先恢复块位方向，再核对连续曲面。',
             '本例显示彭罗斯外壳而非普通三阶方块；不能仅用普通六面颜色判断外形已还原。'),
 'bandaged':('先找绑在一起的实体块，确认一条切面是否会穿过连块。',
              '逐步打开可转工作层，移动连块并归位；每一步都要保留下一步所需切面。',
              '普通魔方能做的公式在绑块上未必合法；案例逐步检查连块，锁住时不会硬转。'),
 'square':('看清每层角块与棱块的宽度；层转与切割是不同动作，多层型号要逐层核对。',
            '先把切割线两侧对齐，恢复层形和块顺序，再检查上下层及中层状态。',
            '斜切线不能穿过角块；Super Square-1 的内外层都要跟踪，不能只看上下两层。'),
 'high_order':('把角块、翼棱和各圈中心分开看；不同距离的中心与翼棱属于不同轨道。',
               '先恢复各面中心，再把同色翼棱配成逻辑棱，随后按三阶处理；偶数阶另查特殊情况。',
               '内层不是整只魔方转动；按动作中的层号或宽转标记操作，奇数阶固定面心保留作参考。'),
 'shape_cube':('用本型号的斜切轮廓辨认中心、棱和角；四阶还要核对各块的形状方向。',
               '先让同组中心与翼棱归到对应机械面，再恢复整只魔方的轮廓与块位。',
               '机械层与视觉面可能不重合；本例沿真实层转动，注意斜切块的方向，不能只看颜色。'),
 'high_minx':('用十二面的面色与五边形中心定拿法，区分不同距离的中心、翼棱及角块轨道。',
              '按轨道整理各面中心和对应棱组，再继续基础十二面体的块位处理；每段结束核对已完成部分。',
              '本型号围绕五边形面转动，不用普通立方体的90°动作；跟随模型标注的轴和角度。'),
 'high_tetra':('用四面体的角与三角面辨位；先区分小角层、主体层和各圈中心。',
               '先确定角的拿法，再按轨道整理中心及棱组，最后核对相邻三角面的连续性。',
               '尖端层与主体层不是同一个转层；魔塔的曲面也不能改变内部四面体的转动规则。'),
 'high_skewb':('沿角轴辨认同一转动带动的三面，按轨道区分中心与周边小块。',
               '先在正确角轴上整理对应轨道，再检查中心朝向和相邻面的块位关系。',
               '斜转不是绕普通面的四分之一圈；动作按实际角轴与层号标注。'),
 'high_dino':('绕角轴跟踪相邻三面的块；高阶模型有更多同轨道小块需要分别整理。',
              '先看完整角转对周围块的影响，再沿各轨道处理错位，检查相邻面边界。',
              '不要用普通面转的方向猜角转方向；以模型动作轴和标注角度为准。'),
 'high_mirror':('全银色靠尺寸与轮廓辨位；区分不同大小的中心和翼棱，不能用六面颜色判断。',
                '先恢复各面中心轮廓，再让翼棱拼成完整边界，随后处理缩减后的块位与方向。',
                '同一平面上的银色块仍可能位置错误；同时比较尺寸、层高和相邻接缝。'),
 'high_morphix':('三角外表面与内部机械层不同；按形状、面色和层号辨认中心、棱与角。',
                 '先整理同轨道中心，再配齐对应棱组，缩减后按三阶粽子的块位与方向继续。',
                 '视觉三角面的中心不是所有机械层的转轴；核对模型里被带动的实际层。'),
}


def modes():
    """All previously missing catalogue modes, not just one order per family."""
    from cube.articulated import MIXUP_MODELS,TANGRAM_MODELS
    from cube.cuboid import MODELS
    from cube.bandaged_cube import KINDS
    from cube.appearance import PENROSE
    from cube.square_family import KINDS as SQUARE
    result=[('cube',n) for n in range(6,18)]
    for kind in ('mirror','mastermorphix'):result.extend((kind,n) for n in range(6,10))
    for kind,orders in [('pyraminx',(6,7)),('skewb',(7,)),('dino',(6,)),
                        ('megaminx',range(6,14)),('moyu',(6,7)),('axis',(4,)),('windmill',(4,)),('fisher',(4,))]:
        result.extend((kind,n) for n in orders)
    result.extend((k,max(dims)) for k,(dims,_) in MIXUP_MODELS.items())
    result.extend((k,3) for k in TANGRAM_MODELS)
    result.extend(('ghost',n) for n in range(1,5))
    result.extend([('pentacle',3),('ghost_pyramid',3),('mirror_pyraminx',3),
                   ('mirror_pyraminx',4),('mirror_skewb',3),('circle_2',2),('o2',1),('ancient_coin',3)])
    from cube.circle_cube import PLANETS
    result.extend(('crazy_'+p,3) for p in PLANETS)
    result.extend((k,make_cube(k,3).n) for k in MODELS if k.startswith('cuboid_') or k in ('camouflage_3','mirror_camouflage_3','floppy_133'))
    result.extend(KINDS.items())
    result.extend((k,int(k[-1])) for k in PENROSE)
    result.extend((k,3) for k in SQUARE)
    return tuple(dict.fromkeys(result))


def prepared(kind,n,length,seed,focus=None):
    """Create a legal teaching state and retain a separately replayed answer."""
    work=make_cube(kind,n);rng=Random(seed);answer=[];previous=None
    from demo.solutions import state_signature
    original=state_signature(work)
    prefix=[]
    if kind=='ghost' and n>1:prefix=list(work.alignment_moves())
    elif kind=='ghost_pyramid':prefix=[work.alignment_move()]
    def apply(move):
        work.apply_move(move);answer.insert(0,inverse(move,work))
    for move in prefix:apply(move)
    for index in range(length):
        options=list(candidates(work));rng.shuffle(options)
        if kind=='pentacle' and (focus=='inner' or index%3==1):
            from cube.polyhedral import Move
            for axis in rng.sample(range(6),6):
                try:
                    plan=list(work.alignment_moves(axis))+[Move(axis,1,90)]
                    check=work.clone();check.apply_moves(plan)
                except ValueError:continue
                options.insert(0,plan);break
        if focus=='inner':
            options.sort(key=lambda move: not (
                isinstance(move,list) or
                isinstance(move,str) and move.startswith(('2','Rw','Uw')) or
                not isinstance(move,str) and (getattr(move,'layer',0)>0 or getattr(move,'amount',0)%2)))
        options.sort(key=lambda move:getattr(move,'axis',move)==previous)
        for move in options:
            try:
                trial=work.clone();sequence=move if isinstance(move,list) else [move]
                inverses=[]
                for action in sequence:
                    trial.apply_move(action);inverses.insert(0,inverse(action,trial))
                if state_signature(trial)==state_signature(work):continue
            except ValueError:continue
            work=trial;answer=inverses+answer;previous=getattr(sequence[-1],'axis',sequence[-1]);break
        else:raise ValueError('No legal teaching move: '+kind)
    if kind=='ghost' and n>1:
        for move in work.alignment_moves(restore=True):apply(move)
    elif kind=='ghost_pyramid':apply(work.alignment_move(close=True))
    if state_signature(work)==original:
        if length>=24:raise ValueError('Unchanged teaching example: '+kind)
        return prepared(kind,n,length+1,seed+1,focus)
    check=work.clone()
    for move in answer:check.apply_move(move)
    if not check.is_solved():raise ValueError('Unverified teaching answer: '+kind)
    return work,tuple(answer)


def _case(kind,n,name,length,seed,focus=None):
    initial,moves=prepared(kind,n,length,seed,focus)
    sequence=('  '.join(notation(m,initial) for m in moves) if len(moves)<=12 else
              f'本例共 {len(moves)} 步。左右箭头逐步退回／执行，当前转轴、层与角度显示在动作进度中。')
    return {'name':name,'initial':initial,'moves':moves,'show_all':True,
            'text':sequence,
            'tip':text('先把实物拿成与初始模型相同的方向并核对块位。逐步执行，结束后核对外形、方向和颜色；其他打乱请使用“按我的录入还原”。',
                       'Match the displayed starting state and grip. Check shape, orientation and colours after replay. Use your entered state for a different scramble.')}


@lru_cache(maxsize=12)
def lessons(kind,n):
    profile=PROFILES[family(kind,n)]
    titles=('认识本型号的合法动作','局部调整与方向核对','组合动作与完成检查')
    result=[]
    for i,(title,length) in enumerate(zip(titles,(1,4,8))):
        result.append({'title':title,'desc':profile[i]+'\n'+profile[(i+1)%3],
                       'cases':[_case(kind,n,'按图逐步复原',length,41+i,'inner' if i==1 else None)]})
    return result


@lru_cache(maxsize=12)
def complete_lessons(kind,n):
    return [{'title':'完整分步案例（固定起始状态）',
             'desc':PROFILES[family(kind,n)][1]+'\n这是预设教学状态的完整复原案例，每步已按本型号的转动约束校验。先核对模型起始状态再跟随，不能直接套用到任意实物打乱。',
             'cases':[_case(kind,n,'从本例的错位状态到完整复原',16,57,'inner')]}]
