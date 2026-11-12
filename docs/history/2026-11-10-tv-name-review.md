# TV-name PR review follow-up — 2026-11-10

Scope: [PR #474](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/474),
following the request to keep naming with final post-install theme/weather choices
and investigate the existing primary launch point instead of reinstalling.
Integrated upstream `44efe145` before adapting the feature. No release selection,
version bump, candidate dispatch or device operation was performed for this review.

## Implementation

- The GUI name field and interactive console prompt run after core installation.
  Explicit `--tv-name` works at the same stage for scripted installs; omission
  preserves the current/default preference in non-interactive mode.
- Installer and TV Settings attempt `updateLaunchPoint` for exactly one existing
  primary point, then verify its identity/title with `listLaunchPoints`.
  Secondary shortcuts, ambiguity, denied calls and mismatching readback cannot
  become success. No added shortcut, package rewrite, retry or elevated permission.
- Home's saved preference is independent of the verified system title. Failed
  system updates are reported; diagnostics contain fixed result categories only.
- Consumer-TV API permissions and system loading behavior remain unverified.
  The [OSE reference](https://www.webosose.org/docs/reference/ls2-api/com-webos-service-applicationmanager/#updatelaunchpoint)
  documents the method but is not consumer-TV acceptance evidence.

## Focused verification ledger

Changed input: final-stage integration and primary launch-point rename/readback.
Previous package-installation observations do not cover this new API behavior.

| Case | Result / evidence |
| --- | --- |
| H1: primary selection, exact payload and readback | Host simulations passed in Python and JavaScript |
| H2: secondary-only/ambiguous/wrong-app selection | Rejected before write; host simulations passed |
| H3: denial, timeout, false success, changed identity | Unconfirmed without retry; host simulations passed |
| H4: final page, existing-title prefill, validation and CLI ordering | Python/Qt checks passed |
| H5: later rename, local preference, reload/reset and failed storage | Chromium preview passed for both editions; simulated native bridge for successful system readback |
| H6: post-install launch parameters and one-time name storage | Node and Chromium preview checks passed for both editions |
| H7: localized strings and privacy projection | Host checks passed; all 13 practical guides updated |
| H8: TV web compilation and ES5 build regression | Passed |
| D1: ordinary Developer Mode public-bus rename/readback, restore original | Blocked: physical TV unavailable for this session; no device operation attempted |
| D2: LG Home, system loading screen, direct launch and Home button | Blocked by D1/device availability; not established by host mocks |
| D3: app restart and full power restart persistence | Blocked by D1/device availability; not established by browser reload |

161 focused Python/Qt/CLI/translation/diagnostic tests passed. Name model/profile
and installation-parameter Node checks passed. Both browser suites passed.
The compatibility compiler and web-build regression passed. These are development
checks, not a final release candidate or physical-TV acceptance.

Exit reconciliation: 11 selected groups; 8 host groups passed; 3 device groups
blocked by physical-device availability; no independent host group remains
untested. Device groups remain outstanding and no hardware acceptance is claimed.

## Scope revised for Root Edition

This PR now provides naming only at the final installer step for Root Edition.
The on-TV editor and No-root naming were removed. Earlier simulation results above
describe the previous scope. Physical acceptance of the Root installer rename,
LG Home and startup presentation, and restart persistence remains pending.
