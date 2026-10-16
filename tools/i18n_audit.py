"""审计中/英/日三份文案是否齐全（找出缺失键）。

用法：
    python tools/i18n_audit.py           # 打印缺失键
    python tools/i18n_audit.py --check   # 有缺失则退出码 1（可用于 CI）

键集会不断增长；只有当同一个键出现在某语言、却在其它语言缺失时才算问题。
键本身只用一种语言（如某些动态拼接键）时，各语言的键集应完全一致。
"""

import os
import sys

os.environ.setdefault("KIVY_NO_ARGS", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def audit():
    from app.i18n import CATALOG, LANGUAGES
    keys = {lang: set(CATALOG.get(lang, {})) for lang in LANGUAGES}
    union = set().union(*keys.values())
    missing = {lang: sorted(union - keys[lang]) for lang in LANGUAGES}
    return union, missing


def main(argv):
    union, missing = audit()
    total = len(union)
    print("keys per language:")
    for lang, _ in ((l, None) for l in ("zh", "en", "ja")):
        print("  %s: %d" % (lang, total - len(missing.get(lang, []))))
    any_missing = False
    for lang, items in missing.items():
        if items:
            any_missing = True
            print("\n[%s] missing %d:" % (lang, len(items)))
            for key in items:
                print("  " + key)
    if not any_missing:
        print("\nall languages complete (%d keys)" % total)
    if any_missing and "--check" in argv:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
