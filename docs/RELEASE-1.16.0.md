# v1.16.0 — settings, photos and installation

Published from [PR #475](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/475).
See the [accepted build, hashes and scoped C3 QA record](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.16.0/docs/history/2026-11-10-release-1.16.0-candidate.md#r2-04-and-final-selected-case-exit-check).

## Changes

- Accept HEIC/HEIF wallpaper photos on the phone page, using native decoding or
  a bundled local worker. Preserve crop, PIN, JPEG transfer and cancellation;
  no external conversion service is used (#477).
- Offer optional post-install Classic/Liquid Glass/Ribbon previews, weather
  and mode-specific renewal Beta or LG firmware blocking. Skip/cancel preserves
  installation success; unchanged mode settings are preserved (#482).
- Correct Settings D-pad grids, compact Root navigation, focus memory,
  language focus and initial weather state. Unknown No-root Home status remains
  retryable; HDMI audio distinguishes loading, themes wrap, wallpaper removal
  asks for confirmation and Developer Mode retains Back (#483).
- Finish removal without a mandatory restart only when current controls/startup,
  absence and process proofs succeed. Preserve required restart and pending
  recovery; distinguish connection loss and package refusal (#481). Correct
  retained-native cleanup Home readback (#478, partial #418).
- Remove the generic C3-only notice without weakening capability checks (#479,
  partial #101). Retain bounded attempt-matched Root driver failure diagnostics
  without raw exception prose or replaying work (#480, partial #397).

- Preserve safe No-root boot-check failure categories in diagnostic reports and
  history, including fixed filesystem/guard details. Reject failure envelopes
  before accepting restart proof. The original C5 removal cause is still unknown
  (#485, partial #472).
- Correct Root recovery verification for the bundled HEIC service: allow up to
  4 MiB only for the exact private service entry in runtime, retained Updater and
  bootstrap checks; preserve digest, path and file-safety validation (#489).

## Versions and packaging

| Component | Published v1.15.0 | Candidate | Reason |
| --- | --- | --- | --- |
| Release | 1.15.0 | 1.16.0 | Installer personalization and HEIC support |
| Home FHD/HD | 1.14.0 | 1.15.0 | Settings, launch parameters and receiver |
| Helper | 0.8.0 | 0.8.0 | Exact published bytes verified |
| cytv | 0.16.0 | 0.17.0 | Personalization, removal and diagnostics |
| Android / versionCode | 0.15.0 / 30 | 0.16.0 / 31 | Shared operations and payload |
| Root / infrastructure | 0.15.0 | 0.16.0 | UI, cleanup/coordinator and bounded recovery checks |
| Both edition Updaters | 0.5.6 | 0.5.7 | Shared UI and embedded removal code |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 | Exact published bundle; no supervisor migration |

Rebuild both-resolution Home/Root and normal/Beta/experimental support, CLI,
four desktop platforms and Android. Preserve Android package ID and original
signer. No Homebrew Installer promotion is selected. App-owned
`tvhome.installer.settings.v1` prevents repeated personalization requests;
removal proof fields preserve recovery goals. No new privileged permission or
network endpoint is introduced.

## Validation and limits

[Full replacement42808578156:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42808578156)
passes all23 jobs on frozen source `f23ab1ac`. Exact final CLI/APK provenance,
original APK signer, all601 payload files and CLI offline checks pass. Protected
Root QA signing42811994143 succeeded with `publish=false`; its signed components
match the final CLI payload. The successful build and scoped acceptance are
pinned together in release-plan.json. Publication and public package/feed
verification completed in [workflow42821319650](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42821319650).

On the maintainer-owned C3 OLED55C3RLA/43.21.71/webOS SDK11.2.0, normal Root FHD
signed update, runtime and actual retained-Updater integrity, live profile/
preferences/Home-Off retention, ordinary rollback→forward and final owner-confirmed
arrows/OK/Back, short Home to LG Home, volume/audio pass. Exact hashes, initial
states, observed results and limits are in the canonical candidate ledger.
The first candidate's recovery failure #489 remains in history; the complete
original case pass preceded the reviewed fix batch and single replacement build.

Settings/receiver results are reused only for identical IPKs/dependencies and
matching device preconditions. New affected HD closure/policy validation is
data-only. The old exact-APK original-signer code30→31 emulator upgrade, four
retained synthetic files and Store/native/idle observations retain their old
artifact scope. The new APK's59 Python/11 UI sources and native entries were
checked independently. All280 pyc differences are confined to timestamp bytes;
the bytecode bodies are identical. No new physical-phone upgrade is claimed.

No physical No-root install, iPhone/live phone transfer, destructive removal,
edition switch, Home-On/emergency, standby/restart/cold boot, firmware blocking or
public-feed test is newly accepted. One C3 and browser tests do not establish
universal compatibility. Original reports #418/#101/#397/#472 remain unresolved;
#489 is delivered in this release with scoped C3 acceptance. Protected combined
signing and public-package/feed verification completed; the limitations above
still apply.
