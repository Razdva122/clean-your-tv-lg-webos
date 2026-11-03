# No-root recovery guidance — 2026-11-03

## Scope

Base: `c07f5c8f3ae61ecc767964119cf53c178c8a2de4` (`release/next`).
Related: #259, #201. This follows the integrated #256 pre-submission removal
correction; no version, candidate scope, build or publication is selected here.

An original No-root removal can fail restoring LG Home before any package removal
request. The retained journal then blocks new setup. #256 allows that original
pre-submission journal to enter guarded removal without the global status
monitor, but failed removal offered only a report, without a direct recovery
review action or enough journal context in its diagnostic export.

The shared predicate now drives the existing mutation guard, UI explanation and
allowlisted diagnostic classification. After that specific failed removal,
desktop and Android offer inspection using the same saved TV connection. The
inspection confirmation defaults to No, and removal requires separate consent.
The failed report remains the primary action. Console advice names the recovery
journey. No automatic retry, reinstall or journal deletion is introduced.

A definite No-root package-status refusal receives its own fixed explanation and
advice. A report distinguishes unsubmitted removal, inherited operation,
interrupted install, started removal and unknown journal. It exports only fixed
categories/actions and Home/Helper removal states, without the raw journal,
paths, operation IDs, addresses, credentials or app inventory. Reports cannot
serve as recovery authority. Missing original failures are not reconstructed.

## Verification

- Red/green tests reproduced missing report context, generic blocked explanation
  and the absent desktop recovery action after a fresh uninstall failed restoring
  LG Home. Real CLI/state and Qt with simulated TV IO check same TV/custom port,
  default-No inspection, unchanged journal after cancellation and no package
  removal request. Existing #256 tests verify successful guarded continuation.
- Recovery report cases cover inherited installs, unexpected fields, malformed
  removal maps, private keys/values and Root isolation. Android bridge tests check
  localized guidance, review-only navigation and no review offer on refusal.
- `npm ci` completed. `scripts/test.sh installer setup android` passed: 668 cytv
  tests (2 optional skips), 222 setup, 27 Android, plus Homebrew checks. The
  configured Python environment includes build dependencies and Qt; an initial
  run with bare Python lacked fonttools and was not counted as passing evidence.
- `node android/tests/maintenance.cjs` passed with actual Chrome: 12 locales,
  both new guidance codes, narrow/landscape layouts and no unsolicited operations.
- Final focused Qt/recovery/localization/Android bridge run: 55 tests passed after
  review corrections. `git diff --check` passed.
- Independent read-only review found no blocking defects. Its two minor notes
  (gate reference and primary-button hierarchy) were corrected.
- Current recovery reference, diagnostic field contract and all 12 localized
  guides updated. Installer translation coverage checks passed. Native-speaker
  review was not performed.

Test environment: macOS arm64 host, synthetic No-root TV IO and Root negative
cases; no physical TV, firmware or remote used. Installed component versions,
Home/Back/volume, emergency release, audio, standby, cold boot, OTA and rollback
were not tested on hardware. Native Helper/input code and package payloads are
unchanged. No new endpoint, permission or persistent journal format is added.

## Remaining work

Rebuild embedding installers through normal coordinator-owned release work.
The published 1.6.0 installer has neither #256 nor this follow-up. Real recovery
acceptance remains outstanding. #259 still needs its original failure/history;
this source change is not proof that its particular journal qualifies. #201's
already-submitted historical operations retain the existing guards and remain
unresolved. No TV was contacted or changed and no new owner installation report
is published.
