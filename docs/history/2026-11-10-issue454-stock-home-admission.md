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
- `scripts/test.sh installer android setup`: passed, including 1,253 installer
  cases (seven expected skips), 290 setup cases, 44 Android cases and the selected
  Homebrew checks. The final additional host-shell fixture was also run in the
  focused host suite; no unchanged full dependency pass was repeated.
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

## Integration and final CI

[PR #492](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/492) merged
as `023ea5ec`; GitHub completed the requested auto-merge after integration policy
passed while the complete Tests run was still running. The task stayed active
until that run and the corrective run were reconciled. Its product sources match
`39a7bc3b`; unrelated v1.16.0 publication documentation was preserved.

[Initial Tests42826518027](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42826518027)
completed with one test failure in Linux shard3. The CI runner itself has UID1001,
so the original fixture's `TRUST_UID=getuid()` treated the simulated vendor owner
as trusted root and skipped the immutable-filesystem branch. All other runtime,
ARM Python and browser checks passed; both summary jobs reflected the failed unit.
This was a test-harness collision, not a production bypass: production `TRUST_UID`
remained0. The fixture now models root0 explicitly and maps only its exact Home
leaf to UID1001, including on `/home/runner` paths.

[PR #494](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/494) contains
only that fixture correction and merged as `c06b39ee` after
[Tests42828196677](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42828196677)
completed successfully. All eight Linux/macOS runtime shards, both OS summaries,
ARM Python, browser and both phone-HEIC jobs passed. The optional full-release
job was correctly skipped outside a frozen candidate. The corrected local
41-case guardian suite and independent read-only review also passed. No product
source changed for the fixture correction; successful unchanged source/ARM
compile and dependency evidence above remains applicable. No new full RC or TV
operation was launched to repair this test failure.

Both merged PRs and #454 are collected into the unfrozen
[next-candidate #491](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/491).
Version selection, final installer/support packaging, trusted candidate build,
matching scoped device acceptance and public delivery remain with that release.
The source integration does not confirm the reporter's original catalog failure
or completed installation. #454 stays open awaiting the corrected public release
and its reporter-device confirmation.
