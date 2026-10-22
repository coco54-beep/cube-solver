# PyInstaller recipe; run through scripts/build_windows.py on Windows.
from pathlib import Path
import os
import sys
os.environ.setdefault('KIVY_NO_ARGS','1')
os.environ.setdefault('KIVY_GL_BACKEND','angle_sdl2')
root=Path(SPECPATH).parent
sys.path.insert(0,str(root/'kociemba-src/package_src'))
from PyInstaller.utils.hooks import collect_submodules
from kivy_deps import angle,glew,sdl2
from kivy.tools.packaging.pyinstaller_hooks import get_deps_minimal,hookspath,runtime_hooks

deps=get_deps_minimal(window='sdl2',text='sdl2',image=('sdl2','pil','tex','dds'),
                      clipboard=('winctypes','sdl2'),audio=None,video=None,camera=None,spelling=None)
hidden=list(deps['hiddenimports'])
for package in ('app','cube','demo','renderer','services','solver','ui','vision','twophase'):
    hidden.extend(collect_submodules(package))
hidden.extend(('kivy_deps.angle','kivy_deps.glew','kivy_deps.sdl2',
               # Kivy's get_deps_minimal names these image_pil/image_sdl2/...,
               # which do not exist; the real provider modules are img_*.
               'kivy.core.image.img_dds','kivy.core.image.img_pil',
               'kivy.core.image.img_sdl2','kivy.core.image.img_tex'))
datas=[]
for folder in ('assets','solver','ui','docs','twophase','demo'):
    for path in (root/folder).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.py','.pyc','.log'):
            datas.append((str(path),str(path.relative_to(root).parent)))
for name in ('p4_table.bin','joint_dist.bin','README.md','README.zh-CN.md','README.ja.md','LICENSE'):
    datas.append((str(root/name),'.'))
binaries=list(deps['binaries'])
for dependency in (angle,glew,sdl2):
    for directory in dependency.dep_bins:
        binaries.extend((str(path),'.') for path in Path(directory).glob('*.dll'))

a=Analysis([str(root/'run_desktop.py')],pathex=[str(root/'kociemba-src/package_src'),str(root)],
           binaries=binaries,datas=datas,hiddenimports=sorted(set(hidden)),
           hookspath=hookspath(),runtime_hooks=runtime_hooks(),excludes=deps['excludes'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='CubeSolver',console=False,debug=False,
        strip=False,upx=False,contents_directory='_internal')
coll=COLLECT(exe,a.binaries,a.datas,name='CubeSolver',strip=False,upx=False)
