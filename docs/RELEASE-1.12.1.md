# v1.12.1 — installer diagnostics and verified Root removal

[Release PR #413](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/413).
The maintainer authorized publishing the exact frozen candidate with the known
Home-routing limitation below. [Full candidate 42397755022:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42397755022) passed all 21 jobs at frozen source `704353a6`.
Artifact-bound acceptance, signing and publication remain separate gates; a PR
merge alone does not establish them.

## Changes

- Distinguish denied network access, refused SSH ports and timeouts; offer an
  explicit Doctor recheck and validated connection editing outside pending
  recovery. macOS Settings guidance does not infer the permission switch state
  (#402). Doctor does not install or resume setup.
- Verify local private recovery storage before creating No-root pending state;
  distinguish directory, capsule and incompatible-source failures using fixed
  private categories (#403 / #201). Existing recovery guards and original
  evidence remain; this does not resolve every original installation report.
- Admit Root removal without systemprofile only for an exact missing-service
  response, independently verified stock LG Home and no current/retained routing
  evidence. Preserve ownership, restoration, restart and final absence checks
  (#404 / #240). General webOS 5 installation/routing support and reporter-device
  recovery remain unverified.
- Remove 192 duplicate Python test executions while preserving defined test bodies
  and intentional retained-version variants; delete two obsolete Ribbon prototype
  checks (#407). No production safety scenarios are deliberately removed.
- Retain allowlisted observer filesystem-operation/storage categories without
  paths or new probes (#411 / #409); the original storage failure is unresolved.
- Read and retain validated TV Node versions and fixed missing/launch/output/read
  failure categories before admission/status (#412 / #410). Existing Root, Beta
  and Helper runtime gates remain authoritative; no system Node is replaced.

## Versions and packaging

| Component | Published v1.12.0 | Candidate v1.12.1 |
| --- | --- | --- |
| Home FHD/HD | 1.13.0 | 1.13.1 |
| Home Helper | 0.7.5 | 0.7.5 |
| cytv | 0.13.0 | 0.13.1 |
| Android / versionCode | 0.12.0 / 26 | 0.12.1 / 27 |
| Root / infrastructure | 0.13.0 | 0.13.1 |
| Both edition Updaters | 0.5.2 | 0.5.3 |
| Fresh System / protocol | 1.2.5 / 1 | 1.2.6 / 1 |

Rebuild desktop/Android installers and coherent normal/Beta Root payloads.
Actual SC/TC subset comparison confirms changed font bytes from the new installer
translations, so Home and font-bearing packages advance despite unchanged Home
JavaScript. Helper remains the exact published 0.7.5 package; no new Helper
transition is selected. Rollback inputs are published Home 1.13.0 FHD/HD with the
same Helper. No published version is reused for changed package contents.

Fresh System 1.2.6 includes changed shared Luna support. Component OTA does not
replace retained System code. Explicit replacement still admits only installed
1.1.0/1.1.1, not 1.1.2/1.2.x; an interrupted replacement needs its original bundle
and coordinator. Root Beta remains a separate exact-Node-0.12.2 payload with
ordinary OTA disabled. Homebrew Installer promotion remains disabled.
Android keeps its application ID and original signing identity. The exact final
APK code26-to-code27 upgrade, synthetic-data retention and native fixtures passed
on an isolated API35 ARM64 emulator. Physical phone-to-TV acceptance is untested.

## Validation and remaining acceptance

The [freeze/pre-dispatch record](history/2026-11-07-release-1.12.1-freeze.md)
records scope, actual package/baseline checks, documentation, independent review
and the selected complete21-job build. Earlier PR checks remain separate from
that final frozen-candidate validation.

[Unattended C3 QA](history/2026-11-07-release-1.12.1-unattended-tv-qa.md)
verified the exact signed Root forward/rollback/forward, preserved profile,
renderer/fonts/icons/all 13 locales/three temporary built-in previews,11 read-only
service cases and software Home/Back/arrows, plus 30 s standby/wake. Two initial
harness assumptions were investigated; affected checks passed with correct
readiness/focus preconditions, without product changes or another candidate.
The exact candidate remains installed and the TV was powered off.

[Final artifact acceptance and maintainer disposition](history/2026-11-08-release-1.12.1-publication-acceptance.md)
records the Android upgrade and explicit publication authorization. Physical Home
failed as described below; it is accepted as a known existing limitation.
Retained System 1.2.5 was unchanged; fresh1.2.6 was not physically accepted.
Physical phone-to-TV, audible playback, key-up/emergency, AC cold boot,
No-root/Beta and other firmware are untested in this focused pass. No additional
physical coverage or universal compatibility is claimed.

## Known limitation accepted for this release

On the maintainer C3 / firmware 43.21.71 / LGE MR23, physical Home after startup
opened LG Home in two observed episodes while Root intent, guardian and project
Home routes remained active. [Issue #422](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/422)
remains open. The maintainer confirmed the bug existed previously and explicitly
authorized this release despite it. No fix is included or claimed; the native
keyfilter selection cause remains under investigation.
[Observed failures and release disposition](history/2026-11-08-release-1.12.1-physical-home-qa.md).
