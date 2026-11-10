# Stock Home admission — 2026-11-10

Focused implementation for [#454](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454),
based on next-cycle `29e07ce7` after v1.16.0. No TV was contacted, no new
installation report was generated and no release version/build/acceptance was
selected. This is source/host verification, not device compatibility evidence.

## Failure and change

The reporter's public attributes and two ARM32 ELF headers reproduce two
independent host refusals: the fixed stock executable has UID 1001 and size
4,530,960 bytes, while the former preflight required UID 0 and at most 4 MiB.
The existing device reader and guardian would also reject that owner. Python
preparation and catalog reads were not reached by that attempt; neither Python
installation failure nor resolution of the original catalog report is proven.

Host, schema2/3 runtime and native guardian now use a bounded 16 MiB stock-file
limit. UID 1001 requires SquashFS; both device consumers check read-only filesystem
flags on the opened descriptor. Unknown evidence refuses. The Python reader
passes only that descriptor to the existing `stat` utility with a five-second
deadline. Regular executable file, no symlink, one link, no special/group/world
write bits, trusted parents, stable read/hash and configured native identity
checks remain. The generic private-file reader and legacy schema1 mount backend
are unchanged; no owner/permission/system-file mutation or new persistent state,
permission, dependency or network endpoint is introduced.

The rebuilt common Windows/macOS/Linux and Android installers need matching
ordinary/Beta Root support bundles. Updating only an installed TV app does not
replace the host preflight. Do not publish a compatibility claim from this patch.

## Focused verification ledger

These checks resolve missing evidence for the changed host/stock-reader/guardian
inputs; no full RC, signing run, TV install or rollback was dispatched. Existing
unchanged release results are not rerun for a new branch.

- `npm ci`: passed in the isolated worktree.
- Red/green host regression: public attributes and headers failed the old parser
  for both independent mismatches; the new immutable-stock case passes. The
  executed shell probe/marker and symlink-refusal test passes too.
- Red/green guardian regression: the actual compiled identity check rejected the
  immutable UID 1001 fixture before the change. It now accepts that fixed identity,
  while mutable/unknown filesystem, read-write flags, foreign UID and changed inode
  refuse. Kernel metadata/filesystem observations are interposed; no filesystem
  was mounted and no real file was chowned by the tests.
- Full compositor probe on a synthetic 4,530,960-byte ARM32 fixture produces the
  full-file SHA-256 and retains mandatory environment validation. Root-owned stock
  does not require the filesystem exception. Device metadata/filesystem/LS2/input
  are test doubles, not acceptance of the reporter's filesystem or device.
- Host capability tests: 18 passed. Compositor runtime suite: 33 passed. Related
  C1/runtime/bundle/recovery tests: 82 passed.
- Native guardian suite: 41 passed after fixture/minimum-size alignment.
- Installer/Android/setup dependency profiles: running; final result pending.
- Zig 0.14.1 ARM32 Linux static compile passed after the minimum-size alignment.
  The binary is a development compile only.
- Final Python 3.9 grammar, formatting and whitespace checks passed.
- Independent read-only review found no remaining actionable defect. Full-probe
  coverage addresses its noted direct-reader-only limitation; the shell fixture
  is POSIX-only so Windows still runs the shared parser cases.

## Documentation and remaining acceptance

Updated the canonical native backend reference. Reviewed practical installation
and localized guide scope: no user control or installation step changes, so no
release banner or developer-status text belongs in `docs/i18n/`. Root node/runtime
variant, recovery and disabled-OTA contracts remain unchanged.

The reporter's TV is OLED55C16LA, firmware 03.53.45, SDK 6.5.3, Node 8.12.0;
Windows installer cytv 0.16.0/v1.15.0. Remote model is unknown. This is existing
public issue context, not a new agent-observed installation result. Physical
installation/catalog/Home/buttons/audio/standby/cold-boot/update/rollback outcomes
on a corrected final artifact remain untested. No additional reporter commands
are needed during implementation. Keep #454 open for published-installer
confirmation; integration alone must not mark the original report fixed.
