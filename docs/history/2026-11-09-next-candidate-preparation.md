# Next candidate preparation — 2026-11-09

Release coordinator: current preparation chat. Candidate [#442](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/442)
remains an unfrozen draft after published v1.13.0. No final version, complete
candidate build or new device acceptance is selected yet.

## Integration and remaining scope

PRs #441, #444, #449 and #450 were merged with merge commits after inspecting
their descriptions, comments, reviews and successful required checks. Earlier
documentation #445 and compatibility-list #447 are also collected in the plan.
The implementation checks cover their respective revisions; they do not attest
a frozen combined candidate. The combined installer/Android/setup pass is running.

The maintainer explicitly said PR #451 needs further work and requested
coordination with its existing chat. That chat is implementing firmware-capability
selection for the shared ordinary/Beta Home backend. Its old SDK 6–9-only scope
is not final. Do not merge that earlier revision or dispatch the full matrix
before the completed revision, its tests and packaging impact are reviewed.

Issues #437 and #389 are open at `status:awaiting-release` for the integrated
failure-path fixes. Reporter-device confirmation remains outstanding. No reporter
installation result or raw diagnostic is republished in this record. #410's
original outcome must be assessed against the final #451 scope, not its title.

## Proposed packaging, pending final scope

| Component | Published baseline | Proposed target | Reason |
| --- | --- | --- | --- |
| Release | 1.13.0 | 1.14.0 | Installer advisory and expanded Root/Beta backend |
| Home | 1.13.2 | 1.13.2 | No selected Home source change |
| Helper | 0.8.0 | 0.8.0 | No selected Helper source change; exact bytes must match |
| cytv | 0.14.0 | 0.15.0 | Advisory, catalog transport and continuation repair |
| Android / versionCode | 0.13.0 / 28 | 0.14.0 / 29 | Shared installer operations and embedded payload |
| Root | 0.13.2 | TBD | Final #451 runtime and infrastructure closure pending |
| Independent updater | 0.5.4 | TBD | Audit embedded coordinator/recovery closure after #451 |
| Fresh System | 1.2.7 / protocol 1 | TBD | Audit its embedded closure after #451 |

All targets are proposals, not committed version bumps. Home/Helper same-version
packages must be compared with authenticated published bytes before dispatch.
If Helper changes, the mandatory published-Home/new-Helper probe applies before
the full candidate. No Homebrew Installer approval is selected. Preserve Android
application ID, signing identity and stored user data.

## Documentation pass in progress

Reviewed the merged documentation changes in #445/#447/#449, README release
boundaries, `docs/CLI.md`, `docs/DESKTOP_INSTALL.md`, `docs/COMPATIBILITY.md`,
the relevant installer authority/diagnostic/recovery references and
`android/STABLE-READINESS.md`. #449 adds practical advice in all 13 locales.
Its new advisory remains explicitly unreleased in the English component guides.
Localized guides retain practical instructions without release/status banners.
Final #451 changes require a refreshed compatibility/control documentation pass.
Installation, update/removal, recovery and component guides must be reconciled
with the final inventory before readiness; historical results retain their scope.

Also reviewed edition selection, installation, update and recovery instructions,
Root entry-point packaging and the Android guide. Corrected stale v1.13.0
candidate/v1.12.1 download text in Root's README, README's fresh-System note and
the old v1.12.1-candidate reference in recovery. No commands or inbound anchors
changed. Final #451 admission guidance is still owned by its implementation.

## Published baseline authentication

Published v1.13.0 is neither draft nor prerelease. Downloaded BUILD-INFO,
SHA256SUMS, four signed System feeds, both Home graphics IPKs and Helper0.8.0.
Every downloaded checksum matches SHA256SUMS. All four envelopes verify with
the repository's pinned public key; downloaded Home/Helper hashes and sizes match
the signed component bindings. BUILD-INFO source is
`7edc6cecd492c31ebf82940ba0a6a983875c989d`, matching the release target, and its
versions match the unchanged preparation metadata. No credentials or device data
were needed. The following are authenticated published baselines, not new tests:

| Package | SHA-256 |
| --- | --- |
| Home1.13.2 FHD | `a1cef43e5317dc309cb7c424304ce943a1a8c9bb7f2926866d6eb9f3f043f0ec` |
| Home1.13.2 HD | `77cad4a33d8b4fa8e37af6fdb54e32611afde90c7d6f8f2848b40994b4ced1a0` |
| Helper0.8.0 | `6116d99281d2f5c21ff192ddb07ce6cbdae4223573999ac0d310d86ace87e0c2` |

README release metadata checks pass (3 tests), formatting check passes and
`git diff --check` is clean. The combined installer/Android/setup run remains
in progress; no result is inferred from partial output.

## Acceptance planning

No TV is accessed or changed in this preparation. Model, firmware, remote and
installer device for new physical acceptance are unselected. Existing C3 and
Android emulator observations apply only to their original v1.13.0 artifacts.

| Case | Changed path / plausible failure | Smallest useful check | State |
| --- | --- | --- | --- |
| Desktop latest-version advisory | #449 may interrupt setup or bypass explicit choice | GUI/CLI metadata-error and bundled-version regressions, packaged desktop smoke | Host integration pass running; final package pending |
| No-root pending continuation | #444 narrows a checked 0775 key to 0640 | Original-operation continuation, unsafe inode refusal and retained emergency stop regressions; affected device continuation after supported update | Host integration pass running; device untested |
| Root catalog discovery | #450 removes Node subprocess dependency | Actual reader with subprocess loading forbidden, stream/deadline/empty-app checks; packaged setup boundary | Host integration pass running; device untested |
| Root/Beta firmware capabilities | #451 changes admission and compositor integration | Final negative/positive firmware fixtures and exact legacy runtimes, then selected native Home/emergency/recovery cases | Blocked on final #451 revision |
| Android update | New APK embeds changed shared operations | Exact original-signer code28→29 emulator upgrade, retained Store and native operation fixtures | Pending final APK |

Standby, AC cold boot, audio, OTA and rollback are not new passes. Refine their
selection from the final runtime/dependency diff; do not repeat unrelated cases
solely because the release number changes. Existing unresolved blockers remain
gates. Exact build/attempt and artifact hashes are required for later acceptance.
