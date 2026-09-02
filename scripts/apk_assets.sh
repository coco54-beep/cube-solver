#!/usr/bin/env bash
set -u
cd /tmp/apkcheck
echo "=== assets tree ==="
find assets -maxdepth 3 2>/dev/null | head -40
echo "=== total assets size ==="
du -sh assets 2>/dev/null
echo "=== does it contain .zip bundles? ==="
find assets -iname "*.zip" -o -iname "*.pybundle*" 2>/dev/null | head
