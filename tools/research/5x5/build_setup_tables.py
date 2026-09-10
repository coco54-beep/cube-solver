"""离线预建 5x5 中心 setup 表，写入随包目录 solver/center5/data/。

设备首启无需 BFS：get_setup_table 会优先加载这里生成的表（见 setup_cache）。
当基元、合法动作集或置换约定变化时，缓存键自动失效；需重新运行本脚本。

用法：
    python tools/research/5x5/build_setup_tables.py

生成结果（每张 ~0.4MB）随 APK 发布；.gitignore 已反忽略该目录。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from solver.center5 import setup_cache  # noqa: E402
from solver.center5.primitives import (  # noqa: E402
    CENTER_PRIMITIVES,
    EDGE_COMM4,
)


def main() -> int:
    primitives = list(CENTER_PRIMITIVES) + [EDGE_COMM4]
    out_dir = setup_cache._bundled_dir()
    print("输出目录: %s" % out_dir)
    for prim in primitives:
        path = setup_cache.dump_setup_table(prim, out_dir)
        size_mb = os.path.getsize(path) / 1e6
        table = setup_cache.get_setup_table(prim)
        print("  %-14s -> %-16s %6d states  %.2f MB"
              % (prim.name, os.path.basename(path), table.size(), size_mb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
