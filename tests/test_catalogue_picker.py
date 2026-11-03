"""Registered models must be visible through real menus, not just routes."""
from types import SimpleNamespace
import pytest
from app.i18n import tr,current_language,set_language
from candidate_puzzles import CATALOGUE_FAMILIES,catalogue_family,PENDING_KINDS
from ui.screens.irregular_directory_screen import (picker_orders,picker_label,
    EDGE_TURNING_PUZZLES,ORDERS,IMPLEMENTED_ORDERS,order_image)


def test_edge_picker_keeps_registered_models_and_legacy_variants():
    visible=picker_orders('edge_family')
    assert visible[0]=='lanlan_flower_copter'
    assert set(visible)==set(CATALOGUE_FAMILIES['edge_family'])|set(EDGE_TURNING_PUZZLES)
    assert len(visible)==len(set(visible))
    assert visible==ORDERS['edge_family']
    assert tuple(k for k in visible if k not in PENDING_KINDS)==IMPLEMENTED_ORDERS['edge_family']
    assert order_image('edge_family','lanlan_flower_copter').endswith('lanlan_flower_copter.png')


@pytest.mark.parametrize('family,kinds',CATALOGUE_FAMILIES.items())
def test_every_registered_family_model_is_in_the_visible_picker(family,kinds):
    visible=picker_orders(family)
    assert set(kinds)<=set(visible)
    assert len(visible)==len(set(visible))


@pytest.mark.parametrize('language',('zh','en','ja'))
def test_registered_edge_cards_and_search_use_localized_model_names(language):
    from ui.screens.home_screen import HomeScreen
    before=current_language()
    try:
        set_language(language)
        expected=tr('directory.lanlan_flower_copter')
        assert picker_label('edge_family','lanlan_flower_copter')[0]==expected
        for kind in EDGE_TURNING_PUZZLES:
            assert picker_label('edge_family',kind)[0]==tr('edge.'+kind)
        entries=HomeScreen._search_entries(SimpleNamespace(puzzle_keys=('edge_family',)))
        matches=[r for r in entries if r[2]=='lanlan_flower_copter']
        assert len(matches)==1 and expected in matches[0][0]
        assert {r[2] for r in entries if r[2] is not None}==set(picker_orders('edge_family'))
        assert catalogue_family('lanlan_flower_copter')=='edge_family'
    finally:set_language(before)
