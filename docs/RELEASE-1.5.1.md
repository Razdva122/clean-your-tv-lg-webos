# v1.5.1 — Faster development and release delivery

This maintenance release changes developer tooling, CI and release coordination.
It does not change the TV application, services, updater or installer behavior.
All component versions remain those published in 1.5.0; only the overall release
version advances. Existing Root limitations remain: Appearance can shift during
Apply and automatic Home after standby can fail. See the
[1.5.0 tested scope and limitations](RELEASE-1.5.0.md).

## Developer feedback

- `scripts/tv-dev.py ui --device lgtv --owner-present --watch` compiles and reloads
  an isolated hosted UI with simulated TV APIs and separate localStorage/IndexedDB.
  It refuses startup when native globals cannot be isolated. `--stage-only`
  compiles without a TV. Hosted rendering on real hardware remains untested by
  this maintenance release.
- Direct Root QA compiles coherent Root, updater and infrastructure packages
  without waiting for desktop or Android packaging. Affected runtime safety
  checks remain before signed delivery. One command dispatches, waits, downloads
  and verifies the protected signed artifact; explicit preflight/install uses
  the original installed verifier and worker. No equal-version or recovery bypass
  is added. See [TV development](development/TV-DEVELOPMENT.md).
- Theme-only iteration continues to use the existing computer-to-TV receiver.

## CI and release flow

- Ordinary PRs run affected checks. Visual assets use UI compatibility and browser
  smoke; behavior changes retain relevant controls, watchdog, emergency, update
  and recovery regressions. Shared/unknown inputs broaden checks.
- Full theme browser coverage and all release platforms run on an explicitly
  dispatched frozen candidate. Runtime and browser jobs run concurrently.
  Required status summaries include failures in every selected job; preliminary
  success cannot satisfy the separate full-release gate.
- Ordinary pushes no longer build all installers or cancel a frozen build.
  Equivalent documentation/evidence edits retain the pinned artifact, and failed
  jobs can be retried without rebuilding successful jobs. Preview tests run once.
- Automatic publication grants the reusable signer its required Actions read
  permission, fixing a workflow permission incompatibility that can prevent startup.
- One coordinator owns frozen scope and the current acceptance record. Developer
  checks, documentation and physical observations follow the affected scope.

## Validation and acceptance boundaries

Local runtime, setup, installer, Android and preview test groups passed, as did
legacy/geometry/settings/theme browser tests, workflow lint, direct package
validation and independent review. The staged UI browser test verifies actual
compiled rendering, theme assets, storage isolation and blocked native calls.
The final candidate's complete platform/test results and artifact comparison are
recorded in the [validation record](history/2026-10-30-release-1.5.1-validation.md)
and [release PR #173](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/173).

No TV was connected, installed or modified for this maintenance work. No new
Home routing, controls, sound, standby, cold-boot, OTA or rollback pass is claimed.
The unchanged TV packages retain the earlier release's limited evidence and
known failures; source-level tooling tests do not extend device compatibility.
