"""Model, renderer and entry-page routing for the requested collection.

Teaching models are independent of the user's input, including shaped pieces
whose colours alone cannot describe their state.
"""
from candidate_puzzles import BY_KIND


def entry_screen(kind):
    if kind=='helicopter_14':return 'EdgeJumblingInputScreen'
    entry=BY_KIND.get(kind)
    if entry is None:return None
    return {
        'extended':'CuboidSixViewScreen','shape':'ShapeCubeScreen',
        'skewb_shell':'ContainerScreen','blanker':'BlankerScreen',
        'mirror_minx':'MirrorMinxScreen',
        'copter':'CopterInputScreen',
        'comet':'CometInputScreen',
        'lanlan_comet':'LanlanCometInputScreen',
        'twins':'TwinsInputScreen',
        'suncube':'SunCubeInputScreen',
        'pisces':'PiscesInputScreen',
        'hexagram':'HexagramInputScreen',
        'flower_copter':'FlowerCopterInputScreen',
        'butterflower':'ButterflowerInputScreen',
        'master_clover':'MasterCloverInputScreen',
        'clover_pyraminx':'CloverPyraminxInputScreen',
    }.get(entry.mechanism,'PolyhedralScreen')


def open_tutorial(screen):
    cube=getattr(screen,'_cube',None)
    if cube is None or not screen.entry_can_edit():return
    entry=BY_KIND.get(cube.puzzle_kind)
    if entry is None:return
    screen.manager.get_screen('DemoMenuScreen').set_mode((entry.kind,entry.n))
    screen.manager.current='DemoMenuScreen'


def make_cube(kind,n):
    entry=BY_KIND[kind];kind=entry.kind
    if n!=entry.n:raise ValueError('Unsupported teaching model order')
    if kind=='helicopter_14':
        from cube.edge_jumbling import Helicopter14Cube
        return Helicopter14Cube()
    if entry.mechanism=='master_clover':
        from cube.master_clover import MasterCloverCube
        return MasterCloverCube()
    if entry.mechanism=='butterflower':
        from cube.butterflower import ButterflowerCube
        return ButterflowerCube()
    if entry.mechanism=='clover_pyraminx':
        from cube.clover_pyraminx import CloverPyraminxCube
        return CloverPyraminxCube()
    if entry.mechanism=='flower_copter':
        from cube.flower_copter import FlowerCopterCube
        return FlowerCopterCube()
    if entry.mechanism=='hexagram':
        from cube.hexagram import HexagramCube
        return HexagramCube()
    if entry.mechanism=='pisces':
        from cube.pisces import PiscesCube
        return PiscesCube()
    if entry.mechanism=='suncube':
        from cube.suncube import SunCube
        return SunCube()
    if entry.mechanism=='twins':
        from cube.twins_pcubes import TwinsPCubesState
        return TwinsPCubesState()
    if entry.mechanism=='lanlan_comet':
        from cube.lanlan_comet import LanlanCometCube
        return LanlanCometCube()
    if entry.mechanism=='comet':
        from cube.crazy_comet import CometCube
        return CometCube()
    if entry.mechanism=='copter':
        from cube.copter_input import CopterCube
        return CopterCube()
    if entry.mechanism=='extended':
        from cube.cuboid import CuboidCube
        return CuboidCube.solved(kind)
    if entry.mechanism=='shape':
        from cube.solid_shape_mods import FACTORIES
        return FACTORIES[kind].solved(n=n)
    if kind=='container':
        from cube.container import ContainerCube
        return ContainerCube.solved()
    if kind=='blanker':
        from cube.blanker import BlankerCube
        return BlankerCube.solved()
    if entry.mechanism=='mirror_minx':
        from cube.mirror_minx import MirrorMinxCube
        return MirrorMinxCube.solved(n=n)
    from cube.polyhedral import PolyhedralPuzzle
    return PolyhedralPuzzle(kind,n)


