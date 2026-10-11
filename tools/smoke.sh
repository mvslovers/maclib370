#!/bin/sh
# smoke.sh AS370 MACROS - assemble test/smoke.s with an as370 against an
# installed or staged macros/ directory (#3, #6).
#
#   1. slot: a copy of the as370 in a throwaway tree that has MACROS at
#      <exedir>/../maclib370/macros assembles it with no -I (an as370 from
#      cc370 1.6.0 on searches that directory by itself)
#   2. control: the same copy in a tree without maclib370 does not -- so
#      in 1 the macros came from MACROS, not from anything the as370 found
#      elsewhere
#   3. with -I MACROS it assembles at RC 0, for any as370, to the same
#      object as in 1
#
# The copies keep an installed as370 out of it: cc370's install.sh puts
# maclib370 beside its as370, and that copy must not stand in for MACROS.
#
# RC: 0 when all of it passed, 1 otherwise.

AS=$1
MAC=$2
[ -x "$AS" ] && [ -d "$MAC" ] || { echo "usage: smoke.sh AS370 MACROS"; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
fail=0
slot=0

# the two trees: <W>/slot/{bin/as370,maclib370/macros}, <W>/bare/bin/as370
mkdir -p "$W/slot/bin" "$W/slot/maclib370" "$W/bare/bin"
cp "$AS" "$W/slot/bin/as370"
cp "$AS" "$W/bare/bin/as370"
cp -R "$MAC" "$W/slot/maclib370/macros"

if "$W/slot/bin/as370" "$ROOT/test/smoke.s" -o "$W/a.obj" > "$W/log1" 2>&1 \
        && [ -s "$W/a.obj" ]; then
    echo "ok    slot: smoke.s assembles with no -I, maclib370 beside as370"; slot=1
else
    echo "FAIL  slot: smoke.s does not assemble with no -I"; tail -20 "$W/log1"; fail=1
fi
if "$W/bare/bin/as370" "$ROOT/test/smoke.s" -o "$W/b.obj" > "$W/log2" 2>&1; then
    echo "FAIL  control: smoke.s assembles without maclib370"; fail=1
else
    echo "ok    control: without maclib370 it does not assemble"
fi
if "$W/bare/bin/as370" "$ROOT/test/smoke.s" -I "$MAC" -o "$W/c.obj" > "$W/log3" 2>&1 \
        && [ -s "$W/c.obj" ]; then
    echo "ok    -I: smoke.s assembles against $MAC"
else
    echo "FAIL  -I: smoke.s does not assemble against $MAC"; tail -20 "$W/log3"; fail=1
fi
if [ $slot = 1 ] && [ -s "$W/c.obj" ]; then
    if cmp -s "$W/a.obj" "$W/c.obj"; then
        echo "ok    slot and -I give the same object"
    else
        echo "FAIL  slot and -I give different objects"; fail=1
    fi
fi
rm -rf "$W"
exit $fail
