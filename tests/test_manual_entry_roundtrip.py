"""Input representations must describe legal scrambles without retained history."""
import random
import pytest


@pytest.mark.parametrize('kind',('square1','square0','square2','super_square1'))
@pytest.mark.parametrize('seed',range(8))
def test_sq_empty_input_rebuilds_every_shape_colour_and_middle(kind,seed):
    if kind=='square1':
        from cube.square1 import Square1Cube,piece_colors
        from cube.square1_entry import Square1Entry
        source=Square1Cube();source.scramble(25,seed)
        entry=Square1Entry(empty=True)
        for layer,start,width,home in source.groups():
            slot=layer*12+start;entry.set_shape(slot,width)
            top,sides=piece_colors(home)
            for field,color in enumerate((top,)+sides):entry.paint(slot,field,color)
    else:
        from cube.square_family import SquareFamilyCube
        from cube.square_family_entry import SquareFamilyEntry
        source=SquareFamilyCube.solved(kind);source.scramble(25,seed)
        entry=SquareFamilyEntry(SquareFamilyCube.solved(kind),empty=True)
        for layer,start,width,home in source.groups():entry.choose_piece(layer*12+start,home)
    entry.middle=source.middle
    result=entry.to_cube()
    assert result.slots==source.slots and result.middle==source.middle


@pytest.mark.parametrize('family,n', [('mirror_tower',3),('mirror_pyraminx',3),('mirror_pyraminx',4),
                                      ('mirror_skewb',3),('fisher_skewb',3),('ghost_pyramid',3)])
def test_shape_cards_include_all_scrambled_pieces_and_visible_directions(family,n):
    from importlib import import_module
    from cube.mirror_tower import frame_key
    from cube.polyhedral_scramble import scramble
    from cube.mirror_pyraminx import placements
    symbol={'mirror_tower':'MirrorTowerCube','mirror_pyraminx':'MirrorPyraminxCube',
            'mirror_skewb':'MirrorSkewbCube','fisher_skewb':'FisherSkewbCube','ghost_pyramid':'GhostPyramidCube'}[family]
    cls=getattr(import_module('cube.'+family),symbol)
    source=cls.solved() if family=='mirror_tower' else cls.solved(n=n)
    if family=='ghost_pyramid':source.phase=0.
    scramble(source,20,81)
    pieces={}
    for pos,piece in source.pieces.items():
        if family=='mirror_tower':
            from cube.mirror_tower import placements as tower_placements
            options=tower_placements(piece.home,pos)
        else:options=placements(n,piece.home,pos,'skewb' if family in ('mirror_skewb','fisher_skewb','ghost_pyramid') else 'pyraminx')
        if family=='fisher_skewb':
            from cube.fisher_skewb import appearance
            assert appearance(piece.home,piece.frame) in {appearance(piece.home,f) for f in options}
        else:assert frame_key(piece.frame) in {frame_key(f) for f in options}
        pieces[pos]=piece
    result=cls(pieces) if family=='mirror_tower' else cls(pieces,n=n)
    assert result.labeled_state()==source.labeled_state()


@pytest.mark.parametrize('kind',('axis','windmill','fisher'))
@pytest.mark.parametrize('n',(3,4))
def test_coloured_shape_mod_cards_retain_physical_orientations(kind,n):
    from cube.shape_cube import AxisCube,WindmillCube,FisherCube
    from cube.mastermorphix import placements,make_piece
    cls={'axis':AxisCube,'windmill':WindmillCube,'fisher':FisherCube}[kind]
    source=cls.solved(n=n);source.apply_moves(['R','U','F2',"L'",'D','B'])
    result=cls.solved(n=n)
    for pos,piece in source.cubies.items():
        assert piece.frame in placements(piece.home,pos)
        result.cubies[pos]=make_piece(piece.home,pos,piece.frame,n)
    assert result.cubies==source.cubies


def test_pandora_six_face_colours_reconstruct_the_real_shell():
    from cube.shape_cube import PandoraCube
    from cube.pandora_entry import to_facelets,from_facelets
    from cube.shape_cube import faces_for
    from cube.mastermorphix import transform
    for seed in range(5):
        rng=random.Random(seed);source=PandoraCube.solved()
        source.apply_moves([rng.choice('URFDLB')+rng.choice(('',"'",'2')) for _ in range(20)])
        data=to_facelets(source);result=from_facelets(data,PandoraCube.solved())
        assert to_facelets(result)==data
        def shell(cube):
            return tuple(sorted((pos,tuple(sorted((color,tuple(sorted(tuple(round(v,6) for v in transform(p.frame,q)) for q in verts)))
                                                  for verts,color in faces_for('pandora',p.home))))
                                for pos,p in cube.cubies.items()))
        assert shell(result)==shell(source)


