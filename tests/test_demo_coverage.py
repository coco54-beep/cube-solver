"""Every added tutorial uses a real model and a reversible, legal example."""
import pytest
from demo.coverage import modes,make_cube,lessons,complete_lessons,family,PROFILES
from demo.solutions import state_signature,inverse_demo_move,solved_demo_cube


@pytest.mark.parametrize('kind,n',modes())
def test_all_added_examples_finish_reverse_and_preserve_input(kind,n):
    source=make_cube(kind,n);before=state_signature(source)
    mode=n if kind=='cube' else (kind,n)
    assert type(solved_demo_cube(mode)) is type(source)
    for step in lessons(kind,n)+complete_lessons(kind,n):
        assert step['desc'] and step['cases']
        for case in step['cases']:
            work=case['initial'].clone();start=state_signature(work)
            for move in case['moves']:
                previous=state_signature(work);work.apply_move(move)
                assert state_signature(work)!=previous,(kind,n,move)
            assert work.is_solved()
            for move in reversed(case['moves']):work.apply_move(inverse_demo_move(move,work))
            assert state_signature(work)==start
    assert state_signature(source)==before


def test_pentacle_teaches_disc_alignment_and_core_layer():
    groups=lessons('pentacle',3)+complete_lessons('pentacle',3)
    moves=tuple(m for s in groups for c in s['cases'] for m in c['moves'])
    assert any(m.layer==0 and abs(m.amount)%90 for m in moves)
    assert any(m.layer==1 for m in moves)


def test_mixup_333_has_real_45_degree_middle_exchange():
    groups=lessons('mixup_333',3)+complete_lessons('mixup_333',3)
    assert any(m.amount%2 for s in groups for c in s['cases'] for m in c['moves'])


def test_ghost_examples_open_and_close_the_real_shell():
    case=complete_lessons('ghost',3)[0]['cases'][0]
    assert any(isinstance(m,str) and m.startswith('@G') for m in case['moves'])
    assert any(m[0] in 'RUF' for m in case['moves'])


def test_high_order_polyhedra_use_their_own_instructions():
    for kind in ('megaminx','skewb','pyraminx','moyu','dino'):
        assert family(kind,7)!='high_order'
        assert '按三阶' not in ''.join(PROFILES[family(kind,7)])
