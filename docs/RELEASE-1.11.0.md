# v1.11.0 — legacy compatibility and installation recovery

Scope frozen by the maintainer on 2026-11-07. [Full candidate42370069375:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42370069375) passed all21 jobs. The maintainer requested publication after the [bounded C3 QA pass](history/2026-11-07-release-1.11.0-tv-qa.md); untested paths remain explicit.

## Changes

- No-root app discovery has a bounded same-package fallback and refreshed remote
  icons (#370 / #207). Original IR routing and device/TLS acceptance remain open.
- Experimental compositor Home uses verified Qt SDK 6–9 capabilities and releases
  only its owned input filter (#371 / #364). Fresh setup only; target-TV physical
  compatibility, ordinary OTA and automatic rearm remain unverified/unavailable.
- Shared build resources, deterministic AR packaging, pinned formatting and
  Python/source-injection contracts are maintained (#372); dead cleanup paths
  and unused bindings are removed without dropping active recovery (#375).
- Failed setup offers direct recovery on CLI, desktop and Android; removal retries
  are bounded, failed Root activation compensates to verified LG Home, and
  uncertain package submission is fenced (#377).
- Root removal can use its bounded catalog fallback and retains first/latest
  failure detail (#379 / #240). Unavailable/malformed catalogs still block;
  the reporter's original installation cause and recovery remain unverified.
- No-root observer diagnostics preserve typed exceptions, guard/storage reasons
  and safe portable Node launch (#380, #382 / #376, #378). Test adapters retain
  actual sender/disconnect/retirement fault injection (#384). Original device
  causes remain unconfirmed.
- Home web compilation targets Chrome 38; Home and Updater services are compiled
  for legacy TV Node. Helper status requires broker confirmation, SSAP permissions
  agree, diagnostic focus is preserved and legacy Updater URLs work (#381 / #47).
  Source/runtime checks do not establish original-device acceptance or support
  for every older webOS web engine.
- No-root observer storage uses private `/tmp` state, SDK-compatible public staging
  and one storage check before pending (#385 / #201). Earlier source-bound capsules
  retain confirmed cleanup. Lost volatile evidence never authorizes replay. Later
  #378 discussion established the published storage-contract blocker; actual
  installation/recovery acceptance on the reporting TVs remains pending.

- Long SSH commands use a framed stdin header so TV exec-request limits do not
  disconnect the installer; IPK/configuration bytes remain separate binary stdin
  (#386). The original pending operation completed after the transport repair.

- Fresh System Updater and the explicit supported replacement target/readback
  pins are synchronized at1.2.4 (#387). The installed-source admission boundary
  remains1.1.0/1.1.1; retained1.1.2/1.2.x are not admitted.

- CI evidence now binds audited test-family inputs, allowing unchanged units to
  retain authenticated successes from PRs or complete candidate jobs. Windows
  long-command regressions use the installed POSIX shell explicitly. Package
  assembly, installed-package verification and final release gates remain fresh.

## Component versions

| Component | Published v1.10.0 | Candidate v1.11.0 |
| --- | --- | --- |
| Home FHD/HD | 1.11.0 | 1.12.0 |
| Home Helper | 0.7.4 | 0.7.5 |
| cytv installer | 0.11.0 | 0.12.0 |
| Android / versionCode | 0.10.0 / 24 | 0.11.0 / 25 |
| Root / infrastructure | 0.11.0 | 0.12.0 |
| Both edition Updaters | 0.5.0 | 0.5.1 |
| Fresh System Updater / protocol | 1.2.3 / 1 | 1.2.4 / 1 |

Changed package bytes require rebuilds, including the newly versioned Helper;
reusing published Helper 0.7.4 would omit the source fixes. Published Home 1.11.0 with exact preliminary Helper 0.7.5 passed the mandatory
same-package Start/confirmation, enabled status, non-root-controller and physical
triple-Home/arrow checks on the authorized C3. The committed approval binds real
published package hashes and the candidate canonical Helper archive. Actual
normal automatic OTA/rollback and unrooted Developer Mode provisioning remain
untested; final candidate equivalence passed, and the bounded final C3 observations are linked below.
Fresh System 1.2.4 versions changed packaged sources; ordinary component OTA does
not replace a retained System supervisor or authorize general migration.
Homebrew Installer remains unreleased with no promotion record. Android retains
its application ID and signing identity.

## Validation and limits

[Candidate PR #374](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/374)
contains the current build, gates and linked implementation evidence.
[Freeze/preflight record](history/2026-11-07-release-1.11.0-freeze.md) records
actual preliminary packages and checks separately from the final [C3 QA observations](history/2026-11-07-release-1.11.0-tv-qa.md).

The preliminary Helper compatibility observation above is bounded to its exact
packages and C3 state; the final case pass below supplies separate physical
observations. HDMI/CEC, pointer/wheel, true cold boot, complete OTA and rollback
remain untested. Earlier TV observations remain bound to their original bytes
and state.
Do not clear emergency stops, uncertain receipts or recovery journals to force
installation. Partial fixes do not close unresolved reports.

The final C3 session passed No-root/Root UI, single-Home routing, audio/volume,
standby/wake, Root key-up and emergency LG return, and normal full removal after
an OS restart. AC cold boot was waived and not executed; normal OTA/retained
rollback, unrooted Developer Mode, Android and other-device acceptance are not
claimed. [Root icon fallback #394](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/394)
is a maintainer-accepted non-blocking follow-up. Clearer No-root/Root transition
guidance is assigned separately for the next release; current guards remain.
