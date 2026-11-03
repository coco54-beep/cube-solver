"""Shared Windows asset selection and an audit of Android table exclusions.

Retired tables stay in the checkout for offline experiments and recovery.
Only production bundles omit them; current solver tables remain offline assets.
"""
import configparser
from fnmatch import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT_MODULES = ('main.py', 'primitives.py', 'candidate_puzzles.py')
RETIRED_TABLES = {
    'solver/data/starminx_i_expanded_group.bin': ('solver/data/starminx_i_edges.bin',),
    'solver/data/twobar_table.bin': ('solver/data/two_bar_shapes.bin', 'solver/data/two_bar_group.bin'),
    'solver/data/bandaged_c_table.bin': ('solver/data/bandaged_c_shapes.bin', 'solver/data/bandaged_c_group.bin'),
    'solver/data/circle2_table.bin': ('solver/data/circle2_group.bin',),
    'solver/data/fused_table.bin': ('solver/data/fused_group.bin',),
    'solver/data/ai_cube_patterns.bin': ('solver/data/ai_shapes.bin', 'solver/data/ai_group.bin'),
    'solver/data/burr_cube_patterns.bin': ('solver/data/burr_shapes.bin', 'solver/data/burr_group.bin'),
    'solver/data/cuboid_442_patterns.bin': ('solver/data/cuboid_442_orientations.bin', 'solver/data/cuboid_442_group.bin'),
    'solver/data/cuboid_442_endgame.bin': ('solver/data/cuboid_442_orientations.bin', 'solver/data/cuboid_442_group.bin'),
}
ASSET_FOLDERS = ('assets', 'cube/data', 'solver', 'ui', 'twophase', 'demo')
DEVELOPMENT_ONLY_FILES = {
    'assets/demo.gif',
    'assets/puzzles/pending/lanlan_andromeda.jpg',
    'assets/puzzles/pending/lanlan_clover_pyraminx.jpg',
    'assets/puzzles/pending/lanlan_sunflower.jpg',
    'assets/puzzles/pending/vp_clover_dodecahedron.png',
    'assets/puzzles/lanlan_master_clover.png',
    'assets/puzzles/lanlan_pisces.png',
    'cube/data/master_clover_shell.bin',
    'solver/data/master_clover_colour_group.bin',
    'solver/data/pisces_colour_group.bin',
    'assets/puzzles/planar_rhombic_12.png',
    'assets/puzzles/lanlan_crazy_comet.png',
    'solver/data/crazy_comet_colour_group.bin',
}
ROOT_ASSETS = ('p4_table.bin', 'joint_dist.bin', 'README.md', 'README.zh-CN.md', 'README.ja.md', 'LICENSE')


def windows_assets(root=ROOT):
    root = Path(root)
    for folder in ASSET_FOLDERS:
        for path in sorted((root / folder).rglob('*')):
            if (path.is_file() and '__pycache__' not in path.parts
                    and path.suffix not in ('.py', '.pyc', '.log')
                    and path.relative_to(root).as_posix() not in RETIRED_TABLES
                    and path.relative_to(root).as_posix() not in DEVELOPMENT_ONLY_FILES):
                yield path
    for name in ROOT_ASSETS:
        yield root / name


def audit(root=ROOT):
    """Fail if the two packagers drift or a replacement asset is missing."""
    root = Path(root)
    config = configparser.ConfigParser(interpolation=None)
    config.read(root / 'buildozer.spec', encoding='utf-8')
    app = config['app']
    excludes = [p.strip() for p in app['source.exclude_patterns'].split(',')]
    includes = [p.strip() for p in app['source.include_patterns'].split(',')]
    rows = []
    for name, replacements in RETIRED_TABLES.items():
        assert any(fnmatch(name, p) for p in excludes), f'Android still bundles {name}'
        assert not any(fnmatch(name, p) for p in includes), f'Android re-includes {name}'
        for replacement in replacements:
            assert (root / replacement).is_file(), f'Missing replacement: {replacement}'
        path = root / name
        rows.append({'path': name, 'bytes': path.stat().st_size if path.exists() else 0,
                     'replacements': replacements})
    selected = {p.relative_to(root).as_posix(): p for p in windows_assets(root)}
    assert not (selected.keys() & RETIRED_TABLES.keys())
    assert not (selected.keys() & DEVELOPMENT_ONLY_FILES)
    assert 'docs' in [p.strip() for p in app['source.exclude_dirs'].split(',')]
    omitted=[root/name for name in DEVELOPMENT_ONLY_FILES]
    omitted.extend(p for p in (root/'docs').rglob('*') if p.is_file())
    # Every other solver table must still ship, including the complete
    # bandage layout/group assets and the active Camouflage tables.
    for path in sorted((*((root / 'solver/data').glob('*.bin')),
                        *((root / 'cube/data').glob('*.bin')))):
        name = path.relative_to(root).as_posix()
        if name in RETIRED_TABLES or name in DEVELOPMENT_ONLY_FILES:
            continue
        assert name in selected, f'Windows lost active table: {name}'
        assert not any(fnmatch(name, p) for p in excludes), f'Android lost active table: {name}'
    return {'excluded_tables': rows, 'excluded_bytes': sum(r['bytes'] for r in rows),
            'excluded_development_bytes':sum(p.stat().st_size for p in omitted if p.is_file()),
            'windows_asset_bytes': sum(p.stat().st_size for p in selected.values()),
            'largest_retained_assets': [{'path': n, 'bytes': p.stat().st_size}
                for n, p in sorted(selected.items(), key=lambda item: item[1].stat().st_size,
                                   reverse=True)[:10]]}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
