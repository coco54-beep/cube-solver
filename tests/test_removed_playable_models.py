"""Deleted models must not reappear through menus or old checkpoints."""
import configparser
import json
from fnmatch import fnmatch
from types import SimpleNamespace

import pytest

from candidate_puzzles import BY_KIND, CATALOGUE_FAMILIES, REMOVED_KINDS


def test_removed_models_have_no_catalogue_search_photo_or_tutorial_entry():
    from ui.screens.home_screen import HomeScreen
    from ui.screens.irregular_directory_screen import ORDERS, IMPLEMENTED_ORDERS
    from ui.widgets.photo_entry import photo_groups
    from demo.expanded_support import entry_screen
    rows = HomeScreen._search_entries(SimpleNamespace(puzzle_keys=tuple(CATALOGUE_FAMILIES)))
    assert not REMOVED_KINDS & set(BY_KIND)
    assert not REMOVED_KINDS & {r[2] for r in rows}
    assert not REMOVED_KINDS & {k for _, kinds in photo_groups() for k in kinds}
    for mapping in (CATALOGUE_FAMILIES, ORDERS, IMPLEMENTED_ORDERS):
        assert all(not REMOVED_KINDS & set(kinds) for kinds in mapping.values())
    assert all(entry_screen(kind) is None for kind in REMOVED_KINDS)


@pytest.mark.parametrize('kind,tag,page', (
    ('lanlan_pisces', 'cube.pisces:PiscesCube', 'PiscesInputScreen'),
    ('lanlan_master_clover', 'cube.master_clover:MasterCloverCube', 'MasterCloverTwistScreen'),
    ('planar_rhombic_12', 'cube.crazy_comet:CometCube', 'CometInputScreen'),
    ('lanlan_crazy_comet', 'cube.crazy_comet:CometCube', 'PolyhedralPlaybackScreen'),
))
def test_old_removed_session_is_skipped_before_loading_assets(tmp_path, monkeypatch, kind, tag, page):
    import app.session as session
    record = session.encode({'version': 1, 'app': {'puzzle_kind': kind}, 'page': page})
    # A malformed retired payload should never be decoded or load its model.
    record['v'][1][1]['v'].append(['cube', {'@': tag, 'v': {}}])
    app = SimpleNamespace(user_data_dir=str(tmp_path), root=SimpleNamespace(current='HomeScreen'))
    store = session.SessionStore(app)
    store.path.write_text(json.dumps(record), encoding='utf-8')
    def unexpected_decode(_):pytest.fail('Removed model was decoded')
    monkeypatch.setattr(session, 'decode', unexpected_decode)
    store.restore()
    assert app.root.current == 'HomeScreen'


def test_current_checkpoint_still_restores_and_removed_assets_do_not_ship():
    from app.session import encode, _removed_checkpoint
    from scripts.bundle_assets import windows_assets, ROOT, DEVELOPMENT_ONLY_FILES, audit
    assert not _removed_checkpoint(encode({'version': 1, 'app': {'puzzle_kind': 'cube'}, 'page': 'InputScreen'}))
    selected = {p.relative_to(ROOT).as_posix() for p in windows_assets()}
    removed_assets = {name for name in DEVELOPMENT_ONLY_FILES
                      if any(part in name for part in ('master_clover', 'pisces', 'planar_rhombic_12', 'crazy_comet'))}
    assert len(removed_assets) == 8 and not removed_assets & selected
    assert {'assets/puzzles/lanlan_comet_physical.png', 'solver/data/lanlan_comet_colour_group.bin'} <= selected
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / 'buildozer.spec', encoding='utf-8')
    patterns = config['app']['source.exclude_patterns'].split(',')
    assert all(any(fnmatch(name, pattern.strip()) for pattern in patterns) for name in removed_assets)
    assert audit()['windows_asset_bytes'] > 0
