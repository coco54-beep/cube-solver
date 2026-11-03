"""Curved Drawing3 panels must retain the new independent body identities."""
import json
from collections import Counter
from types import SimpleNamespace
import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union
from cube.twins_pcubes import TwinsPCubesState
from cube.twins_cad_material import structure as cad
from cube.twins_display import data,panels,surfaces
from cube.twins_pcubes_aligned import generators
from cube.appearance import transform_frame
from cube.polyhedral import CUBE,dot


def flat(poly,face):
    axes=[i for i,n in enumerate(CUBE[face]) if not n]
    return Polygon([tuple(p[i] for i in axes) for p in poly])


def test_original_cad_curves_cover_all_six_faces_without_flat_substitution():
    c=TwinsPCubesState();drawing=cad()[2]
    assert sorted(data()['mapping'])==list(range(192))
    assert Counter(f for h,f,p in panels())=={i:32 for i in range(6)}
    for slot,(h,f,poly) in enumerate(panels()):
        assert (h,f)==c.panels[slot][:2]
        assert flat(poly,f).equals(flat(drawing[data()['mapping'][slot]][2],f))
    for face in range(6):
        shapes=[flat(p,f) for h,f,p in panels() if f==face]
        assert sum(p.area for p in shapes)==pytest.approx(4.,abs=1e-7)
        assert unary_union(shapes).area==pytest.approx(4.,abs=1e-7)
    assert max(len(p) for h,f,p in panels())>40  # sampled arcs, not straight edges


@pytest.mark.parametrize('index',range(40))
def test_all_closed_exchanges_keep_curved_patches_equivariant(index):
    c=TwinsPCubesState();action,word=generators()[index];c.apply_moves(word)
    for slot,target in enumerate(action):
        h,f,p=panels()[slot];th,tf,tp=panels()[target]
        moved=tuple(transform_frame(c.frames[h],v) for v in p)
        normal=transform_frame(c.frames[h],CUBE[f])
        assert dot(normal,CUBE[tf])==pytest.approx(1)
        assert flat(moved,tf).hausdorff_distance(flat(tp,tf))<2e-5


def test_paint_owners_and_original_state_survive_skin_and_checkpoint_loading():
    from app.session import encode,decode
    from renderer.twins_view import TwinsView
    c=TwinsPCubesState().apply_moves(generators()[21][1][:2])
    c=decode(json.loads(json.dumps(encode(c))))
    before=c.signature();fingerprint=c.geometry_fingerprint
    assert len(surfaces())==len(c.frames)==166
    for h,row in enumerate(surfaces()):
        assert all(slot==-1 or panels()[slot][0]==h for p,n,slot in row)
    view=SimpleNamespace(home_surfaces=TwinsView.home_surfaces,piece_filter=None,cube=c)
    shown=TwinsView._surfaces(view,c)
    assert {s for p,n,color,s,layer,h,w in shown if s is not None}==set(range(192))
    assert all(color==c.paints[s] and h==panels()[s][0]
               for p,n,color,s,layer,h,w in shown if s is not None)
    edges=TwinsView._physical_outlines(view)
    for slot,(h,f,p) in enumerate(panels()):
        assert edges[slot][0][0]==transform_frame(c.frames[h],p[0])
    assert c.signature()==before and c.geometry_fingerprint==fingerprint


def test_curved_skin_is_in_both_platforms_production_asset_selection():
    from scripts.bundle_assets import windows_assets
    from pathlib import Path
    from configparser import ConfigParser
    from fnmatch import fnmatch
    root=Path(__file__).resolve().parents[1];name='cube/data/twins_pcubes_skin.bin'
    assert name in {p.relative_to(root).as_posix() for p in windows_assets()}
    spec=ConfigParser(interpolation=None);spec.read(root/'buildozer.spec',encoding='utf-8')
    assert not any(fnmatch(name,p.strip()) for p in spec['app']['source.exclude_patterns'].split(','))
