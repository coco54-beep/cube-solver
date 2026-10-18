"""Compact orientation search agrees with exhaustive small problems."""
from itertools import combinations
import random

import pytest

from cube.polyhedral import Move
from solver import icosahedron


def test_packed_edge_search_preserves_minimum_cost(monkeypatch):
    rng=random.Random(12345)
    vectors=rng.sample(range(1,256),8)
    words=[(Move(i,0,1),)*rng.randrange(1,6) for i in range(8)]
    generators={v:(len(word),word) for v,word in zip(vectors,words)}
    monkeypatch.setattr(icosahedron,'_edge_generators',lambda order:generators)
    for goal in rng.sample(range(1,256),40):
        costs=[]
        for count in range(1,5):
            for indices in combinations(range(8),count):
                value=0
                for index in indices: value^=vectors[index]
                if value==goal: costs.append(sum(len(words[i]) for i in indices))
        result=icosahedron._sparse_edge_orientation(tuple((goal>>i)&1 for i in range(8)),5)
        if not costs:
            assert result is None
        else:
            assert result is not None
            assert sum(map(len,result))==min(costs)
            value=0
            for word in result: value^=vectors[word[0].axis]
            assert value==goal


@pytest.mark.parametrize('name', ['_sparse_edge_orientation','_sparse_twist_orientation'])
def test_solved_orientations_do_not_build_search_tables(monkeypatch,name):
    def unexpected(*args): raise AssertionError('An already solved stage loaded tables')
    monkeypatch.setattr(icosahedron,'_edge_generators',unexpected)
    monkeypatch.setattr(icosahedron,'_twist_generators',unexpected)
    assert getattr(icosahedron,name)((0,)*12,5)==[]
