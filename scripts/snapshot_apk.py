"""Capture only the APK's application sources and data before a long build."""
import argparse
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.bundle_assets import APPLICATION_ROOT_MODULES,RETIRED_TABLES,DEVELOPMENT_ONLY_FILES


def check_root_imports(root, sources):
    """Reject a snapshot that omits an imported application root module."""
    selected = set(sources)
    for source in sources:
        if source.suffix != '.py':
            continue
        tree = ast.parse(source.read_text(encoding='utf-8-sig'), filename=str(source))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom)
                     and not node.level and node.module else [])
            for name in names:
                dependency = root / (name.split('.')[0] + '.py')
                if dependency.is_file() and dependency not in selected:
                    raise ValueError(f'{source.relative_to(root)} imports omitted module {dependency.name}')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('destination',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    destination=args.destination.resolve()
    assert destination.is_relative_to(root/'tmp')
    assert not destination.exists(),'Use a new snapshot directory'
    destination.mkdir(parents=True)
    extensions={'.py','.kv','.png','.jpg','.json','.txt','.bin','.md','.ttf','.pkl','.java','.xml'}
    sources=[root/name for name in (*APPLICATION_ROOT_MODULES,'joint_dist.bin','p4_table.bin',
                                  'README.md','README.zh-CN.md','README.ja.md','LICENSE')]
    for folder in ('app','assets','cube','demo','renderer','services','solver','ui','vision','twophase','kociemba-src','android_src'):
        for source in (root/folder).rglob('*'):
            if (source.is_file() and '__pycache__' not in source.parts
                    and source.relative_to(root).as_posix() not in RETIRED_TABLES
                    and source.relative_to(root).as_posix() not in DEVELOPMENT_ONLY_FILES
                    and (source.suffix in extensions or (folder=='twophase' and not source.suffix))):
                sources.append(source)
    check_root_imports(root, sources)
    manifest={}
    for source in sources:
        relative=source.relative_to(root)
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        manifest[relative.as_posix()]=hashlib.sha256(target.read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'created':datetime.now().isoformat(),
                          'source':str(destination),'files':manifest},indent=2),encoding='utf8')
    print(f'{len(sources)} files captured in {destination}',flush=True)


if __name__=='__main__':main()
