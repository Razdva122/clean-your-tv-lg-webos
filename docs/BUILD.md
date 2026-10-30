# Build

[Developer references](development/README.md) · [Install without building](INSTALL.md)

Requirements: Bash, Python 3.9+, Node.js 20.19+ with npm, webOS CLI,
Zig 0.14.1, and a C compiler for tests. CI uses Node 22. These are source-build
requirements; installed cytv packages carry their host runtime.

```sh
scripts/test.sh
scripts/build.sh
```

The commands above run full verification and package builds. For an ordinary
edit, start with the affected `scripts/test.sh ui`, `tv`, `installer`, `setup`,
`android` or `preview` group and its dependencies; the frozen release still runs
all groups. For compiled UI reload and direct signed Root QA, use
[TV development](development/TV-DEVELOPMENT.md) instead of rebuilding every
desktop installer. See [Contributing](../CONTRIBUTING.md) for verification scope.

Use `ZIG=/absolute/path/to/zig` and `ARES_PACKAGE=/absolute/path/to/ares-package`
when tools are not on PATH. Generic builds use an empty app inventory. For a useful
launcher, run `sync-apps.py` before packaging. Do not publish personalized packages.

Development outputs: launcher and helper IPKs named using their `appinfo.json`
IDs/versions, plus `SHA256SUMS` in `dist/`. The permission postprocessor targets
the newly built helper package, even if older packages remain in `dist/`.

The build stages an allowlisted set of source files and empty state directories.
A package postprocessor sets those two directories to prisoner:jailer, mode 0770,
for the tested Developer Mode environment. No root access is required to install.

The relay, controller and startup service use separate locks, heartbeats and a
persistent emergency stop. The startup service claims a boot before launching so
a failure cannot produce an automatic retry loop. A manual helper launch resumes
a stopped setup. See RECOVERY.md before changing this behavior.

Private runtime state includes pairing keys, control files and logs under the
helper's `state/` directory. Never build a public package from a live TV backup.

For the independent development updater package, run `scripts/build-updater.sh`. It also produces `dist/updater-setup/` with the scoped permission CLI and documentation. Only the pinned public signing key is copied into the package; service state is created at runtime, with no fixed-UID postprocessor. Read [UPDATES.md](UPDATES.md) for validation results and remaining release gates; it is separate from `scripts/build.sh` and requires root for TV-side installation.
For current component versions, use `release-versions.json`. For Root bundles see
[manual installation](MANUAL_INSTALL.md); for standalone installers see [CLI builds](CLI.md#build-from-source).

The payload also includes the fixed System Updater bootstrap and support
files. Use `python scripts/build-cytv.py --payload-only` for a payload check or
`--desktop` for the host application. The optional TV Python archive is downloaded
only when needed or explicitly cached with `cytv --prepare-python-runtime`; it
is not embedded by this build. See [installation](INSTALL.md) and [release history](history/README.md).
