#!/usr/bin/env bash
for host in github.com dl.google.com pypi.org raw.githubusercontent.com; do
  code=$(timeout 15 curl -sS -o /dev/null -w "%{http_code}" "https://$host" 2>/dev/null)
  echo "$host -> ${code:-FAIL}"
done
