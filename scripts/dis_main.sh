#!/usr/bin/env bash
set -u
cd /tmp/apkcheck
tar xf assets/private.tar main.pyc 2>/dev/null
python3 - <<'PY'
import dis, marshal, importlib.util, sys
data = open('/tmp/apkcheck/main.pyc','rb').read()
# pyc header varies; try to find marshal
import struct
# try to locate code object
try:
    co = marshal.loads(data[16:])  # 3.7+ header 16 bytes
except Exception:
    co = marshal.loads(data[12:])
dis.dis(co)
PY
