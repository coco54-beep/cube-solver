"""Verify that APK bytecode and solver assets match this build's staged sources."""
import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('apk',type=Path)
    parser.add_argument('--source-root',type=Path)
    parser.add_argument('--abi',choices=('arm64-v8a','x86_64'),default='arm64-v8a')
    parser.add_argument('--output',default='reports/android-test/1.2.21/package-check.json')
    args=parser.parse_args()
    workspace=Path(__file__).resolve().parents[1]
    root=args.source_root or workspace
    stage=workspace/'.buildozer/android/app'
    expected={}
    for folder in ('app','cube','demo','renderer','services','solver','ui','vision','twophase',
                   'kociemba-src/package_src/twophase'):
        for source in (root/folder).rglob('*.py'):
            relative=source.relative_to(root)
            assert digest(source.read_bytes())==digest((stage/relative).read_bytes()),relative
            bytecode=relative.with_suffix('.pyc')
            expected[bytecode.as_posix()]=digest((stage/bytecode).read_bytes())
    for source in [root/'main.py',root/'primitives.py']:
        relative=source.relative_to(root)
        assert source.read_bytes()==(stage/relative).read_bytes(),relative
        bytecode=relative.with_suffix('.pyc')
        expected[bytecode.as_posix()]=digest((stage/bytecode).read_bytes())
    for source in [root/'p4_table.bin',root/'joint_dist.bin',
                   *[p for p in (root/'solver').rglob('*') if p.suffix in ('.bin','.pkl','.json') and p.is_file()]]:
        relative=source.relative_to(root).as_posix()
        expected[relative]=digest(source.read_bytes())
    for folder in ('assets','ui','twophase','demo'):
        for source in (root/folder).rglob('*'):
            if (source.is_file() and (source.suffix in ('.kv','.ttf','.png','.jpg','.json')
                                     or (folder=='twophase' and not source.suffix))):
                expected[source.relative_to(root).as_posix()]=digest(source.read_bytes())
    verified=[]
    with zipfile.ZipFile(args.apk) as apk:
        assert any(n.startswith('lib/'+args.abi+'/') for n in apk.namelist())
        with tarfile.open(fileobj=apk.open('assets/private.tar'),mode='r|*') as archive:
            for member in archive:
                name=member.name.removeprefix('./')
                assert not name.startswith(('reports/','tmp/','tests/','scripts/')),name
                if name in expected:
                    assert digest(archive.extractfile(member).read())==expected[name],name
                    verified.append(name)
    assert set(verified)==set(expected),sorted(set(expected)-set(verified))
    result={'apk':str(args.apk.resolve()),'sha256':digest(args.apk.read_bytes()),
            'bytes':args.apk.stat().st_size,'verified_files':len(verified),'status':'pass'}
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
