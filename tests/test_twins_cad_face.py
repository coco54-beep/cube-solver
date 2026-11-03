"""CAD surface verification without claiming a solved Twins mechanism."""
import json,math
from pathlib import Path
from collections import Counter
import pytest
from tools.cad_face_regions import curves_from_entities,face_regions,split_curves,EPS,with_central_radius


def source():return json.loads((Path(__file__).parent/'data/twins_face_curves.json').read_text())


def test_original_entities_and_four_separate_central_arcs_are_preserved():
    data=source();curves=curves_from_entities(data['entities'])
    assert Counter(e['type'] for e in data['entities'])=={'ARC':12,'LINE':6,'LWPOLYLINE':1}
    assert Counter(c.kind for c in curves)=={'arc':12,'line':10}
    central=[c for c in curves if c.kind=='arc' and c.a==(0.,0.)]
    assert len(central)==4
    for angle in (0.,math.pi/2,math.pi,math.pi*1.5):
        point=(central[0].radius*math.cos(angle),central[0].radius*math.sin(angle))
        assert all(c.parameter(point) is None for c in central)
    for angle in (math.pi/4,math.pi*3/4,math.pi*5/4,math.pi*7/4):
        point=(central[0].radius*math.cos(angle),central[0].radius*math.sin(angle))
        assert sum(c.parameter(point) is not None for c in central)==1


@pytest.mark.parametrize('step',(1.,.5))
def test_all_drawn_cuts_close_into_thirty_two_regions_without_dangling_lines(step):
    from shapely.geometry import LineString,box
    from shapely.ops import unary_union,polygonize_full
    curves=curves_from_entities(source()['entities']);regions,paths=face_regions(curves,step)
    assert len(regions)==32 and abs(sum(p.area for p in regions)-4)<1e-7
    assert unary_union(regions).symmetric_difference(box(-1,-1,1,1)).area<1e-7
    polygons,cuts,dangles,invalid=polygonize_full(unary_union([LineString(p) for h,p in paths]))
    assert max(cuts.length,dangles.length,invalid.length)<1e-7
    assert len(polygons.geoms)==32
    by_handle={c.handle:c for c in curves if c.kind=='arc'}
    for handle,points in paths:
        if handle in by_handle:
            assert all(by_handle[handle].parameter(p) is not None for p in points)


@pytest.mark.parametrize('radius',(None,2.6,3.0))
def test_export_is_a_closed_outer_shell_with_192_face_groups_not_a_rigid_piece_claim(tmp_path,radius):
    from tools.preview_twins_cad import export_shell
    from cube.polyhedral import dot,cross
    curves=curves_from_entities(source()['entities'])
    if radius is not None:curves=with_central_radius(curves,radius)
    regions,paths=face_regions(curves)
    output=tmp_path/'twins-cad-shell.obj';summary=export_shell(regions,output)
    assert summary['face_patches']==192
    vertices=[];faces=[];groups=[]
    for line in output.read_text().splitlines():
        if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append(tuple(int(s)-1 for s in line.split()[1:]))
        elif line.startswith('g '):groups.append(line)
    edges=Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1]))
    assert set(edges.values())=={2} and len(vertices)-len(edges)+len(faces)==2
    assert len(groups)==len(set(groups))==192
    volume=sum(dot(vertices[a],cross(vertices[b],vertices[c]))/6 for a,b,c in faces)
    assert abs(volume-8)<1e-6
    assert 'patches are not rigid cubies' in output.read_text()


@pytest.mark.parametrize('radius',(2.6,2.8,3.0))
def test_radius_preview_rejoins_original_curves_and_preserves_complete_face(radius):
    from shapely.geometry import LineString
    from shapely.ops import unary_union,polygonize_full
    original=curves_from_entities(source()['entities'])
    changed=with_central_radius(original,radius)
    for before,after in zip(original,changed):
        if before.kind!='arc' or before.a!=(0.,0.):
            assert before==after;continue
        assert after.radius==pytest.approx(radius/5)
        for t in (0.,1.):
            point=after.point(t)
            assert sum(c.parameter(point) is not None for c in changed if c.kind=='arc' and c.a!=(0.,0.))==1
    regions,paths=face_regions(changed)
    assert len(regions)==32 and sum(p.area for p in regions)==pytest.approx(4.)
    polygons,cuts,dangles,invalid=polygonize_full(unary_union([LineString(p) for h,p in paths]))
    assert max(cuts.length,dangles.length,invalid.length)<1e-7
    assert with_central_radius(original,radius)==changed  # No accumulated edits.


@pytest.mark.parametrize('radius',(0.,-1.,5.,float('nan'),float('inf')))
def test_invalid_radius_is_rejected(radius):
    with pytest.raises(ValueError):with_central_radius(curves_from_entities(source()['entities']),radius)
