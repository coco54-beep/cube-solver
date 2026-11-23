"""Photographed shells: real pieces, independent input and production solving."""
from collections import Counter
import json
import pytest

SOLIDS=(('rhombic_3',3),('rhombic_4',4),('rhombic_mask_4',4),('caneball_4',4))
DODECAHEDRONS=(('dodecahedron_2',2),('dodecahedron_3',3))
POLYS=('skewb_rhombic','jewel_fto','rua','helicopter_14')


def visible(cube):
    from cube.shape_cube import faces_for
    from cube.mastermorphix import transform
    return tuple(sorted((color,tuple(sorted(tuple(round(x,6) for x in transform(p.frame,v)) for v in face)))
                        for p in cube.cubies.values() for face,color in faces_for(cube.puzzle_kind,p.home,cube.n)
                        if color>=0))


def reenter(source):
    """Match only observed coloured surfaces, with no hidden identity witness."""
    from cube.mastermorphix import placements,make_piece
    from cube.shape_cube import faces_for
    from cube.mastermorphix import transform
    from cube.polyhedral import PolyhedralPuzzle
    if source.puzzle_kind=='helicopter_14' and hasattr(source,'frames'):
        # The public model now includes shape and hidden material. Its
        # independently reloaded observation cannot be a fixed-slot colour list.
        return type(source).from_observation(json.loads(json.dumps(source.observation_data())))
    if not hasattr(source,'cubies'):
        draft=PolyhedralPuzzle(source.puzzle_kind,source.n,[-1]*len(source.colors))
        for i,color in enumerate(source.colors):draft.colors[i]=color
        return draft
    def sig(home,frame):
        return tuple(sorted((color,tuple(sorted(tuple(round(v,6) for v in transform(frame,p)) for p in poly)))
                            for poly,color in faces_for(source.puzzle_kind,home,source.n) if color>=0))
    draft=type(source).solved(n=source.n)
    for pos,piece in source.cubies.items():
        wanted=sig(piece.home,piece.frame)
        choices=((h,f) for h in draft.positions for f in placements(h,pos) if sig(h,f)==wanted)
        home,frame=next(choices)
        draft.cubies[pos]=make_piece(home,pos,frame,source.n)
    assert visible(draft)==visible(source)
    return draft


@pytest.mark.parametrize('kind,n',SOLIDS)
def test_rhombic_shell_has_exact_core_and_real_closed_surfaces(kind,n):
    from cube.solid_shape_mods import FACTORIES,faces_for
    from cube.polyhedral import cross,dot,add,scale
    c=FACTORIES[kind].solved(n=n)
    assert len(c.cubies)==(26 if n==3 else 56)
    counts=Counter(color for home in c.positions for poly,color in faces_for(kind,home,n) if color>=0)
    if kind=='caneball_4':
        assert counts==Counter({i:7 for i in range(8)})
        assert all(sum(color>=0 for _,color in faces_for(kind,h,n))==1 for h in c.positions)
    else:assert all(counts[i]==(5 if n==3 else 4 if kind=='rhombic_mask_4' else 8) for i in range(12))
    assert counts.get(12,0)==(24 if kind=='rhombic_mask_4' else 0)
    for home in c.positions:
        edges=Counter()
        for polygon,color in faces_for(kind,home,n):
            assert len(polygon)>=3
            normal=cross(add(polygon[1],scale(polygon[0],-1)),add(polygon[2],scale(polygon[0],-1)))
            assert dot(normal,normal)>1e-16
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                edges[tuple(sorted((tuple(round(x,6) for x in a),tuple(round(x,6) for x in b))))]+=1
        assert edges and set(edges.values())=={2},home
    before=visible(c)
    for m in ('R','U','F','r' if n==4 else 'L'):
        for _ in range(4):c.apply_move(m)
        assert visible(c)==before


@pytest.mark.parametrize('kind,n,cut_ratio',(('rhombic_3',3,1/4),('rhombic_4',4,1/3)))
def test_rhombic_cut_distance_relative_to_axial_tip(kind,n,cut_ratio):
    from cube.solid_shape_mods import FACTORIES,faces_for

    fields=[(polygon,color) for home in FACTORIES[kind].solved(n=n).positions
            for polygon,color in faces_for(kind,home,n)]
    tip=max(abs(vertex[0]) for polygon,color in fields if color>=0 for vertex in polygon)
    cut_planes={round(polygon[0][0]/tip,8) for polygon,color in fields if color<0
                and all(abs(p[0]-polygon[0][0])<1e-8 for p in polygon)}
    expected={round(-cut_ratio,8),round(cut_ratio,8)}
    if n==4:
        expected.add(0.)
    assert cut_planes==expected


