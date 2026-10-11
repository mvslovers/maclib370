#!/bin/sh
# checkpkg.sh DIST VERSION - check the artifacts tools/package.py made (#3).
#
# Needs dpkg-deb and rpm (CI: Ubuntu).  The member count is taken from the
# repository, not written down here.
#
# RC: 0 when every check passed, 1 otherwise; each check prints one line.

D=$1
V=$2
[ -n "$D" ] && [ -n "$V" ] || { echo "usage: checkpkg.sh DIST VERSION"; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SYS=usr/lib/cc370/cc370/maclib370
DEB="$D/maclib370_${V}_all.deb"
RPM="$D/maclib370-${V}.noarch.rpm"
TGZ="$D/maclib370-${V}.tar.gz"
META="$D/maclib370-${V}-metadata.json"
fail=0

check() {   # check "what" "got" "want"
    if [ "$2" = "$3" ]; then
        echo "ok    $1"
    else
        echo "FAIL  $1"
        echo "      got:  $2"
        echo "      want: $3"
        fail=1
    fi
}

( cd "$D" && sha256sum -c --quiet SHA256SUMS ) && echo "ok    SHA256SUMS" \
    || { echo "FAIL  SHA256SUMS"; fail=1; }

check "deb Package"      "$(dpkg-deb -f "$DEB" Package)"      "maclib370"
check "deb Architecture" "$(dpkg-deb -f "$DEB" Architecture)" "all"
check "deb Version"      "$(dpkg-deb -f "$DEB" Version)"      "$V"
check "deb Depends"      "$(dpkg-deb -f "$DEB" Depends)"      ""

check "rpm Name"    "$(rpm -qp --qf '%{NAME}' "$RPM" 2>/dev/null)" "maclib370"
check "rpm Arch"    "$(rpm -qp --qf '%{ARCH}' "$RPM" 2>/dev/null)" "noarch"
# rpmlib(...) capabilities are rpm's own, not a dependency on a package
check "rpm Requires" \
    "$(rpm -qpR "$RPM" 2>/dev/null | grep -vc '^rpmlib(')" "0"

check "metadata version" \
    "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$META")" \
    "$V"

# the same files in all three, under the sysroot in the packages
t=$(tar tzf "$TGZ" | grep -v '/$' | sort)
d=$(dpkg-deb -c "$DEB" | awk '{print $NF}' | grep -v '/$' \
    | sed "s|^\./$SYS/||" | sort)
# rpm -qlp lists directories without a trailing slash: keep regular files
r=$(rpm -qp --qf '[%{FILEMODES:perms} %{FILENAMES}\n]' "$RPM" 2>/dev/null \
    | awk '/^-/ {print $2}' | grep "^/$SYS/" | sed "s|^/$SYS/||" | sort)
same() {    # same "what" "list" "reference list"
    if [ "$2" = "$3" ]; then
        echo "ok    $1"
    else
        echo "FAIL  $1"
        printf '%s\n' "$2" > "$D/.checkpkg.a"
        printf '%s\n' "$3" > "$D/.checkpkg.b"
        diff "$D/.checkpkg.a" "$D/.checkpkg.b" | head -20 | sed 's/^/      /'
        rm -f "$D/.checkpkg.a" "$D/.checkpkg.b"
        fail=1
    fi
}
same "deb files = tarball files" "$d" "$t"
same "rpm files = tarball files" "$r" "$t"
check "files outside the sysroot (deb)" \
    "$(dpkg-deb -c "$DEB" | awk '{print $NF}' | grep -v '/$' \
       | grep -vc "^\./$SYS/")" "0"
check "files outside the sysroot (rpm)" \
    "$(rpm -qp --qf '[%{FILEMODES:perms} %{FILENAMES}\n]' "$RPM" 2>/dev/null \
       | awk '/^-/ {print $2}' | grep -vc "^/$SYS/")" "0"

members=$(find "$ROOT/maclib" "$ROOT/amodgen" -name '*.macro' | wc -l | tr -d ' ')
check "tarball members = repository members" \
    "$(echo "$t" | grep -c '^macros/[^/]*\.macro$')" "$members"
for f in macros/GETMAIN.macro macros/CVT.macro MANIFEST.tsv README.md LICENSE; do
    check "tarball has $f" "$(echo "$t" | grep -cx "$f")" "1"
done
echo "tarball: $(echo "$t" | wc -l | tr -d ' ') files"

exit $fail
