# Separate installer outcomes — 2026-11-01

## Source behavior

Third stage of the maintainer-requested installer improvements. Console, desktop
and Android distinguish package verification, launch submission/acknowledgement,
startup evidence and physical Home behavior reported by the owner.

Existing No-root package version verification and Root package/updater proofs mark
packages verified. A lost launch response remains submitted/unconfirmed and keeps
existing recovery records; it is not labelled not installed or retried. No-root
adds one read-only existing Helper process probe after successful installation,
with a five-second timeout. Missing/failed readback remains unverified without
undoing completed packages. A process observation does not certify controller,
relay, service or actual key health. Root reuses its existing guardian and routes
readback; no additional Root activation/status operation is introduced.

After successful setup or explicitly confirmed Root continuation, the owner opens
another TV app and briefly presses physical Home once, then chooses CYTV Home,
LG Home/no expected response, or skip. Default is skip. `--yes` cannot answer,
noninteractive operation and EOF/Ctrl+C here leave it untested. This optional
observation does not undo installation, reopen pending, retry setup, change
routing, clear emergency stop or publish anything. Local reports identify the
owner observation explicitly. Other controls, sound, standby, cold boot, OTA and
rollback remain untested; one button press is not universal compatibility.

Qt and Android prioritize the three outcome rows over prerequisites. Incomplete
checks show Review TV checks and retain report access; only all three passes
show Home button confirmed by you. Android offers semantic numeric choices,
focuses skip and consumes options once. New runs clear prior results. Reports
revalidate fixed `tv.setup_outcome` fields and check statuses, dropping unknown
fields/types; no free text, app inventories, addresses or private data are added.
These facts grant no deployment/recovery or release-acceptance authority.

Current CLI/diagnostic references and all twelve installer guides describe the
unpublished behavior. Czech remains TV-only. No dependency, endpoint, permission,
persistent TV file, retained worker or Root runtime changes. Rebuild embedding
installers through normal candidate preparation; no version/build/freeze selected.
[Evidence contract](../development/INSTALLER-OUTCOMES.md).

## Verification and limits

- `npm ci` completed before implementation.
- Red/green tests cover independent package/launch/runtime/Home evidence, default
  skip/noninteractive/EOF, per-run reset, hostile export data, lost launch response
  with verified packages/preserved pending, optional readback failure after success,
  and existing Root readback remaining separate from physical Home.
- `scripts/test.sh installer android setup` passes: 613 installer cases (two
  expected platform skips), 25 Android, 220 setup plus Homebrew payload/runtime/
  bridge/continuation checks. A later strengthened Qt case models #207's key
  distinction: packages/process pass while owner-reported Home fails, with report
  save, no reinstall and no pending receipt. All 34 Qt recovery/GUI cases pass.
- Real Chrome maintenance/result/prompt tests pass in twelve locales, including
  narrow/landscape layouts, default-skip Enter, all three owner outcomes, outcome
  ordering, per-run reset, target/custom-port preservation and operation recreation.
  Twelve-language picker/persistence/native-message tests also pass. A rendered
  Russian Qt fixture was visually inspected; no device screenshot was used.
- Independent read-only review found no remaining actionable correctness/safety
  findings, including the final sorting-only display change. Changed Markdown
  relative-file links and `git diff --check` pass.

Host/transport/UI simulations only. No TV was contacted, staged or changed;
model/firmware/remote are not applicable to these fixtures. No owner installation
result or raw evidence is published. Original #207 standard-remote routing remains
unresolved and open/planned; this is partial diagnosis/workflow improvement.
Final selected CI and integration are recorded below after verification.

A final prompt-localization regression found that whitespace in the full prompt
key and the desktop's stripped title left English text in non-English sessions.
The new test failed in all eleven translated locales, then passed after fixing
both keys. Hindi now explicitly says press and release Home once briefly. All
64 affected localization/actual-Qt/Android-bridge cases pass after this correction;
no device behavior or observation default changed.

## Integration

[PR #234](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/234) merged into
`release/next` as `252a8a88403a25915a9ecc97da5e38f88b9b382b` after final source
`bfe83a9a9ea6df56b975c6ec7f5042e5fdfec1e0` passed the selected
[Linux/macOS/ARM checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41332068921),
[frozen Windows/macOS Intel runtime](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41332068891)
and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41332068897).
Linux CI ran 614 installer cases (36 expected optional/platform skips), 25 Android
and 220 setup cases. Actual Qt and Chrome were verified locally as recorded above.
Browser/release-build/publication jobs were correctly skipped for focused CI.
Merged product and test files match the verified source. A zero install exit code
means setup work completed, not that skipped or owner-reported failing Home checks
passed; those separate statuses remain in the local report.

Candidate #210 inventory includes this partial improvement without selecting a
version, frozen package or physical acceptance. Original #207 stays open/planned;
its standard-remote mapping is unchanged and no extra owner test is requested.
The source-integration comment, current label and candidate record are verified
as part of integration. No physical result or shipping notice is claimed.
