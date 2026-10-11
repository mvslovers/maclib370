#!/bin/sh
# smoke.sh AS370 MACROS - assemble test/smoke.s with an as370 against an
# installed or staged macros/ directory (#3).
#
#   1. with -I MACROS it assembles at RC 0
#   2. control: without it, it does not -- so the macros came from MACROS,
#      not from a copy the as370 found by itself
#
# The -I goes once a released as370 searches <exedir>/../maclib370/macros
# (cc370 4d1fca9); see TODO.md.
#
# RC: 0 when both checks passed, 1 otherwise.

AS=$1
MAC=$2
[ -x "$AS" ] && [ -d "$MAC" ] || { echo "usage: smoke.sh AS370 MACROS"; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
fail=0

if "$AS" "$ROOT/test/smoke.s" -I "$MAC" -o "$W/a.obj" > "$W/log1" 2>&1 \
        && [ -s "$W/a.obj" ]; then
    echo "ok    smoke.s assembles against $MAC"
else
    echo "FAIL  smoke.s does not assemble against $MAC"; tail -20 "$W/log1"; fail=1
fi
if "$AS" "$ROOT/test/smoke.s" -o "$W/b.obj" > "$W/log2" 2>&1; then
    echo "FAIL  control: smoke.s assembles without maclib370"; fail=1
else
    echo "ok    control: without maclib370 it does not assemble"
fi
rm -rf "$W"
exit $fail
