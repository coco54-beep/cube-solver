"""5x5 活动中心置换抽象（permutation.py）测试。

冻结方向：permutation[pos] = home；conjugate_cycle 正向 3-cycle a->b, b->c, c->a。
覆盖：恒等分解、单 3-cycle、逆 3-cycle、双换位（偶）之分解，以及大量随机偶置换的
「分解->重组」一致性。
"""

from solver.center5.permutation import (
    assert_decomposition_valid,
    compose_cycles,
    decompose_even_pos_to_home,
    permutation_parity,
)


def test_identity_decomposes_to_empty():
    assert decompose_even_pos_to_home(tuple(range(24))) == ()


def test_single_forward_3cycle():
    perm = list(range(24))
    perm[0], perm[1], perm[2] = 1, 2, 0  # 0->1, 1->2, 2->0
    assert permutation_parity(perm) == 0
    assert decompose_even_pos_to_home(perm) == ((0, 1, 2),)
    assert compose_cycles(((0, 1, 2),)) == perm


def test_inverse_3cycle():
    perm = list(range(24))
    perm[0], perm[1], perm[2] = 2, 0, 1  # 0->2, 2->1, 1->0
    assert permutation_parity(perm) == 0
    assert compose_cycles(decompose_even_pos_to_home(perm)) == perm


def test_double_transposition_is_even():
    perm = list(range(24))
    perm[0], perm[1] = 1, 0
    perm[2], perm[3] = 3, 2
    assert permutation_parity(perm) == 0
    cycles = decompose_even_pos_to_home(perm)
    assert compose_cycles(cycles) == perm


def test_odd_permutation_rejected():
    perm = list(range(24))
    perm[0], perm[1] = 1, 0
    perm[2], perm[3], perm[4] = 3, 4, 2
    assert permutation_parity(perm) == 1
    try:
        decompose_even_pos_to_home(perm)
    except ValueError:
        pass
    else:
        raise AssertionError("奇数置换应被拒绝")


def test_random_even_recompose():
    import random

    rng = random.Random(7)
    for _ in range(100):
        p = list(range(24))
        rng.shuffle(p)
        if permutation_parity(p) != 0:
            continue
        assert_decomposition_valid(p)
