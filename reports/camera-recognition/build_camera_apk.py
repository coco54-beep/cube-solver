import os
os.environ['VIRTUAL_ENV'] = '/opt/buildvenv'
os.environ['PATH'] = '/opt/buildvenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
from buildozer import Buildozer
os.chdir('/mnt/d/coco/cube-solver')
builder = Buildozer('buildozer.spec')
builder.config.set('app', 'source.dir', '/mnt/d/coco/cube-solver/tmp/apk-source-1.2.22-camera-20261015')
builder.run_command(['android', 'debug'])
