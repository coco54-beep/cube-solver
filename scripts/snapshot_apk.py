"""Capture only the APK's application sources and data before a long build."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil


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
    extensions={'.py','.kv','.png','.jpg','.json','.txt','.bin','.md','.ttf','.pkl'}
    sources=[root/name for name in ('main.py','primitives.py','joint_dist.bin','p4_table.bin',
                                  'README.md','README.zh-CN.md','LICENSE')]
    for folder in ('app','assets','cube','demo','docs','renderer','services','solver','ui','twophase','kociemba-src'):
        for source in (root/folder).rglob('*'):
            if (source.is_file() and '__pycache__' not in source.parts
                    and (source.suffix in extensions or (folder=='twophase' and not source.suffix))):
                sources.append(source)
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
