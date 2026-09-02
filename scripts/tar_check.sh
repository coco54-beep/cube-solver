#!/usr/bin/env bash
set -u
cd /tmp/apkcheck
tar tf assets/private.tar 2>/dev/null | grep -iE "\.ttf|joint_dist\.bin|p4_table\.bin|twophase/|app/application|main\.py" | head -40
echo "=== count ==="
tar tf assets/private.tar 2>/dev/null | wc -l
echo "=== top level ==="
tar tf assets/private.tar 2>/dev/null | grep -vE "/" | head -20
