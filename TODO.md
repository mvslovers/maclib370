# TODO

1. **Smoke assembly without `-I`.** `tools/smoke.sh` passes `-I <macros>`
   because no cc370 release searches `<exedir>/../maclib370/macros` yet
   (cc370 4d1fca9, in cc370's Unreleased). Once one does: unpack the tarball
   into the cc370 tree as `cc370/maclib370/` and assemble with no `-I`. The
   control (no maclib370 -> no assembly) stays.
2. Then cc370 depends on the package, and libc370 later (mbt#234 step 4).
