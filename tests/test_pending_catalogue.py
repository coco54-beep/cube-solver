"""Visible references must remain separate from playable profiles."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from candidate_puzzles import REQUESTED,PENDING_KINDS,REMOVED_KINDS,CATALOGUE_FAMILIES,catalogue_family
from ui.screens.irregular_directory_screen import (IrregularDirectoryScreen,picker_orders,picker_label,
    order_image,IMPLEMENTED_ORDERS)


def test_removed_requests_are_absent_from_all_catalogue_families():
    status=json.loads(Path('docs/expansion-progress.json').read_text(encoding='utf-8'))
    assert PENDING_KINDS|REMOVED_KINDS=={p['kind'] for p in status['removed_models']}
    assert len(PENDING_KINDS)==4 and not PENDING_KINDS&{e.kind for e in REQUESTED}
    assert not PENDING_KINDS&{p['kind'] for p in status['models']}
    assert status['counts']['mechanism_pending']==0
    for kind in PENDING_KINDS:
        assert catalogue_family(kind) is None
        assert all(kind not in kinds for kinds in CATALOGUE_FAMILIES.values())
        assert all(kind not in picker_orders(family) for family in CATALOGUE_FAMILIES)
        assert all(kind not in kinds for kinds in IMPLEMENTED_ORDERS.values())


@pytest.mark.parametrize('language',('zh','en','ja'))
def test_removed_models_have_no_search_or_photo_entry(language):
    from app.i18n import current_language,set_language,tr
    from ui.screens.home_screen import HomeScreen
    from ui.widgets.photo_entry import photo_groups
    before=current_language()
    try:
        set_language(language)
        entries=HomeScreen._search_entries(SimpleNamespace(puzzle_keys=tuple(CATALOGUE_FAMILIES)))
        for kind in PENDING_KINDS:
            matches=[r for r in entries if r[2]==kind]
            assert not matches
        assert not {k for family,kinds in photo_groups() for k in kinds}&PENDING_KINDS
    finally:set_language(before)


@pytest.mark.parametrize('kind',sorted(PENDING_KINDS))
def test_pending_routes_only_show_a_reference_without_constructing_an_engine(kind):
    calls=[];fake=SimpleNamespace(_show_pending=lambda *args,**kwargs:calls.append(args))
    IrregularDirectoryScreen.launch_order(fake,catalogue_family(kind),kind)
    IrregularDirectoryScreen.open_order_picker(fake,kind)
    assert calls==[(kind,),(kind,)]


def test_removed_reference_assets_are_excluded_from_windows_and_android():
    import configparser
    from fnmatch import fnmatch
    from scripts.bundle_assets import windows_assets
    assets={p.resolve() for p in windows_assets()}
    config=configparser.ConfigParser(interpolation=None);config.read('buildozer.spec',encoding='utf-8')
    extensions={s.strip() for s in config['app']['source.include_exts'].split(',')}
    excluded=[s.strip() for s in config['app']['source.exclude_patterns'].split(',')]
    for kind in PENDING_KINDS:
        path=Path(order_image(catalogue_family(kind),kind)).resolve()
        assert path not in assets
        assert any(fnmatch(path.relative_to(Path.cwd()).as_posix(),pattern) for pattern in excluded)


def test_pending_reference_keeps_family_picker_open_for_return_navigation():
    closed=[];opened=[]
    picker=SimpleNamespace(dismiss=lambda:closed.append(True))
    screen=SimpleNamespace(launch_order=lambda *args:opened.append(args))
    kind='lanlan_sunflower';family=catalogue_family(kind)
    IrregularDirectoryScreen.select_order(screen,picker,family,kind)
    assert not closed and opened==[(family,kind)]


def test_mislabelled_sun_cube_photo_is_not_a_second_gemini_entry():
    from candidate_puzzles import BY_KIND
    from ui.screens.home_screen import HomeScreen
    assert 'lanlan_4corners_plus' not in BY_KIND
    visible=picker_orders('edge_family')
    assert visible.count('mf8_suncube_2')==1 and 'mf8_suncube_2' in IMPLEMENTED_ORDERS['edge_family']
    entries=HomeScreen._search_entries(SimpleNamespace(puzzle_keys=('edge_family',)))
    assert sum(row[2]=='mf8_suncube_2' for row in entries)==1
    assert all(row[2]!='lanlan_4corners_plus' for row in entries)
