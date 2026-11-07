# v1.12.0 — legacy runtime choices and Root follow-ups

Frozen on 2026-11-07 for [release PR #399](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/399).
[Full build 42384446335:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42384446335) passed all 21 jobs; [verified artifacts and remaining gates](history/2026-11-07-release-1.12.0-artifacts.md). Scoped acceptance is complete with the limitations below; public delivery is confirmed only after signed package/feed verification.
New features remain outside this candidate until publication.

## Changes

- Explicit Root Beta for exactly Node.js 0.12.2 and No-root over existing root SSH
  (#388 / #383). Beta leaves system Node unchanged, keeps Python/vendor/Home
  admission and disables ordinary OTA. It is separate from regular Root and
  experimental compositor Home; original-device compatibility is unverified.
- Root setup continues with a localized warning when optional input discovery
  fails but the required application list is valid (#391 / #389). Input discovery
  stays unverified; missing or malformed required applications still stop setup.
- Hidden apps no longer consume the visible Root icon budget; the exact system
  application root is admitted with existing path/image/size limits (#398 / #394).
  Exact-package C3 acceptance loads all33 original visible icons without project fallbacks.
- The known No-root-to-Root transition block explains backup, explicit full removal
  using the saved Root connection, verified cleanup, then Root setup (#400 / #396).
  Full removal also removes No-root Home and Helper; ownership guards remain.
- Open Root Settings follows transitional Home status with bounded serialized
  read-only polling and a Check status action on exhaustion (#401 / #347).
  Lifecycle cancellation and emergency Off remain; polling never enables Home.
- Fixed private retention summaries distinguish completion/no-op, refusal, missing
  inventory, changed proof and filesystem errors (#401 / #348). Logging cannot
  fail an operation; actual partial unlink counts are retained. Automatic re-entry
  after interrupted staging retirement remains unimplemented.
- Changed SSH identity guidance explains pre-authentication rejection and preserving
  the original profile, keys and pending receipts (#401 / #368). Independent
  verification and a reviewed profile-preserving trust-recovery implementation
  remain necessary; no host-key replacement command is added.

- Windows host validation isolates the generated Beta policy from its unused
  TV-only lock import while retaining every refusal assertion (#405). No product
  behavior or package version changes in this correction.

## Versions and delivery

| Component | Published v1.11.0 | v1.12.0 |
| --- | --- | --- |
| Home FHD/HD | 1.12.0 | 1.13.0 |
| Home Helper | 0.7.5 | 0.7.5 |
| cytv installer | 0.12.0 | 0.13.0 |
| Android / versionCode | 0.11.0 / 25 | 0.12.0 / 26 |
| Root / infrastructure | 0.12.0 | 0.13.0 |
| Both edition Updaters | 0.5.1 | 0.5.2 |
| Fresh System Updater / protocol | 1.2.4 / 1 | 1.2.5 / 1 |

All installer platforms and normal/Beta Root package graphs are rebuilt. Home
also changes because shared Chinese glyph collection includes the new installer
translations; unchanged Home JS is not proof of unchanged package bytes. Helper
0.7.5 is retained exactly; no new Helper source change or transition is selected.
Previous published Home 1.12.0 FHD/HD with the same Helper supplies rollback inputs.

Fresh System 1.2.5 includes changed shared support. Component/UI-only OTA does not
replace a retained System supervisor or deliver its new retention hooks. Explicit
supervisor replacement still admits only installed 1.1.0/1.1.1, not 1.1.2/1.2.x;
this candidate adds no general migration. Interrupted replacements require their
original bundle/coordinator. Root Beta is a distinct exact-Node payload with
ordinary OTA disabled, not acceptance of regular Root on legacy Node.

Android retains the application ID and original signing certificate. Its final
signed APK original-signer code25-to-code26 upgrade and synthetic retained-data
checks passed on an isolated API35 ARM64 emulator; see the
[scoped QA record](history/2026-11-07-release-1.12.0-scoped-qa.md). Physical-phone and live phone-to-TV
operations remain untested. Homebrew Installer
promotion remains disabled; there is no selected release approval.

## Validation and remaining acceptance

[Freeze/preflight record](history/2026-11-07-release-1.12.0-freeze.md) records actual
package checks, baseline authentication and documentation review. Earlier combined
source evidence is in the [integration record](history/2026-11-07-post-1.11.0-integration.md)
and [#401 record](history/2026-11-07-small-issue-followups.md), including its original
failed observer run and separately corrected final CI.

The freeze itself did not access a TV. The later
[scoped QA record](history/2026-11-07-release-1.12.0-scoped-qa.md) records the maintainer's
case selection, explicit physical-Beta deferral, exact APK emulator acceptance,
package browser checks and authorized C3 update. Root icons and Home after explicit
owner enable passed; automatic Home preservation through the update remains
unproved. Owner-confirmed arrows/OK, volume/audible sound and post-standby Settings
convergence passed. After disclosure of the unexpected pre-suspension Home disable, the maintainer
explicitly instructed shipment with this unresolved observation retained as a
follow-up, not a passing automatic-resume result. Legacy Beta bootstrap and original #383/#389 outcomes
remain unverified; partial #348/#368 work leaves those original reports open.
