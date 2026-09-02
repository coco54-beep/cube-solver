#!/usr/bin/env bash
grep -n -iE "gradle|FAILURE|What went wrong|Could not|Exception|Downloading|Connection|timed out|BUILD" /mnt/d/coco/cube-solver/build_apk.log | tail -30
