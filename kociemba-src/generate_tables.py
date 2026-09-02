"""Generate the hkociemba two-phase tables once, into <project_root>/twophase/.

The pruning/move/conj tables total ~63 MB. Generation takes ~30 minutes on
first run and happens at twophase.solver import time. Subsequent imports simply
load the (much faster) tables, so the APK ships the generated twophase/ folder.

Run from the project root:
    python kociemba-src/generate_tables.py

Watch progress in table_gen.log. Look for TABLE_GENERATION_DONE.
"""
import os
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_PKG_SRC = os.path.join(_ROOT, "kociemba-src", "package_src")
sys.path.insert(0, _PKG_SRC)

import twophase.defs as defs  # noqa: E402
# Redirect table storage to an absolute path so generation is CWD-independent.
defs.FOLDER = os.path.join(_ROOT, "twophase")

_t0 = time.time()
import twophase.solver as sv  # noqa: E402,F401  (triggers table generation)

print(f"tables ready in {time.time() - _t0:.1f} s -> {defs.FOLDER}", flush=True)

# Smoke test: an already-solved cube should come back as a 0-move solution.
_SOLVED = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
print("solved-cube smoke:", sv.solve(_SOLVED, 20, 3), flush=True)
print("TABLE_GENERATION_DONE", flush=True)
