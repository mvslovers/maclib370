# Changelog

All notable changes to maclib370. Versions follow semantic versioning: a
different source level or any changed member is a minor release, a change
to the tooling alone is a patch.

## [Unreleased]

## [1.0.0] - unreleased

### Added
- `SYS1.MACLIB` (747 members) and `SYS1.AMODGEN` (288 members) of MVS 3.8j at
  the level of TK5 Update 5, one `NAME.macro` file per member, with
  `MANIFEST.tsv` and `tools/extract.py --verify` to check every member against
  the SHA-256 of its EBCDIC bytes.
- Packages: `maclib370-<v>.tar.gz` (no top directory; unpack it into
  `<sysroot>/maclib370`), `maclib370_<v>_all.deb` and
  `maclib370-<v>.noarch.rpm` (under `/usr/lib/cc370/cc370/maclib370`), a
  metadata file and `SHA256SUMS`, plus a Homebrew formula in
  `mvslovers/homebrew-tap`. Installed there, both libraries sit in one
  directory, `macros/`, where `as370` looks for them.
