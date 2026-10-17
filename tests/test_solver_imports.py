"""Solver imports and APK filters must preserve the bundled two-phase engine."""
import configparser
from fnmatch import fnmatch
from pathlib import Path
import subprocess
import sys


ROOT=Path(__file__).resolve().parents[1]


def test_irregular_import_does_not_require_twophase():
    script="""
import sys,importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='twophase' or fullname.startswith('twophase.'):
            raise ModuleNotFoundError('two-phase deliberately unavailable')
sys.meta_path.insert(0,Block())
from solver.polyhedral import solve_polyhedral
from solver.result import SolveResult
assert 'solver.solver3' not in sys.modules
assert 'solver.solver4' not in sys.modules
from solver import solve_2x2
assert callable(solve_2x2)
assert 'solver.solver3' not in sys.modules
"""
    subprocess.run([sys.executable,'-c',script],cwd=ROOT,check=True,
                   capture_output=True,timeout=15)


def test_android_filters_keep_twophase_python_sources():
    config=configparser.ConfigParser(interpolation=None)
    config.read(ROOT/'buildozer.spec',encoding='utf-8')
    patterns=[p.strip() for p in config['app']['source.exclude_patterns'].split(',')]
    sources=list((ROOT/'kociemba-src/package_src/twophase').glob('*.py'))
    assert any(p.name=='defs.py' for p in sources)
    for source in sources:
        relative=source.relative_to(ROOT).as_posix()
        assert not any(fnmatch(relative,pattern) for pattern in patterns),relative
