# maclib370

The system macro libraries of MVS 3.8j -- `SYS1.MACLIB` and `SYS1.AMODGEN` --
as files for the cc370 toolchain, so that `as370` assembles against the same
macros an MVS system would give IFOX00.

| directory | dataset | members |
|---|---|--:|
| `maclib/` | `SYS1.MACLIB` | 747 |
| `amodgen/` | `SYS1.AMODGEN` | 288 |

The two libraries share no member name; installed, both go into one
directory, `<sysroot>/maclib370/macros`.

## Source

TK5, read from a frozen copy of its DASD: the system known here as
`MVSTK5-REF`, shut down cleanly on 2026-09-11 and copied with a SHA-256 sum per
file. The SMP inventory of a second TK5 system whose `SYS1.MACLIB` is
byte-identical identifies the level as **TK5 Update 5** (2026-02-18); the
frozen copy itself carries no version string.

The libraries are taken **as shipped**, maintenance and usermods included, not
at the IBM distribution-library level. Measured against TK5's own
distribution libraries (`AMACLIB` and the rest):

- 711 `SYS1.MACLIB` members are byte-identical to their distribution-library
  copy.
- 26 have no entry in either SMP zone and are byte-identical to the
  `AMACLIB` member of the same name (24 `BNGI*`, `DELETE`, `DEMF`).
- 10 differ from the distribution level or have no distribution member. They
  are TK5's own:

| member | SYSMOD (SMP RMID / last update) |
|---|---|
| `GETMAIN` | ZP60033 -- adds `LOC=` |
| `WTO` | ZP60039 |
| `WTOR` | ZP60040 |
| `GTTERM` | ZP60032 / UZ44753 |
| `IKTTCAST` | UZ28155 / ZP60007 |
| `IKTTVWA` | UZ55134 / ZP60009 |
| `STFSMODE` | ETV0108 / ZP60009 |
| `IHADVA` | RP00003 |
| `IEAPMNIP` | TNIP800 (no distribution-library member) |
| `IEAPPNIP` | TNIP800 (no distribution-library member) |

`SYS1.AMODGEN` is itself a distribution library and is taken whole.

## Form

One file per member, `NAME.macro` in upper case. Each EBCDIC record becomes
one line: decoded with code page 037, all 80 columns kept (columns 73-80 hold
the sequence numbers), LF, UTF-8. Code page 037 maps all 256 byte values, so
the conversion loses nothing: `MANIFEST.tsv` records the SHA-256 of every
member's EBCDIC bytes, and

```
python3 tools/extract.py --verify
```

re-encodes every file and checks it against that sum.

`as370` reads this form exactly as it reads the original records: assembling
all 5,528 modules of an MVS 3.8j source tree against it gave the same object
decks as with CRLF line ends, as with Latin-1, and as with trailing blanks
trimmed.

## Reproducing

```
python3 tools/extract.py --frozen <frozen copy> --dasdpdsu <hercules>/dasdpdsu
```

checks the two volume files against the SHA-256 sums pinned in the script
(`dasd/tk5res.390` holds `SYS1.MACLIB`, `dasd/tk5dlb.392` holds
`SYS1.AMODGEN`), unloads both libraries with Hercules' `dasdpdsu`, rewrites
`maclib/`, `amodgen/` and `MANIFEST.tsv`, and verifies the result. It stops
without writing anything if a member is not a whole number of 80-byte records
or if the two libraries share a name. `--unloaded DIR` reuses an earlier
`dasdpdsu` run on a host without Hercules; the volume sums are then not
checked, and the manifest says so.

## The IBM material

The members are IBM's MVS 3.8j macros as distributed with TK5, plus the
modifications listed above. This repository records where they came from; it
makes no statement about them beyond that.
