#!/usr/bin/env bash
grep -n -iE "error|failed|exception|traceback|cannot|not found|unsupported|stderr" /mnt/d/coco/cube-solver/build_apk.log | tail -45
