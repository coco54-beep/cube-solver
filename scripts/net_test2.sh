#!/usr/bin/env bash
for url in \
  "https://codeload.github.com/kivy/python-for-android/tar.gz/refs/heads/master" \
  "https://raw.githubusercontent.com/kivy/python-for-android/master/README.md" \
  "https://github.com.cnpmjs.org/kivy/python-for-android.git" \
  "https://ghproxy.com/https://github.com/kivy/python-for-android.git" \
  ; do
  code=$(timeout 20 curl -sS -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  echo "$code  <-  $url"
done
