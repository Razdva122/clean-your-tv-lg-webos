# Source installer build dependencies — 2026-11-03

Related: [#272](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/272).
Host-only source verification; no TV was contacted or installation result copied.

`install.sh` installed only `requirements.txt`, then reached the Home build without
installing `scripts/build-requirements.txt`. Font preparation requires its pinned
`fonttools==4.60.1`; a clean environment could therefore fail after pairing and app
inventory, before package installation. The normal desktop builder already includes
this requirement through `cytv/build-requirements.txt`.

The existing host pip step now installs both requirement files before installing
webOS CLI or accessing a TV. Its existing `set -e` and preparation-stage error trap
stop a dependency failure before pairing. No pin, TV permission, runtime package,
profile, recovery behavior or release version changes.

Verification on macOS 15.6.1 ARM64:

- Existing 13 source-installer tests passed before the change.
- Two new tests failed before the correction: missing build dependency installation
  and failure continuing into TV work. Both passed after it; the tests execute the
  real Bash installer with simulated external tool/network boundaries.
- `PATH="$PWD/.venv/bin:$PATH" bash scripts/test.sh setup`: all 224 tests passed.
  An earlier sandboxed focused invocation refused `/dev/fd` in the existing PTY
  color test; the normal approved test run passed without changing that code.
- A newly created Python 3.11.12 venv installed exactly `requirements.txt` and
  `scripts/build-requirements.txt`. `fontTools` 4.60.1 and websockets imported, and
  actual pinned-source SC/TC font preparation with a fresh font cache passed static
  font and runtime-character coverage checks. No preinstalled Python packages or
  prepared subset cache were used by that environment.
- `bash -n install.sh` and `git diff --check` passed. Independent read-only review
  found no issues and independently passed both new regression tests.

The English source-install guide already promises automatic local dependencies;
this restores that contract without adding a user command. Existing localized
setup/control flows remain applicable. No device installation, remote controls,
sound, standby/cold boot, OTA/rollback, Termux or other-host acceptance is claimed.
Integration, CI and public delivery remain separate from these local checks.
