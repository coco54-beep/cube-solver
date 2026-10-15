"""Build and verify a portable x64 folder, then zip it for GitHub Releases."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.constants import APP_VERSION

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    assert sys.platform=='win32' and struct.calcsize('P')==8,'Build using 64-bit Windows Python'
    assert (ROOT/'p4_table.bin').stat().st_size>100000000,'Materialise the LFS solver table first'
    output=ROOT/'bin'/f'windows-{APP_VERSION}'
    if not args.skip_build:
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm',
                        '--distpath',str(output),'--workpath',str(ROOT/'build'/f'windows-{APP_VERSION}'),
                        str(ROOT/'packaging/windows.spec')],cwd=ROOT,check=True)
    bundle=output/'CubeSolver';internal=bundle/'_internal'
    assets=[]
    for folder in ('assets','solver','ui','docs','twophase','demo'):
        for source in (ROOT/folder).rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts and source.suffix not in ('.py','.pyc','.log'):
                assets.append(source)
    assets.extend(ROOT/name for name in ('p4_table.bin','joint_dist.bin','README.md','README.zh-CN.md','README.ja.md','LICENSE'))
    for source in assets:
        target=internal/source.relative_to(ROOT)
        assert target.is_file() and digest(source)==digest(target),source.relative_to(ROOT)
    for dll in ('libEGL.dll','libGLESv2.dll','SDL2.dll'):
        assert (internal/dll).is_file(),dll
    report=output/'self-check.json'
    # Exercise the frozen entry point from a different working directory.
    subprocess.run([str(bundle/'CubeSolver.exe'),'--self-check',str(report)],cwd=output,
                   timeout=180,check=True)
    check=json.loads(report.read_text(encoding='utf-8'))
    assert check['status']=='pass' and check['version']==APP_VERSION
    for name in ('README.md','README.zh-CN.md','README.ja.md','LICENSE'):
        shutil.copy2(ROOT/name,bundle/name)
    shutil.copy2(report,bundle/'verification.json')
    archive=ROOT/'bin'/f'CubeSolver-{APP_VERSION}-windows-x64.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as stream:
        for file in sorted(bundle.rglob('*')):
            if file.is_file():stream.write(file,file.relative_to(output))
    manifest={'version':APP_VERSION,'platform':'windows-x64','archive':archive.name,
              'bytes':archive.stat().st_size,'sha256':digest(archive),
              'verified_assets':len(assets),'self_check':check}
    (ROOT/'bin'/f'CubeSolver-{APP_VERSION}-windows-x64.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (ROOT/'bin'/f'CubeSolver-{APP_VERSION}-windows-x64.sha256').write_text(
        f"{manifest['sha256']}  {archive.name}\n",encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)
if __name__=='__main__':main()
