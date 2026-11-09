# Installer removal compatibility and simpler scratch cleanup

Related issues: #240, #418, #283 and #438. This is source and host verification,
not a report of a new installation on a user's TV. No TV was contacted or
changed. Original activation/installation causes and physical reporter-device
acceptance remain separate unresolved work.

## Scope and reproduced failures

No-root removal had two unconditional launches of `com.webos.app.home`. A retail
TV without that separate application could refuse with application-launch -101,
including when project apps had already been removed through the OS. Both paths
now use one helper. Only the exact typed app-not-found rejection admits fresh
foreground verification against fixed LG stock surfaces. If necessary it launches
only fixed Live TV and waits for observed stock foreground. Other rejections,
malformed replies and connection loss still stop. Existing controller stop,
startup/input cleanup, package absence and full-restart checks remain mandatory.
The public LG Application Manager reference defines -101 as app not found:
<https://webostv.developer.lge.com/develop/references/application-manager>.

Current compositor C1 installer bundles omitted `runtime/c1-home-gate`, which
`runtime_restore` selects for a retained schema-1 mount backend. Generated-bundle
regression reproduced this packaging failure. The normal compositor installer
now includes a current authenticated recovery-only binary. Real bundle validation
and restore selection verify it; tampering refuses. New installation still copies
and selects only compositor routing, and legacy Beta remains mount-free. This is
a concrete removal-path defect; discarded historical child detail does not prove
it is the only cause on the original C1.

Root final cleanup no longer launches its Luna/private-inventory children through
Node `spawnSync`. A bounded asynchronous reader keeps Luna stdin open until the
client exits, drains output, limits response size and reaps failed/timed-out
children. The ordinary Root cleaner and final Node proof both support a complete
`getActivityInfo` inventory when the older `/list` request is unavailable.
Malformed inventories remain failures, never empty success.

A completed TV cleanup is rechecked under its original operation/removal lease
and locks even when the local installer still has a private-cleanup checkpoint.
A legacy completion can publish the final exclusion fence once, without reopening
package removal. Current package, startup, routing, activity, input and private
absence checks remain authority; a historical `complete` flag alone is insufficient.

## Simplification requested during implementation

Temporary support is a directory scope, not a collection of file-specific recovery
states. Root removal now uses the existing pinned tree remover for its original
host-checkpointed `/tmp/cytv-root-tail-<UUID>` directories. Old gate bytes, atomic
upload remnants and cache subdirectories are inert and removed together.
The code does not compare every historical support file with the latest installer
hash or add exceptions for temporary filenames.

Only these exact saved scratch directories receive the broader tree treatment.
Matching operation/lease, original locks, ownership, single-link regular files,
no-follow directory traversal and inode checks remain. Internal symlinks are
unlinked without following targets. Unsafe or redirected roots refuse. The
persistent ownership journals and old-worker fences are separate and retained.
No new state file, permission grant, dependency or network endpoint is introduced.
No-root adds an existing Application Manager foreground query and may launch
fixed Live TV during explicit removal; this user-visible transition is documented.

## Verification and review

Red tests reproduced missing fixed Home, asynchronous foreground transition,
missing schema-1 C1 recovery support, synchronous-child/Activity compatibility,
legacy completed cleanup replay, old support hashes and temporary-file residue.
The corrected focused checks include:

- Root cleanup/tail/child/handoff: 55 tests, two explicit platform/container skips,
  using exact Node 8.12.0 and the compiled Node 0.12.2 source.
- Real subprocess tests verify open stdin, drained output, exit failure, absent
  executable, deadline and stdout/stderr size bounds.
- No-root ordinary removal and fence dependency group: 69 tests.
- Root removal: 76 tests; C1 gate lifecycle/setup/bundle: 43 tests.
- C1 payload: generated FHD/HD bundles, actual manifest/restore selector,
  fresh-install exclusion and tampering checks. Actual Zig ARM32 build and
  `validate_native_gate` passed; recovery executor size is 84,904 bytes.
- Shared Luna RPC: eight tests, including complete alternative activity inventory
  bounds and child reaping.
- Independent review reproduced one old-gate-hash retry blocker. Its correction
  and subsequent directory-scope simplification were independently reviewed;
  the reviewer found no remaining blocker and reran four focused safety cases.
- Changed Python parses with Python 3.9 grammar; formatting and whitespace checks
  passed before the final consolidated commit.

The complete affected local command exited successfully:

```sh
PYTHON=<maintained-project-venv>/bin/python PYTHONDONTWRITEBYTECODE=1 \
NODE8=<exact-8.12.0> NODE012=<exact-0.12.2> \
NODE010=<exact-0.10.15> NODE01025=<exact-0.10.25> \
scripts/test.sh installer setup android tv-runtime
```

It passed 1,192 installer cases (three declared skips), 286 setup cases, 44
Android Python cases, 1,185 Root runtime cases (three declared skips), 136 System
cases and selected JS/native/compatibility/package checks. Final scoped cleanup
rerun passed all 55 cases (two platform/container skips) on exact Node 8.12.0 and
compiled Node 0.12.2; the final C1 payload test rerun passed both cases. Windows
retains byte/manifest validation while the native runtime-selector execution is
POSIX-only. These implementation checks do not substitute for a frozen candidate.
The [implementation PR](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/457)
records subsequent integration/publication separately. Product/test head
`a5cdaaae` passed all selected PR checks: [Tests 42567793891](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42567793891),
including eight Linux/macOS runtime shards, browser and optional Python;
[Windows/Intel Mac runtime 42567793959](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42567793959)
and [preview build 42567794013](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42567794013)
also passed. Release policy passed; full-release/deployment were unselected.
The final evidence-only commit preserves every product/test input.

## Packaging and acceptance limits

Rebuild the shared desktop/console/Android installer, normal C1 support and Root
Updater support through the release coordinator. No version, inventory, build pin,
release PR or publication was changed by this implementation task. The frozen
candidate is not silently replaced. English recovery/maintenance, developer
contracts and all thirteen localized practical removal guides were updated;
localized guides contain no new release history or QA claims.

Host: macOS ARM64, maintained project Python environment, current Node 23.11.0 and
exact legacy Node runtimes. New physical TV model, firmware/webOS and remote:
unselected/untested. Removal, Home/remote behavior, sound, standby, cold boot,
OTA and rollback on reporter devices remain untested here. Public delivery and
fresh physical acceptance must precede claims that those devices are recovered.