@pytest.mark.parametrize('kind,n',[
    ('pyraminx',2),('pyraminx',5),('skewb',3),('skewb',5),('dino',2),('dino',4),('dino4',2),
    ('megaminx',3),('megaminx',5),('moyu',3),('moyu',5),('fto',2),('fto',5),('football',3),('football',5),
    ('icosahedron',3),('icosahedron',5),('war_drum',3),('pentahedron',3),('skewb_ultimate',3),
    ('void_cube',3),('void_tower',3),('void_minx',3),('helicopter',3),('clover',3),('blossom',3),
    ('ivy',3),('super_ivy',3),('eight_petals',3),('mosaic',4),('tins',5),('dino_skewb',4),('dayan_dino_skewb',4),
    ('petal_tetrahedron',3),('petal_tetrahedron_nocentre',3),('petal_icosahedron',3),('petal_icosahedron_nocentre',3),
    ('pyraminx_duo',3),('coin_tetrahedron',3)])
def test_fixed_polyhedral_colour_input_rebuilds_legal_pieces_without_history(kind,n):
    from cube.polyhedral import PolyhedralPuzzle,solved_colors
    from cube.polyhedral_scramble import scramble
    from solver.polyhedral import identify
    source=PolyhedralPuzzle(kind,n);scramble(source,16,83)
    entered=PolyhedralPuzzle(kind,n,list(source.colors))
    state=identify(entered)
    assert sorted(state)==list(range(len(state)))
    if kind!='dino4':
        assert all(entered.colors[destination]==solved_colors(entered)[home] for home,destination in enumerate(state))


@pytest.mark.parametrize('kind',('circle_2','crazy_mercury','crazy_venus','crazy_earth','crazy_mars',
                                  'crazy_jupiter','crazy_saturn','crazy_uranus','crazy_neptune'))
def test_circle_input_rebuilds_internal_sectors_and_anchor(kind):
    from cube.circle_cube import Circle2Cube
    from cube.polyhedral import PolyhedralPuzzle
    from cube.polyhedral_scramble import scramble
    from solver.circle_cube import validate_circle
    source=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3)
    scramble(source,18,93)
    raw=Circle2Cube(colors=list(source.colors)) if kind=='circle_2' else PolyhedralPuzzle(kind,3,list(source.colors))
    result=raw.entered();validate_circle(result)
    assert result.colors==source.colors
    if kind=='circle_2':assert result.anchor==source.anchor
    for move in source.moves():
        a=source.clone();b=result.clone();a.apply_move(move);b.apply_move(move)
        assert a.colors==b.colors


@pytest.mark.parametrize('kind',('cuboid_224','cuboid_442','cuboid_234','cuboid_133','cuboid_335','cuboid_446','camouflage_3'))
def test_six_views_rebuild_changed_shape_without_piece_labels(kind):
    from cube.cuboid import CuboidCube
    from cube.cuboid_observation import SixViewDraft,project
    from cube.polyhedral_scramble import scramble
    source=CuboidCube.solved(kind);scramble(source,10,95)
    observed=SixViewDraft.from_cube(source)
    draft=SixViewDraft(kind,observed.state())
    result=draft.match(seconds=5.)
    assert result.status=='ok',(kind,result)
    def visible(cube):
        views=project(cube,draft.model)
        return tuple((tuple((color,depth) for color,group,depth in view),
                      tuple(sorted(tuple(i for i,(_,g,_) in enumerate(view) if g==group)
                                   for group in {g for color,g,depth in view if g}))) for view in views)
    # Group numbers are hidden piece labels; boundaries, colours and depth
    # must match even when identical internal pieces exchange identities.
    assert visible(result.cube)==visible(source)


def test_circle_entry_synchronizes_anchor_before_opening_twist(monkeypatch):
    from types import SimpleNamespace
    from cube.circle_cube import Circle2Cube
    from cube.polyhedral_scramble import scramble
    import ui.screens.polyhedral_screen as screen
    source=Circle2Cube();scramble(source,18,93)
    raw=Circle2Cube(colors=list(source.colors))
    assert raw.anchor!=source.anchor
    manager=SimpleNamespace(current='PolyhedralScreen')
    # Invoke through a lightweight subclass, retaining super() dispatch.
    class Harness(screen.PolyhedralScreen):
        def __init__(self):self._cube=raw
        def entry_can_edit(self):return True
        def entry_can_twist(self):return True
        def error(self,message):pytest.fail(message)
        @property
        def manager(self):return manager
    screen.PolyhedralScreen.open_twist(Harness())
    assert manager.current=='PolyhedralTwistScreen' and raw.anchor==source.anchor


@pytest.mark.parametrize('part',('edge','center'))
def test_mirror_input_rejects_repeated_noncorner_pieces(part):
    from types import SimpleNamespace
    from cube.mirror import MirrorCube
    from cube.mastermorphix import position_kind,placements,make_piece
    from ui.screens.mirror_screen import MirrorScreen
    cube=MirrorCube.solved(n=3)
    a,b=[pos for pos in cube.positions if position_kind(pos)==part][:2]
    cube.cubies[b]=make_piece(a,b,placements(a,b)[0],3)
    fake=SimpleNamespace(_cube=cube,_recorded=set(cube.positions),_all_positions=lambda:cube.positions,
                         hint=SimpleNamespace(text=''))
    assert MirrorScreen.check(fake) is None


