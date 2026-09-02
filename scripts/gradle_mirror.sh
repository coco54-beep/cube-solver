#!/usr/bin/env bash
for url in \
  "https://mirrors.cloud.tencent.com/gradle/gradle-8.14.3-all.zip" \
  "https://mirrors.huaweicloud.com/gradle/gradle-8.14.3-all.zip" \
  "https://downloads.gradle.org/distributions/gradle-8.14.3-all.zip" \
  ; do
  code=$(timeout 20 curl -sS -o /dev/null -w "%{http_code}" -r 0-1024 "$url" 2>/dev/null)
  echo "$code  <-  $url"
done
