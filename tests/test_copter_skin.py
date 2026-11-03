"""Closed interior surfaces, not flat backing plates on a coloured shell."""
from collections import Counter
import math
import pytest
from cube.polyhedral import dot,cross,add,scale
from renderer.copter_skin import surfaces


def test_each_material_region_is_a_closed_positive_volume_triangle_shell():
    meshes=surfaces();assert len(meshes)==45 and all(meshes)
    assert sum(map(len,meshes))<18000
    volumes=[];painted=Counter()
    for parts in meshes:
        edges=Counter();volume=0.
        for triangle,normal,slot in parts:
            a,b,c=triangle;volume+=dot(a,cross(b,c))/6
            assert dot(cross(add(b,scale(a,-1)),add(c,scale(a,-1))),normal)>0
            for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                edge=tuple(sorted((tuple(round(v,6) for v in a),tuple(round(v,6) for v in b))))
                edges[edge]+=1
            if slot>=0:painted[slot]+=1
        assert all(count==2 for count in edges.values())
        assert volume>1e-4
        volumes.append(volume)
    assert sum(volumes)==pytest.approx(8.,abs=1e-9)
    assert set(painted)==set(range(72))