@pytest.mark.parametrize('n',range(2,18))
def test_standard_cube_face_input_can_represent_every_supported_order(n):
    from cube.cube2 import Cube2
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    from cube.cube5 import Cube5
    from cube.cube_n import CubeN
    from cube.conversion import cubies_to_facelets,facelets_to_cubies
    from cube.validation import validate_2x2,validate_3x3,validate_4x4,validate_5x5
    from cube.validation_n import validate_nxn
    source={2:Cube2,3:Cube3,4:Cube4,5:Cube5}[n].solved() if n<=5 else CubeN.solved(n)
    source.apply_moves(['R','U','F2',"L'",'D','B'])
    data=cubies_to_facelets(source.cubies,n)
    assert cubies_to_facelets(facelets_to_cubies(data,n),n)==data
    errors={2:validate_2x2,3:validate_3x3,4:validate_4x4,5:validate_5x5}[n](data) if n<=5 else validate_nxn(data,n)
    assert not errors


@pytest.mark.parametrize('kind',('mirror','mastermorphix'))
@pytest.mark.parametrize('n',range(2,10))
def test_cube_shape_cards_cover_supported_orders(kind,n):
    from cube.mastermorphix import MastermorphixCube,placements,make_piece,geometry_signature
    from cube.mirror import MirrorCube,shape_signature
    cls=MirrorCube if kind=='mirror' else MastermorphixCube
    source=cls.solved(n=n);source.apply_moves(['R','U','F2',"L'",'D','B'])
    entered=cls.solved(n=n)
    for pos,piece in source.cubies.items():
        assert piece.frame in placements(piece.home,pos)
        entered.cubies[pos]=make_piece(piece.home,pos,piece.frame,n)
    if kind=='mirror':assert shape_signature(entered)==shape_signature(source)
    else:
        assert all(geometry_signature(entered.cubies[pos],entered.palette,n)==geometry_signature(p,source.palette,n)
                   for pos,p in source.cubies.items())


@pytest.mark.parametrize('kind',('axis','windmill','fisher','windmill_unequal','fisher_unequal','windmill_offset','fisher_offset'))
def test_merged_mirror_cards_retain_all_real_shapes_and_directions(kind):
    from cube import mirror_shape as shapes
    from cube.mastermorphix import make_piece
    cls={'axis':shapes.MirrorAxisCube,'windmill':shapes.MirrorWindmillCube,'fisher':shapes.MirrorFisherCube,
         'windmill_unequal':shapes.MirrorUnequalWindmillCube,'fisher_unequal':shapes.MirrorUnequalFisherCube,
         'windmill_offset':shapes.MirrorOffsetWindmillCube,'fisher_offset':shapes.MirrorOffsetFisherCube}[kind]
    source=cls.solved();source.apply_moves(['R','U','F2',"L'",'D','B'])
    entered=cls.solved();group_of,groups=shapes.shape_groups(kind)
    for pos,piece in source.cubies.items():
        representative=groups[group_of[piece.home]][0]
        target=shapes.shell_signature(kind,piece.home,piece.frame)
        home,frame=next((h,f) for h,f in shapes.shape_orientations(kind,representative,pos) if shapes.shell_signature(kind,h,f)==target)
        entered.cubies[pos]=make_piece(home,pos,frame,3)
    entered=shapes.normalize_shape_input(entered)
    assert all(shapes.shell_signature(kind,entered.cubies[pos].home,entered.cubies[pos].frame)==shapes.shell_signature(kind,p.home,p.frame)
               for pos,p in source.cubies.items())


@pytest.mark.parametrize('n',(4,5,6,7,8,9))
def test_identical_mirror_centres_do_not_require_hidden_piece_ids(n):
    from cube.mirror import MirrorCube,normalize_entry,shape_signature
    from cube.mastermorphix import placements,make_piece
    source=MirrorCube.solved(n=n)
    # One selected centre card can describe several geometrically identical
    # centres. Replace a centre by a repeated identity with the same shell.
    maxc=max(max(map(abs,p)) for p in source.positions)
    homes=[p for p in source.positions if p[2]==maxc and abs(p[0])<maxc and abs(p[1])<maxc and p[0]==p[1]!=0]
    a=homes[0];b=(-a[0],a[1],a[2])
    repeated=source.clone();repeated.cubies[b]=make_piece(a,b,placements(a,b)[0],n)
    assert shape_signature(repeated)==shape_signature(source)
    result=normalize_entry(repeated)
    assert {p.home for p in result.cubies.values()}==set(result.positions)
    assert shape_signature(result)==shape_signature(repeated)
