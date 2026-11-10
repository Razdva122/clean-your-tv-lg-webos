# v1.16.0 — settings, photos and installation

Unpublished candidate in [PR #475](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/475).
See the [candidate ledger](history/2026-11-10-release-1.16.0-candidate.md)
for build evidence and remaining acceptance. Candidate preparation does not authorize publication.

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

## Versions and packaging

| Component | Published v1.15.0 | Candidate | Reason |
| --- | --- | --- | --- |
| Release | 1.15.0 | 1.16.0 | Installer personalization and HEIC support |
| Home FHD/HD | 1.14.0 | 1.15.0 | Settings, launch parameters and receiver |
| Helper | 0.8.0 | 0.8.0 | Exact published bytes verified |
| cytv | 0.16.0 | 0.17.0 | Personalization, removal and diagnostics |
| Android / versionCode | 0.15.0 / 30 | 0.16.0 / 31 | Shared operations and payload |
| Root / infrastructure | 0.15.0 | 0.16.0 | UI and cleanup/coordinator support |
| Both edition Updaters | 0.5.6 | 0.5.7 | Shared UI and embedded removal code |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 | Exact published bundle; no supervisor migration |

Rebuild both-resolution Home/Root and normal/Beta/experimental support, CLI,
four desktop platforms and Android. Preserve Android package ID and original
signer. No Homebrew Installer promotion is selected. App-owned
`tvhome.installer.settings.v1` prevents repeated personalization requests;
removal proof fields preserve recovery goals. No new privileged permission or
network endpoint is introduced.

## Validation and limits

Implementation CI and focused integration checks are linked in #475.
Pre-dispatch payload construction and all-variant version checks passed;
published baseline hashes and both signed system feeds were authenticated.
[Final full candidate42783898383:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42783898383)
passes all23 jobs on source `fa2abc9d`. Exact macOS ARM64 CLI payload/runtime
and original-signer production APK checks pass; all601 payload entries match
focused package preflight. The selected build is pinned in release-plan.json.
These host checks do not complete device acceptance or authorize publication.

No TV operation or new hardware acceptance is performed for this preparation.
Home routing, audible sound, emergency controls, standby, cold boot, OTA,
rollback, physical iPhone decoding and live phone-to-TV remain untested on new
artifacts. Final original-signer Android upgrade and retained-state checks remain
a publication gate. Browser tests do not establish device compatibility.
Original reports #418, #101, #397 and #472 remain open and unresolved.
