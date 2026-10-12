"""Independent scramble examples and verified, state-specific solution lessons."""
import random

from demo.cases import TEACHING_COLORS, inverse_move_str
from demo.irregular_cases import text


def solved_demo_cube(mode):
    from cube.cube2 import Cube2
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    from cube.cube5 import Cube5
    if isinstance(mode,int):
        return {2:Cube2,3:Cube3,4:Cube4,5:Cube5}[mode].solved(TEACHING_COLORS)
    kind,n=('mastermorphix',3) if mode=='mastermorphix' else mode
    if kind=='mastermorphix':
        from app.mastermorphix_palette import load_palette
        from cube.mastermorphix import MastermorphixCube
        return MastermorphixCube.solved(load_palette(),n=n)
    if kind=='mirror':
        from cube.mirror import MirrorCube
        return MirrorCube.solved(n=n)
    if kind in ('axis','pandora','windmill','fisher'):
        from cube.shape_cube import AxisCube,PandoraCube,WindmillCube,FisherCube
        return {'axis':AxisCube,'pandora':PandoraCube,'windmill':WindmillCube,'fisher':FisherCube}[kind].solved(n=n)
    if kind=='square1':
        from cube.square1 import Square1Cube
        return Square1Cube.solved()
    if kind=='mirror_tower':
        from cube.mirror_tower import MirrorTowerCube
        return MirrorTowerCube.solved()
    from cube.polyhedral import PolyhedralPuzzle
    return PolyhedralPuzzle(kind,n)


def inverse_demo_move(move,cube):
    if isinstance(move,str):
        return inverse_move_str(move)
    if getattr(cube,'puzzle_kind',None)=='square1':
        return move.inverse()
    return move.inverse(cube.geometry.spec.turn_order)


def build_example(mode,case):
    if 'initial' in case:
        return case['initial'].clone()
    cube=solved_demo_cube(mode)
    for move in reversed(case['moves']):
        cube.apply_move(inverse_demo_move(move,cube))
    return cube


def make_scrambled_demo(mode,seed=54):
    """Generate the starting state before asking a solver for any moves."""
    cube=solved_demo_cube(mode)
    kind=getattr(cube,'puzzle_kind','cube')
    if kind=='square1':
        cube.scramble(length=12,seed=seed)
    elif hasattr(cube,'geometry'):
        from solver.polyhedral import scramble
        scramble(cube,length=24,seed=seed)
    else:
        from cube.scramble import random_scramble
        # Two-layer widths keep odd-order fixed face centres at their axes.
        word=random_scramble(cube.n,rng=random.Random(seed),puzzle_kind='mastermorphix')
        for move in word:
            cube.apply_move(move)
    if cube.is_solved():
        raise ValueError('The demonstration scramble must change the puzzle')
    return cube


def state_signature(cube):
    def frame(c):
        values=getattr(c,'frame',None)
        return tuple(tuple(round(x,8) for x in row) for row in values) if values is not None else None
    if getattr(cube,'puzzle_kind',None)=='square1':
        return cube.slots,cube.middle
    if getattr(cube,'puzzle_kind',None)=='mirror_tower':
        return tuple(sorted((p,c.home,frame(c)) for p,c in cube.pieces.items()))
    if hasattr(cube,'cubies'):
        return tuple(sorted((p,c.home,tuple(sorted(c.stickers.items())),frame(c))
                            for p,c in cube.cubies.items()))
    return tuple(cube.colors)


def verified_solution_lessons(initial,result):
    """Reject a failed/partial solution before exposing any lesson to the UI."""
    if not result.success:
        raise ValueError(result.message or 'The solver did not finish')
    replay=initial.clone()
    for move in result.moves:
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('The demonstration solution did not restore its starting state')
    stages=[s for s in result.stages if s.moves]
    phase_moves=[m for s in stages for m in s.moves]
    phase_replay=initial.clone()
    try:
        for move in phase_moves:
            phase_replay.apply_move(move)
        phases_verified=bool(stages) and phase_replay.is_solved()
    except (ValueError,KeyError):
        phases_verified=False
    # A pedagogical phase path may be slightly longer than the solver's
    # compacted word. Use it only after independently verifying the whole path.
    complete_moves=phase_moves if phases_verified else result.moves
    def example(name,cube,moves):
        return {'name':name,'initial':cube.clone(),'moves':tuple(moves),
                'text':text(f'共 {len(moves)} 步，当前动作显示在播放进度中。',
                            f'{len(moves)} moves. The playback progress shows the current move.'),
                'tip':text('先把实物摆成与起始模型相同的方向和块排列，再逐步跟随；其他打乱应使用“按我的录入还原”。',
                           'Match the model orientation and starting pieces before following it. Use your entered state for a different scramble.')}
    complete={'title':text('完整还原：从真实打乱到还原','Complete restoration of a real scramble'),
              'desc':text('本演示先独立生成合法打乱，再根据块状态求解。按右箭头执行一步，左箭头撤回一步；可旋转模型核对实物。',
                          'A legal scramble is generated first and solved from its piece state. Right executes a move, left undoes it; rotate the model to check your puzzle.'),
              'cases':[example(text('完整还原过程','Complete solution'),initial,complete_moves)]}
    lessons=[complete]
    if phases_verified:
        work=initial.clone()
        for stage in stages:
            titles={
                'twophase':text('三阶整体还原','Three-layer restoration'),
                '2x2':text('二阶整体还原','Two-layer restoration'),
                'centers':text('六面中心归面','Restore the face centers'),
                'center':text('六面中心归面','Restore the face centers'),
                'edge_pairing':text('棱块配对','Pair the edges'),
                'reduce_edges':text('中棱与翼块组合','Group middle edges and wings'),
                'parity':text('四阶特殊情况处理','Four-layer parity correction'),
                'reduced_3x3':text('按三阶还原','Restore the reduced three-layer puzzle'),
                'reduce_3x3':text('按三阶还原','Restore the reduced three-layer puzzle'),
                'orient':text('配棱朝向修正','Correct paired-edge orientation'),
            }
            title=titles.get(stage.name,stage.description)
            descriptions={
                'centers':text('把各面的同色中心归面，棱角留待后续阶段处理。先核对本段起始状态再跟随。',
                               'Restore all face-center colors; corners and edges are handled later. Match this phase start before following it.'),
                'center':text('把各面的同色中心归面，固定面心作为配色参考。棱角留待后续阶段处理。',
                              'Restore face-center colors using fixed centers as references. Corners and edges are handled later.'),
                'reduce_edges':text('把同色中棱与双翼集中到同一棱位。这一步结束后，中棱与翼块可能仍有方向差异，继续下一阶段修正。',
                                    'Gather a middle edge and its two matching wings into one slot. Their orientations may still differ; continue to the orientation phase.'),
                'edge_pairing':text('把同色双翼配成逻辑棱，保留已完成的中心。配棱完成后继续处理特殊情况和三阶阶段。',
                                    'Pair matching wings while preserving center colors, then continue with parity correction and three-layer restoration.'),
                'orient':text('修正中棱相对双翼的方向，使每组三块棱的朝向一致。完成后继续按三阶还原。',
                              'Align the middle edge with its two wings, then continue with three-layer restoration.'),
            }
            lessons.append({'title':title,
                            'desc':descriptions.get(stage.name,text('从完整演示中该阶段的真实状态开始。此段完成后继续后续阶段，不要求每段都恢复整只魔方。',
                                                                   'This phase starts at its real state in the complete solution. Continue to the next phase after finishing it.')),
                            'cases':[example(title,work,stage.moves)]})
            for move in stage.moves:
                work.apply_move(move)
    return lessons
