#!/usr/bin/env bash
for url in \
  "https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/8.13.0/gradle-8.13.0.pom" \
  "https://repo.maven.apache.org/maven2/" \
  "https://plugins.gradle.org/m2/" \
  "https://jcenter.bintray.com/" \
  ; do
  code=$(timeout 15 curl -sS -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  echo "$code  <-  $url"
done
