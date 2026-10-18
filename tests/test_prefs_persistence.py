"""Atomic preference persistence and migration without an Android device."""
import json

import pytest

from app import prefs


@pytest.fixture
def preference_paths(monkeypatch, tmp_path):
    current = tmp_path/'private'/'prefs.json'
    legacy = tmp_path/'legacy.json'
    monkeypatch.setattr(prefs, '_PREFS_FILE', str(current))
    monkeypatch.setattr(prefs, '_LEGACY_FILE', str(legacy))
    return current, legacy


def test_theme_and_calibration_preserved_together(preference_paths):
    current, _ = preference_paths
    prefs.set('theme_mode', 'light')
    prefs.set('photo_calibration_cube', {'codes': ['O', 'Y']})
    assert prefs.load() == {'theme_mode': 'light',
                            'photo_calibration_cube': {'codes': ['O', 'Y']}}
    assert json.loads(current.read_text(encoding='utf-8')) == prefs.load()


def test_legacy_migration_runs_only_when_private_file_missing(preference_paths):
    current, legacy = preference_paths
    legacy.write_text('{"theme_mode":"light"}', encoding='utf-8')
    assert prefs.load()['theme_mode'] == 'light'
    assert current.is_file()
    prefs.set('theme_mode', 'dark')
    assert prefs.load()['theme_mode'] == 'dark'


def test_failed_replacement_keeps_previous_preferences(monkeypatch, preference_paths):
    current, _ = preference_paths
    prefs.set('theme_mode', 'light')
    original = current.read_bytes()
    def fail_replace(*args):
        raise OSError('simulated storage failure')
    monkeypatch.setattr(prefs.os, 'replace', fail_replace)
    prefs.set('theme_mode', 'dark')
    assert current.read_bytes() == original
    assert not list(current.parent.glob('.prefs-*.tmp'))