@pytest.mark.parametrize('kind,n',DODECAHEDRONS)
def test_dodecahedron_seams_are_symmetric_about_the_cubic_axes(kind,n):
    from math import dist
    from cube.solid_shape_mods import FACTORIES,faces_for

    fields=[(polygon,color) for home in FACTORIES[kind].solved(n=n).positions
            for polygon,color in faces_for(kind,home,n)]
    painted=[(polygon,color) for polygon,color in fields if color>=0]
    assert Counter(color for _,color in painted)=={i:2 if n==2 else 6 for i in range(12)}
    assert Counter(len(polygon) for polygon,_ in painted)==({4:24} if n==2 else {4:60,5:12})
    radius=max(dist(vertex,(0.,0.,0.)) for polygon,_ in painted for vertex in polygon)
    axis_cut_planes={round(polygon[0][0]/radius,8) for polygon,color in fields if color<0
                     and all(abs(p[0]-polygon[0][0])<1e-8 for p in polygon)}
    ratio=round((1/6)/.7,8)
    assert axis_cut_planes==({0.} if n==2 else {-ratio,ratio})


@pytest.mark.parametrize('kind,counts',(
    ('skewb_rhombic',(14,48,4,120)),('jewel_fto',(42,54,8,120)),
    ('rua',(38,72,12,180)),('helicopter_14',(32,32,12,180))))