def view_class(kind):
    if kind=='helicopter_14':
        from renderer.edge_jumbling_view import EdgeJumblingView
        return EdgeJumblingView
    entry=BY_KIND[kind]
    if entry.mechanism=='master_clover':
        from renderer.master_clover_view import MasterCloverView
        return MasterCloverView
    if entry.mechanism=='butterflower':
        from renderer.butterflower_view import ButterflowerView
        return ButterflowerView
    if entry.mechanism=='clover_pyraminx':
        from renderer.pisces_view import CloverPyraminxView
        return CloverPyraminxView
    if entry.mechanism=='flower_copter':
        from renderer.flower_copter_view import FlowerCopterView
        return FlowerCopterView
    if entry.mechanism=='hexagram':
        from renderer.pisces_view import HexagramView
        return HexagramView
    if entry.mechanism=='pisces':
        from renderer.pisces_view import PiscesView
        return PiscesView
    if entry.mechanism=='suncube':
        from renderer.twins_view import SunCubeView
        return SunCubeView
    if entry.mechanism=='twins':
        from renderer.twins_view import TwinsView
        return TwinsView
    if entry.mechanism=='lanlan_comet':
        from renderer.comet_view import LanlanCometView
        return LanlanCometView
    if entry.mechanism=='comet':
        from renderer.comet_view import CometView
        return CometView
    if entry.mechanism=='copter':
        from renderer.copter_view import CopterView
        return CopterView
    if entry.mechanism=='dial_beans':
        from renderer.dial_bean_view import DialBeanView
        return DialBeanView
    if entry.mechanism=='extended':
        from renderer.cuboid_view import CuboidView
        return CuboidView
    if entry.mechanism=='shape':
        from renderer.shape_cube_view import SOLID_VIEWS
        return SOLID_VIEWS[entry.kind]
    if kind=='container':
        from renderer.fisher_skewb_view import FisherSkewbView
        return FisherSkewbView
    if kind=='blanker':
        from renderer.blanker_view import BlankerView
        return BlankerView
    if entry.mechanism=='mirror_minx':
        from renderer.mirror_minx_view import MirrorMinxView
        return MirrorMinxView
    from renderer.polyhedral_view import PolyhedralView
    return PolyhedralView


def legal_moves(cube):
    if hasattr(cube,'cubies'):
        return ('R','U','F',"R'","U'","F'") + (('r','u') if cube.n==4 else ())
    from cube.polyhedral import Move
    if hasattr(cube,'moves'):return tuple(cube.moves())
    g=cube.geometry
    return tuple(Move(axis,layer,g.spec.step(axis))
                 for axis,layers in enumerate(g.layers) for layer,band in enumerate(layers) if band)


def scramble(cube,seed=54,length=24):
    """A reproducible legal walk; recompute bands for shape-changing models."""
    if cube.puzzle_kind=='helicopter_14' and hasattr(cube,'frames'):
        from cube.helicopter_14_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    if cube.puzzle_kind=='lanlan_clover_pyraminx':
        from cube.clover_pyraminx_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    if cube.puzzle_kind=='lanlan_flower_copter':
        from cube.flower_copter_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    if cube.puzzle_kind=='lanlan_hexagram':
        from cube.hexagram_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    if cube.puzzle_kind=='lanlan_pisces':
        from cube.pisces_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    if cube.puzzle_kind in ('mf8_twins','mf8_suncube_2'):
        if cube.puzzle_kind=='mf8_twins':
            if getattr(cube,'geometry_profile',None)=='pcubes-skewby-twins-v1':from cube.twins_pcubes_aligned import scrambled
            else:from cube.twins_aligned import scrambled
        else:from cube.suncube_aligned import scrambled
        cube.restore(scrambled(seed,length));return cube
    from random import Random
    rng=Random(seed);previous=None
    for _ in range(length):
        choices=list(legal_moves(cube));rng.shuffle(choices)
        choices.sort(key=lambda m: (getattr(m,'axis',m)==getattr(previous,'axis',previous)))
        for move in choices:
            try:
                candidate=cube.clone();candidate.apply_move(move)
            except ValueError:continue
            cube.apply_move(move);previous=move;break
        else:raise ValueError('No legal teaching move')
    if cube.is_solved():cube.apply_move(legal_moves(cube)[0])
    return cube


def signature(cube):
    from demo.solutions import state_signature
    if hasattr(cube,'cubies'):return state_signature(cube)
    if isinstance(getattr(cube,'pieces',None),dict):
        return tuple(sorted((position,piece.home,tuple(tuple(round(v,8) for v in row) for row in piece.frame))
                            for position,piece in cube.pieces.items()))
    return tuple(cube.colors),getattr(cube,'frames',None)
