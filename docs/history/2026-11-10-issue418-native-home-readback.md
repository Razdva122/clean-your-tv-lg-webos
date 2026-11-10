# Retained native Home removal readback — 2026-11-10

Related issue: #418. This records source investigation and synthetic host checks,
not a report of a new operation on a user's TV. No TV was contacted or changed.
The original activation cause and reporter-device recovery remain unconfirmed.

## Reproduced cause and correction

A successful current native restore leaves its backend selection and inverse
journals intact. Cleanup captures `profileless_cleanup_eligible` before restore;
these native markers make it false. Neither the never-applied proof nor the
empty-evidence compositor proof can then pass, so final routing readback falls
through to Home settings. A firmware without readable Home settings remains
blocked despite native restoration. Retrying preserves this same false checkpoint.

Current authenticated runtime support now returns `native_restored_sha256` only
after exact backend selection, verified current recovery executable, successful
restore and unchanged selection readback. The existing removal receipt binds
that digest to its preserved `home-backend.json`. Only the corresponding exact
native inverse names are admitted; generic profile-routing evidence, another
native backend, mismatched live selection and the profile override remain
refusals. The old profileless flag is not rewritten and original inverse bytes
are not removed or edited.

The existing `stock-compositor` proof verifies the current native identity/hash,
manifest, stock vendor filters, mounts and foreign Home state. It is repeated
before destructive continuation, after restart and during final verification.
The final Node cleaner permits the bound native inverse while requiring every
live routing marker absent before private-runtime retirement and before final
acknowledgement. Its native exception is isolated from `never-applied` admission.
Writer fences, original unknown outcomes, package terminal/absence checks,
restart and private-data cleanup retain their existing authority.

## Verification

- Baseline cleanup suite: 81 cases passed.
- Before the correction, the retained-native regression stopped at
  `original-writers-fenced` on Home settings; the final Node regression refused
  its saved native inverse. Both failed for the intended missing behavior.
- A further negative regression reproduced native proof accidentally admitting
  a contradictory never-applied receipt. Restricting the native exception to
  stock-compositor proof corrected it.
- Final cleanup/coordinator/Node-tail/handoff run: 145 cases passed, two declared
  platform skips, with exact Node 8.12.0 and compiled Node 0.12.2 coverage.
  Cases include actual backend schemas 1/2/3, changed or absent restore proof,
  first/original evidence retention, live/preserved profile journals, opposite
  native backend, selection drift and post-restart routing drift. Existing
  compositor tests cover changed target, vendor chain, mount and foreign Home.
- Independent read-only review found a schema propagation gap in a test, which
  was corrected; final review reported no actionable product findings.
- Python 3.9 grammar, Prettier for the changed JS and whitespace checks pass.
- Broader installer/setup/Android/TV-runtime verification is pending at this
  checkpoint; the implementation PR records the final result.

Host: macOS ARM64, maintained project virtualenv, current Node 23.11.0 and exact
legacy runtimes. Native Home, vendor APIs and installed state are fixture models;
real filesystem/subprocess finalizer checks do not prove physical TV recovery.
TV model, firmware/webOS and remote for new physical tests: unselected/untested.
Installation, Home/remote/audio, emergency controls, standby, cold boot, OTA and
rollback on the reporter's device remain untested.

## Delivery boundaries

No new dependency, permission, endpoint or state file is introduced. The existing
removal receipt gains a bounded backend digest; it is not exported as recovery
authority in diagnostics. Developer contracts and the recovery matrix are
updated. Ordinary Remove/restart/setup controls are unchanged, so the localized
practical guides need no new instructions or release news.

Rebuild normal Root/Updater support and embedding desktop/console/Android
installers through the release coordinator. This task changes no release
version, frozen inventory, selected build, signing or publication state. A source
fix and passing host checks do not establish completion of the original issue.