def test_fixed_cuts_preserve_whole_pieces_and_have_only_real_axes(kind,counts):
    from cube.polyhedral import PolyhedralPuzzle,Move
    c=PolyhedralPuzzle(kind,3);g=c.geometry
    assert (len(g.pieces),len(g.stickers),len(g.spec.axes),360//g.spec.turn_order)==counts
    if kind=='skewb_rhombic':assert Counter(map(len,g.pieces))=={3:8,4:6}
    if kind=='rua':assert Counter(map(len,g.pieces))=={1:24,3:8,4:6}
    for move in c.moves():
        perm=g.permutation(move)
        assert sorted(perm)==list(range(len(c.colors)))
        for piece in g.pieces:assert len({g.stickers[perm[s]].piece for s in piece})==1
        work=c.clone()
        for _ in range(g.spec.order(move.axis)):work.apply_move(move)
        assert work.colors==c.colors
    if kind in ('jewel_fto','helicopter_14'):
        gold=c.color_count-1
        assert Counter(c.colors)[gold]==(6 if kind=='jewel_fto' else 8)
        assert all(len(g.pieces[s.piece])==1 for s in g.stickers if c.colors[g.pieces[s.piece][0]]==gold)


def test_four_layer_mask_matches_the_photographed_strips_and_gold_squares():
    from cube.solid_shape_mods import RhombicMask4Cube,faces_for
    from cube.polyhedral import CUBE,dot
    from math import sqrt
    cube=RhombicMask4Cube.solved(n=4)
    coloured=Counter();gold=Counter();by_piece=Counter()
    for home in cube.positions:
        fields=[(poly,color) for poly,color in faces_for(cube.puzzle_kind,home,4) if color>=0]
        by_piece[len(fields)]+=1
        for poly,color in fields:
            if color==12:
                normal=next(n for n in CUBE if all(abs(dot(n,p)-1)<1e-7 for p in poly))
                gold[normal]+=1
                assert len(poly)==4
                # The gold rims meet the wing/centre cuts, not tiny wing facets.
                axis=next(i for i,v in enumerate(normal) if v)
                assert all(abs(p[i])<=sqrt(2)-1+1e-7 for p in poly for i in range(3) if i!=axis)
            else:coloured[color,len(poly)]+=1
    assert coloured==Counter({(color,sides):2 for color in range(12) for sides in (3,4)})
    assert gold==Counter({normal:4 for normal in CUBE})
    assert by_piece=={1:48,3:8}


@pytest.mark.parametrize('kind,n',SOLIDS+DODECAHEDRONS+tuple((k,3) for k in POLYS))
def test_new_model_checkpoint_does_not_change_entered_state(kind,n):
    from demo.expanded_support import make_cube,scramble,signature
    from app.session import encode,decode
    source=scramble(make_cube(kind,n),20261026,30)
    draft=reenter(source)
    restored=decode(json.loads(json.dumps(encode(draft))))
    assert restored.puzzle_kind==kind and restored.n==n
    assert signature(restored)==signature(draft)
    assert not getattr(restored,'scramble_history',None)


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('kind,n',SOLIDS+DODECAHEDRONS+tuple((k,3) for k in POLYS))
def test_observed_scramble_reentry_solves_without_a_scramble_log(kind,n,length):
    from demo.expanded_support import make_cube,scramble
    from services.solve_service import SolveService,CancelToken
    from services.solution_cache import clear
    source=scramble(make_cube(kind,n),20261026+length,length)
    draft=reenter(source)
    before=visible(draft) if hasattr(draft,'cubies') else tuple(draft.colors)
    clear();answers=[]
    SolveService()._run(draft,answers.append,None,CancelToken())
    assert len(answers)==1 and answers[0].success,answers[0].message if answers else 'Missing result'
    replay=draft.clone()
    for move in answers[0].moves:replay.apply_move(move)
    assert replay.is_solved(),(kind,length,len(answers[0].moves))
    assert (visible(draft) if hasattr(draft,'cubies') else tuple(draft.colors))==before
    assert not getattr(draft,'scramble_history',None)
    clear()


def test_photographed_models_have_one_home_in_existing_categories():
    from candidate_puzzles import CATALOGUE_FAMILIES,BY_KIND
    from demo.expanded_support import entry_screen
    from app.i18n import tr
    for kind,n in SOLIDS+tuple((k,3) for k in POLYS):
        assert BY_KIND[kind].n==n
        assert sum(kind in names for names in CATALOGUE_FAMILIES.values())==1
        assert entry_screen(kind)==('ShapeCubeScreen' if (kind,n) in SOLIDS else
                                    'EdgeJumblingInputScreen' if kind=='helicopter_14' else 'PolyhedralScreen')
        assert not tr('directory.'+kind).startswith('directory.')


@pytest.mark.parametrize('kind,n',SOLIDS)
def test_twist_playback_and_entry_choose_the_same_shell_renderer(kind,n):
    from cube.solid_shape_mods import FACTORIES
    from renderer.shape_cube_view import SOLID_VIEWS
    from renderer.mastermorphix_view import cube_view_class_for
    from demo.expanded_support import view_class
    c=FACTORIES[kind].solved(n=n)
    assert cube_view_class_for(c) is view_class(kind) is SOLID_VIEWS[kind]


def test_caneball_invisible_corner_direction_does_not_reject_real_input():
    from demo.expanded_support import make_cube,scramble
    from cube.mastermorphix import placements,make_piece
    from solver.shape_cube import solve_shape_cube
    c=scramble(make_cube('caneball_4',4),54,30)
    before=visible(c)
    pos=next(p for p in c.positions if all(abs(v)==3 for v in p))
    piece=c.cubies[pos]
    for frame in placements(piece.home,pos):
        work=c.clone();work.cubies[pos]=make_piece(piece.home,pos,frame,4)
        assert visible(work)==before
        result=solve_shape_cube(work)
        assert result.success,result.message
        for move in result.moves:work.apply_move(move)
        assert work.is_solved()


def test_visible_illegal_corner_is_not_changed_to_force_a_solution():
    from demo.expanded_support import make_cube
    from cube.mastermorphix import placements,make_piece
    from cube.high_shape import normalize_high_shape_input
    from services.failures import classify
    from app.i18n import tr
    c=make_cube('rhombic_4',4)
    pos=next(p for p in c.positions if all(abs(v)==3 for v in p))
    piece=c.cubies[pos]
    frame=next(f for f in placements(piece.home,pos) if f!=piece.frame)
    c.cubies[pos]=make_piece(piece.home,pos,frame,4)
    before=visible(c)
    with pytest.raises(ValueError,match='shape.error.corner_twist'):
        normalize_high_shape_input(c)
    assert visible(c)==before
    assert classify('shape.error.corner_twist')==classify(tr('shape.error.corner_twist'))=='illegal'
