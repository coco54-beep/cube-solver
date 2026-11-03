"""Large material meshes keep their colours and triangles within GLES limits."""
import pytest
from renderer.mesh_batches import triangle_batches


def test_small_mesh_uses_existing_buffers_and_empty_mesh_clears_draws():
    vertices=[float(i) for i in range(21)];indices=[0,1,2]
    batches=list(triangle_batches(vertices,indices))
    assert len(batches)==1 and batches[0][0] is vertices and batches[0][1] is indices
    assert list(triangle_batches([],[]))==[]


def test_large_mesh_preserves_every_ordered_triangle_and_all_vertex_attributes():
    count=70002
    vertices=[float(i*7+j) for i in range(count) for j in range(7)]
    indices=list(range(count))+[59998,60000,0,70000,3,69999]
    batches=list(triangle_batches(vertices,indices));assert len(batches)>1
    recovered=[]
    for points,triangles in batches:
        assert len(points)//7<=60000 and max(triangles)<60000 and len(triangles)%3==0
        for i in triangles:
            attributes=points[i*7:(i+1)*7];source=int(attributes[0])//7
            assert attributes==vertices[source*7:(source+1)*7]
            recovered.append(source)
    assert recovered==indices


def test_shared_vertices_at_a_batch_boundary_are_rebased_without_seam_cracks():
    vertices=list(range(6*7));indices=[0,1,2,2,3,4,4,5,0]
    result=list(triangle_batches(vertices,indices,limit=4))
    assert len(result)==3
    assert [tuple(v[k*7]//7 for k in ix) for v,ix in result]==[(0,1,2),(2,3,4),(4,5,0)]


@pytest.mark.parametrize('vertices,indices,stride,limit',[
    ([0]*21,[0,1,3],7,60000),([0]*21,[-1,1,2],7,60000),
    ([0]*21,[0,1],7,60000),([0]*20,[0,1,2],7,60000),
    ([0]*21,[0,1,2],7,65536),([0]*21,[0,1,2],7,2)])
def test_invalid_buffers_fail_before_upload(vertices,indices,stride,limit):
    with pytest.raises(ValueError):list(triangle_batches(vertices,indices,stride,limit))
