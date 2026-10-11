#!/usr/bin/env python3
"""Extract maclib370 from the frozen TK5 DASD copy.

    python3 tools/extract.py --frozen ~/MVSTK5-REF-frozen-20260911
    python3 tools/extract.py --unloaded DIR      # DIR/MACLIB, DIR/AMODGEN

With --frozen, the two volume files are checked against the SHA-256 sums below
before anything is read, and Hercules' dasdpdsu unloads SYS1.MACLIB and
SYS1.AMODGEN into a temporary directory.  With --unloaded, an earlier dasdpdsu
run is reused (for a host without Hercules); the volume sums cannot be checked
then, and MANIFEST.tsv says so.

Every member is written as NAME.macro: the EBCDIC records decoded with cp037,
80 columns each (columns 73-80 kept), one record per line, LF, UTF-8.  cp037
covers all 256 byte values, so nothing is lost: MANIFEST.tsv carries the
SHA-256 of each member's EBCDIC bytes, and --verify re-encodes every .macro
file and checks it against that sum.

The run fails, and writes nothing, if a member is not a whole number of 80-byte
records or if the two libraries share a member name (they are installed into
one directory).
"""
import argparse, hashlib, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The input, pinned: MVSTK5-REF, frozen 2026-09-11 (SHA256SUMS of that copy).
LIBS = (
    # (directory, dataset, volume file, sha256 of the volume file)
    ("maclib", "SYS1.MACLIB", "dasd/tk5res.390",
     "449ae2385610f61e3b1428adc8b0351675989556edbdef0e474c8a5d66b6ef08"),
    ("amodgen", "SYS1.AMODGEN", "dasd/tk5dlb.392",
     "9f13dbaaadca89e2da31e6b83ee7f221c7cba08168d3242de41682e5c02caa20"),
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def unload(frozen, dasdpdsu, work):
    """dasdpdsu every library into work/<DATASET-LAST-QUALIFIER>/."""
    for d, dsn, vol, want in LIBS:
        path = os.path.join(frozen, vol)
        got = sha256(path)
        if got != want:
            sys.exit(f"extract: {vol}: sha256 {got}, expected {want} -- not the pinned input")
        out = os.path.join(work, dsn.split(".")[-1])
        os.makedirs(out)
        r = subprocess.run([dasdpdsu, path, dsn], cwd=out, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"extract: dasdpdsu {vol} {dsn}: rc {r.returncode}\n{r.stdout}{r.stderr}")


def members(unloaded, dsn):
    """{NAME: bytes} for one unloaded library.  dasdpdsu writes name.mac."""
    src = os.path.join(unloaded, dsn.split(".")[-1])
    out = {}
    for f in sorted(os.listdir(src)):
        name = f.rsplit(".", 1)[0].upper()
        if not re.fullmatch(r"[A-Z$#@][A-Z0-9$#@]{0,7}", name):
            sys.exit(f"extract: {dsn}: unexpected file {f!r}")
        if name in out:
            sys.exit(f"extract: {dsn}: member {name} twice")
        out[name] = open(os.path.join(src, f), "rb").read()
    return out


def render(data):
    if len(data) % 80:
        return None
    t = data.decode("cp037")
    return "".join(t[i:i + 80] + "\n" for i in range(0, len(t), 80)).encode("utf-8")


def verify():
    """Re-encode every .macro file and check it against MANIFEST.tsv."""
    bad = n = 0
    for line in open(os.path.join(ROOT, "MANIFEST.tsv")):
        if line.startswith("#") or line.startswith("library\t"):
            continue
        lib, name, recs, ebcdic, _ = line.rstrip("\n").split("\t")
        text = open(os.path.join(ROOT, lib, name + ".macro"), "rb").read().decode("utf-8")
        recs_ = text.split("\n")[:-1]
        ok = all(len(r) == 80 for r in recs_) and len(recs_) == int(recs) and \
            hashlib.sha256("".join(recs_).encode("cp037")).hexdigest() == ebcdic
        bad += not ok; n += 1
        if not ok:
            print(f"verify: {lib}/{name}.macro does not re-encode to its EBCDIC sum")
    print(f"verify: {n - bad} of {n} members re-encode to their EBCDIC SHA-256")
    return 1 if bad or not n else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--frozen", help="the frozen DASD copy (holds dasd/)")
    g.add_argument("--unloaded", help="an earlier dasdpdsu run: DIR/MACLIB, DIR/AMODGEN")
    g.add_argument("--verify", action="store_true", help="check the tree against MANIFEST.tsv")
    ap.add_argument("--dasdpdsu", default="dasdpdsu", help="path of Hercules' dasdpdsu")
    a = ap.parse_args()
    if a.verify:
        return verify()

    with tempfile.TemporaryDirectory() as work:
        if a.frozen:
            unload(os.path.expanduser(a.frozen), a.dasdpdsu, work)
            unloaded, mode = work, "frozen"
        else:
            unloaded, mode = a.unloaded, "unloaded"

        libs = {}
        for d, dsn, vol, want in LIBS:
            libs[d] = members(unloaded, dsn)
        shared = set(libs["maclib"]) & set(libs["amodgen"])
        if shared:
            sys.exit(f"extract: {len(shared)} member names in both libraries: {sorted(shared)[:10]}")
        rendered = {}
        for d, ms in libs.items():
            for name, data in ms.items():
                r = render(data)
                if r is None:
                    sys.exit(f"extract: {d}/{name}: {len(data)} bytes, not whole 80-byte records")
                rendered[(d, name)] = (data, r)

        # Everything checked; now replace the tree.
        for d, dsn, vol, want in LIBS:
            out = os.path.join(ROOT, d)
            if os.path.isdir(out):
                shutil.rmtree(out)
            os.makedirs(out)
        rows = []
        for (d, name), (data, r) in sorted(rendered.items()):
            open(os.path.join(ROOT, d, name + ".macro"), "wb").write(r)
            rows.append(f"{d}\t{name}\t{len(data) // 80}\t{hashlib.sha256(data).hexdigest()}"
                        f"\t{hashlib.sha256(r).hexdigest()}\n")

    with open(os.path.join(ROOT, "MANIFEST.tsv"), "w") as f:
        f.write("# maclib370 -- written by tools/extract.py, do not edit\n")
        for d, dsn, vol, want in LIBS:
            f.write(f"# {d}: {dsn} from {vol}, volume sha256 {want}"
                    f"{'' if mode == 'frozen' else ' (NOT checked: --unloaded)'}\n")
        f.write("library\tmember\trecords\tsha256_ebcdic\tsha256_macro\n")
        f.writelines(rows)
    for d in libs:
        print(f"extract: {d}: {len(libs[d])} members")
    return verify()


if __name__ == "__main__":
    sys.exit(main())
