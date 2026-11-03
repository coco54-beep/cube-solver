"""Cross-check the offline order certificate against an independent BSGS."""
from random import Random
import pytest
from sympy.combinatorics import Permutation,PermutationGroup
from tools.exact_group_certificate import Certificate


@pytest.mark.parametrize('degree',(3,5,8,12,20))
@pytest.mark.parametrize('seed',range(4))
def test_incremental_orders_and_membership_match_independent_implementation(degree,seed):
    rng=Random(seed);base=list(range(degree));rng.shuffle(base)
    certificate=Certificate(degree,base);generators=[]
    for _ in range(4):
        p=list(range(degree));rng.shuffle(p);generators.append(Permutation(p))
        certificate.add(p);group=PermutationGroup(generators)
        assert certificate.order==group.order()
        for __ in range(8):
            q=list(range(degree));rng.shuffle(q)
            assert certificate.contains(q)==group.contains(Permutation(q))


def test_coupled_orbits_and_fixed_prefix_are_not_assumed_independent():
    # An involution swaps two pairs together; each orbit alone has order 2,
    # but the complete group has order 2, not their product 4.
    c=Certificate(6,(2,3,4,5));c.add((0,1,3,2,5,4))
    assert c.order==2 and not c.contains((0,1,3,2,4,5))


def test_every_strong_generator_word_and_transversal_replays_exactly():
    from solver.polyhedral import Word,compose,inverse
    from cube.polyhedral import Move
    atoms=((1,2,3,4,5,6,7,0),(1,0,2,3,4,5,6,7))
    c=Certificate(8,tuple(reversed(range(8))),track_words=True)
    for i,p in enumerate(atoms):c.add(p,Word(move=Move(i)))
    def replay(word):
        p=tuple(range(8))
        for m in word.flatten(8):
            for _ in range(m.amount%8):p=compose(p,atoms[m.axis])
        return p
    # The transposition's inverse is represented by seven copies, which is
    # still exact in this order-8 abstract action.
    for row in c.gens:
        for p in row:assert replay(c.words[p.tobytes()])==tuple(p)
    for level,row in enumerate(c.trans):
        for beta,p in row.items():assert replay(c.path_words[level][beta])==tuple(p)
