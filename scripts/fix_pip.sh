#!/usr/bin/env bash
set -u
echo "=== current pip ==="
/opt/buildvenv/bin/pip --version
echo "=== downgrade pip < 25 ==="
/opt/buildvenv/bin/pip install "pip<25" 2>&1 | tail -5
echo "=== after ==="
/opt/buildvenv/bin/pip --version
