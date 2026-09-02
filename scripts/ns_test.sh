#!/usr/bin/env bash
set -u
cd /tmp
rm -rf nstest
mkdir -p nstest/sub
cat > nstest/sub/x.py <<'EOF'
VAL = 42
EOF
# 临时移除 __init__.py 模拟缺失
cd /tmp/nstest
python3 - <<'PY'
import sys
sys.path.insert(0, '/tmp/nstest')
try:
    from sub import x
    print("namespace import OK:", x.VAL)
except Exception as e:
    print("namespace import FAIL:", type(e).__name__, e)
PY
echo "=== 模拟 .pyc import（p4a 用 pyc）==="
cd /tmp/nstest/sub
python3 -m py_compile x.py
ls -la /tmp/nstest/sub
