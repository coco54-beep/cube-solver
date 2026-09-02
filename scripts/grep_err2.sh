#!/usr/bin/env bash
grep -n -iE "error:|FAILED|BUILD FAILED|Exception|could not|cannot|unsupported|what went wrong|FAILURE" /mnt/d/coco/cube-solver/build_apk.log | tail -30
