# v1.12.1 — installer diagnostics and verified Root removal

Unpublished candidate for [release PR #413](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/413).
Downloads still serve published v1.12.0. Full candidate build, artifact-bound
acceptance, signing and publication are separate gates; none is implied by a PR merge.

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
Android keeps its application ID and original signing identity; final exact APK
code26-to-code27 upgrade/retained-data acceptance remains pending.

## Validation and limits

The [freeze and pre-dispatch record](history/2026-11-07-release-1.12.1-freeze.md)
records scope, real package/baseline checks, documentation and planned cases.
Implementation PR checks passed before integration; they are separate from the
combined/frozen candidate matrix. No new TV or phone result is claimed.
Host fixtures do not establish original-device recovery or universal compatibility.
Physical Home/keys/audio/standby/cold boot/OTA/rollback are untested on these new
artifacts until explicitly recorded. Existing limitations and unresolved reports
remain visible in the release PR.
