"""Build the reviewed source snapshot using the existing Android toolchain."""
from buildozer import Buildozer

builder = Buildozer('buildozer.spec')
builder.config.set('app', 'source.dir', '/mnt/d/coco/cube-solver/tmp/apk-1.2.39-20261102')
builder.run_command(['android', 'debug'])
