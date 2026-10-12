#!/usr/bin/env bash
set -eu
export VIRTUAL_ENV=/opt/buildvenv
export PATH=/opt/buildvenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /mnt/d/coco/cube-solver
exec buildozer android debug
