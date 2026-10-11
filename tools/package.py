#!/usr/bin/env python3
"""package -- maclib370's release artifacts, one per channel (#3).

The macros are the same whatever the host, so there is one artifact per
channel, not one per host:

    maclib370-<v>.tar.gz             macros/ MANIFEST.tsv README.md LICENSE,
                                     no top directory: unpack it INTO
                                     <sysroot>/maclib370
    maclib370_<v>_all.deb            /usr/lib/cc370/cc370/maclib370/...
    maclib370-<v>.noarch.rpm         the same tree
    maclib370-<v>-metadata.json      version, commit, source, member count
    SHA256SUMS                       over all of the above

macros/ is maclib/ and amodgen/ in one directory, which is how as370 finds
them (<exedir>/../maclib370/macros).  Flattening stops on a name the two
libraries share, compared without case: a Homebrew install lands on a
case-insensitive file system.

Usage:  python3 tools/package.py build --version V [--out dist] [--no-nfpm]

.deb/.rpm need nfpm on PATH (CI installs a pinned release); --no-nfpm writes
the tarball, the metadata and the nfpm configs only.
"""
import argparse, gzip, hashlib, json, os, shutil, subprocess, sys, tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = ("maclib", "amodgen")
TOPS = ("macros", "MANIFEST.tsv", "README.md", "LICENSE")
SYSROOT = "/usr/lib/cc370/cc370/maclib370"
LICENSE = "MIT (tooling); IBM material, see README"


def gitrev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"],
                                       text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def stage(dst):
    """Copy the members into dst/macros, the rest beside it.  Returns the
    member count per library, or None on a collision."""
    seen, count = {}, {}
    mac = os.path.join(dst, "macros")
    os.makedirs(mac)
    for lib in LIBS:
        names = sorted(f for f in os.listdir(os.path.join(ROOT, lib))
                       if f.endswith(".macro"))
        for f in names:
            key = f.lower()
            if key in seen:
                print(f"[package] {lib}/{f} collides with {seen[key]}")
                return None
            seen[key] = f"{lib}/{f}"
            shutil.copy(os.path.join(ROOT, lib, f), os.path.join(mac, f))
        count[lib] = len(names)
    for f in TOPS[1:]:
        shutil.copy(os.path.join(ROOT, f), os.path.join(dst, f))
    return count


def entries(stage_dir):
    """Every path under the stage, sorted, directories before their files."""
    out = []
    for top in TOPS:
        base = os.path.join(stage_dir, top)
        out.append(base)
        for d, dirs, files in os.walk(base):
            dirs.sort()
            out += [os.path.join(d, x) for x in dirs]
            out += [os.path.join(d, x) for x in sorted(files)]
    return out


def tarball(stage_dir, path):
    """Reproducible: sorted, fixed owner, mtime and mode, no top directory."""
    def norm(ti):
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        ti.mtime = 0
        ti.mode = 0o755 if ti.isdir() else 0o644
        return ti
    # gzip writes a timestamp into its header: fix it too
    with open(path, "wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
            tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as t:
        for e in entries(stage_dir):
            t.add(e, arcname=os.path.relpath(e, stage_dir), recursive=False,
                  filter=norm)


def nfpm_yaml(stage_dir, version):
    lines = [
        "# rendered by tools/package.py - do not edit",
        "name: maclib370",
        "arch: all",
        "platform: linux",
        f"version: {version}",
        "version_schema: none",
        "maintainer: mvslovers <https://github.com/mvslovers>",
        "description: |",
        "  SYS1.MACLIB and SYS1.AMODGEN of MVS 3.8j (TK5) as files for the",
        "  cc370 toolchain: as370 finds them with no -I.",
        "homepage: https://github.com/mvslovers/maclib370",
        f"license: {LICENSE}",
        "section: devel",
        "contents:",
        f"  - src: {stage_dir}/macros/",
        f"    dst: {SYSROOT}/macros",
        "    type: tree",
    ]
    for f in TOPS[1:]:
        lines += [f"  - src: {stage_dir}/{f}",
                  f"    dst: {SYSROOT}/{f}"]
    lines += ["rpm:", "  packager: mvslovers"]
    return "\n".join(lines) + "\n"


def cmd_build(a):
    out = os.path.abspath(a.out)
    st = os.path.join(out, "stage")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(st)
    count = stage(st)
    if count is None:
        return 1
    n = sum(count.values())
    print(f"[package] {n} members "
          + ", ".join(f"{k} {v}" for k, v in count.items()) + " -> macros/")

    v = a.version
    tgz = os.path.join(out, f"maclib370-{v}.tar.gz")
    tarball(st, tgz)

    meta = {
        "schema": 1,
        "name": "maclib370",
        "version": v,
        "commit": gitrev(),
        "members": dict(count, total=n),
        "manifest_sha256": sha256(os.path.join(ROOT, "MANIFEST.tsv")),
    }
    mj = os.path.join(out, f"maclib370-{v}-metadata.json")
    with open(mj, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    files = [tgz, mj]
    for packager, target in (("deb", f"maclib370_{v}_all.deb"),
                             ("rpm", f"maclib370-{v}.noarch.rpm")):
        cfg = os.path.join(out, f"nfpm-{packager}.yaml")
        with open(cfg, "w") as f:
            f.write(nfpm_yaml(st, v))
        if a.no_nfpm:
            continue
        path = os.path.join(out, target)
        subprocess.check_call(["nfpm", "package", "--config", cfg,
                               "--packager", packager, "--target", path])
        files.append(path)

    with open(os.path.join(out, "SHA256SUMS"), "w") as f:
        for p in files:
            f.write(f"{sha256(p)}  {os.path.basename(p)}\n")
    for p in files + [os.path.join(out, "SHA256SUMS")]:
        print(f"[package] {os.path.relpath(p, ROOT)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--version", required=True)
    b.add_argument("--out", default=os.path.join(ROOT, "dist"))
    b.add_argument("--no-nfpm", action="store_true")
    a = ap.parse_args()
    return cmd_build(a)


if __name__ == "__main__":
    sys.exit(main())
