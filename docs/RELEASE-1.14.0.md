# v1.14.0 — installer choice and shared Root capabilities

Published as v1.14.0 after v1.13.0, delivered through
[PR #442](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/442).
Scope and versions were frozen before acceptance. [Selected full build42566531298:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42566531298)
passed every mandatory job at2f6da451 and is pinned. Its optional, unapproved
Homebrew job failed an external Python download; no Homebrew promotion is selected.
The guarded QA-signing correction (#456) replaces the initial full build.
[Exact Android/C3 QA and explicit limits](history/2026-11-09-release-1.14.0-qa.md).
Selected C3 signed-update/control/audio/remote-standby and exact Android emulator
acceptance passed; public delivery completed in [Automatic release42571455618](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42571455618). Alternate legacy hardware,
physical phones and other unselected paths retain their documented limits.

## Changes

- Before a new computer installation, offer the latest GitHub installer or an
  explicit choice to keep the current embedded packages (#449). Failed metadata
  checks remain nonblocking. Pending operations and maintenance bypass the
  advisory; `--yes` alone cannot select an older installer when a newer one is
  detected. No device data is sent to GitHub.
- Continue an authenticated No-root operation when firmware has normalized the
  caller-owned pairing key to exactly 0775 (#444, #437). The checked single-link
  inode is restricted to 0640 with its bytes/owner/group preserved. Status stays
  read-only, immutable operation evidence is unchanged and emergency stops are
  retained. Reporter-device continuation remains unverified.
- Read Root application/input catalogs over the existing SSH connection without
  TV Node subprocesses (#450, #389). Preserve bounded streams, deadlines, icons,
  mandatory nonempty applications and separate optional-input warnings. The
  reported Node/libuv failure path is bypassed; reporter-device setup is still
  unconfirmed.
- Package the same guarded KeyFilters backend in ordinary Root and exact-Node-
  0.12.2 Root Beta, for both resolutions (#451). Schema3 admission checks actual
  capabilities without a numeric SDK/model allowlist. Native ARM32 LG Home,
  vendor Qt filters, confirmed System Profile absence, emergency input and safe
  recovery remain required. Live Qt API checks precede lease subscription;
  bounded descriptor reads work on Node0.12.2. Historical schema2 identity/state
  and recovery formats are preserved, but fresh probes and explicit re-enable
  now also require the shared read-only environment checks. Restore does not
  re-admit the device. Ordinary profile routing remains preferred
  when its reads succeed.
- Balance existing CI work across four shards per OS and retain timings without
  weakening coverage or evidence trust (#441). Use TV POSIX paths in the Windows
  catalog test fixture (#452), preserving the real-reader icon assertions. Reconcile published/localized
  guides (#445) and curate the user-confirmed TV list (#447).

The original #410 report remains open/planned. A synthetic SDK3.9.0/native-Home
fixture is not acceptance of that TV. Old in-compositor LG Home panels and other
unsupported Home implementations remain refused. Experimental compositor/Beta
paths retain fresh-install restrictions and disabled ordinary OTA.

## Versions and packaging

| Component | Published v1.13.0 | Published v1.14.0 | Reason |
| --- | --- | --- | --- |
| Home FHD/HD | 1.13.2 | 1.13.3 | Shared Chinese font subset includes new installer translations |
| Home Helper | 0.8.0 | 0.8.0 | Unchanged source; exact published bytes required |
| cytv | 0.14.0 | 0.15.0 | Advisory, continuation repair, catalog transport and selector |
| Android / versionCode | 0.13.0 / 28 | 0.14.0 / 29 | Shared operations and rebuilt embedded payload |
| Root / infrastructure | 0.13.2 | 0.14.0 | Shared broker, admission and normal/Beta packaging |
| Both edition Updaters | 0.5.4 | 0.5.5 | Same shared font subset; runtime code unchanged |
| Fresh System / protocol | 1.2.7 / 1 | 1.2.7 / 1 | Supervisor code/inventory unchanged |

Desktop/Android installers and Root normal/Beta/experimental variants were rebuilt
at candidate freeze.
The broker is embedded in ordinary Root too, so its package and infrastructure
hashes change. Updater packages need their own version bump for the font bytes. System retains
its exact own package/code; regenerate release-set data for the new artifacts. Existing supervisors stay pinned;
no new supervisor migration, signing identity or Homebrew promotion is admitted.
Preserve Android application ID, original signer and private stored data.

## Validation and remaining gates

[Preparation, baseline authentication and selected cases](history/2026-11-09-next-candidate-preparation.md)
record the integrated host checks and documentation review.
[Root/Beta development evidence](history/2026-11-09-root-beta-keyfilters.md)
records exact legacy runtimes, ARM32 builds, refusal cases and limitations.
All nine implementation/maintenance PRs are included; #451's final a80392fb CI passed
Linux/macOS, browser, ARM Python and Windows/macOS desktop runtime checks.
Those results precede versioned frozen-candidate build validation.

The selected replacement full candidate42566531298:1 passed all mandatory jobs;
20 jobs succeeded and one optional unapproved Homebrew job failed an external
Python download. No Homebrew promotion is selected. Initial and replacement
artifact/source/payload verification is recorded in the [dated QA evidence](history/2026-11-09-release-1.14.0-qa.md).
The exact replacement original-signer Android code28→29 emulator upgrade, four
retained files, real Store/native operations and idle/no-replay passed.

Authorized owner-supervised C3 testing installed exact signed Root0.14.0 and
Root Updater0.5.5 through the original retained System1.2.5 worker. Transaction,
profile/theme/icon preservation, six renderer and eleven service checks passed.
The owner reported Home/navigation/audio,10-second remote standby/wake, triple
Home/staysOff and explicit resume/finalOff successful. Independent final readback
confirmed disabled intent/guardian off, recovery integrity, completed original
transaction and no pending operation. Eight unsuccessful observer reads have
undetermined causes; telemetry does not establish continuous coverage.

Public signing/publication and package/feed verification completed successfully.
The [publication record](history/2026-11-09-release-1.14.0-publication.md) records
public assets, signatures, shipping notices and post-publication issue status. This pass does not accept legacy/Beta hardware or #410, physical
phones/minimum WebView, passive IR/other remotes, AC cold boot, actual whole-
edition rollback or retained supervisor migration. The scope/dependency rationale
and exact hashes/preconditions are in the QA record. Existing v1.13.0 observations
retain their original artifact scope; no universal compatibility claim is made.
