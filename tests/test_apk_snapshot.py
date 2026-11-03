"""Regression coverage for missing root modules in the Android snapshot."""
from pathlib import Path
import pytest
from scripts.bundle_assets import APPLICATION_ROOT_MODULES
from scripts.snapshot_apk import check_root_imports


def test_catalog_is_a_required_application_module():
    assert 'candidate_puzzles.py' in APPLICATION_ROOT_MODULES


def test_root_dependency_cannot_be_silently_omitted(tmp_path):
    screen=tmp_path/'screen.py'
    screen.write_text('from candidate_puzzles import BY_KIND\n',encoding='utf8')
    catalog=tmp_path/'candidate_puzzles.py'
    catalog.write_text('BY_KIND={}\n',encoding='utf8')
    with pytest.raises(ValueError,match='candidate_puzzles.py'):
        check_root_imports(tmp_path,[screen])
    check_root_imports(tmp_path,[screen,catalog])


def test_application_imports_fit_snapshot_root_modules():
    root=Path(__file__).resolve().parents[1]
    sources=[root/name for name in APPLICATION_ROOT_MODULES]
    for folder in ('app','cube','demo','renderer','services','solver','ui','vision'):
        sources.extend((root/folder).rglob('*.py'))
    check_root_imports(root,sources)
