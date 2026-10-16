"""三份文案（中/英/日）键集应一致，避免新增文案时漏译。"""

import pytest

pytest.importorskip("kivy")


def test_language_key_sets_match():
    from app.i18n import CATALOG, LANGUAGES
    keys = {lang: set(CATALOG.get(lang, {})) for lang in LANGUAGES}
    union = set().union(*keys.values())
    missing = {lang: sorted(union - keys[lang]) for lang in LANGUAGES}
    assert not any(missing.values()), "\n".join(
        "%s missing: %s" % (lang, items) for lang, items in missing.items() if items)
