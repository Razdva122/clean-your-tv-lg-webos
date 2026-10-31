# No-root recovery and legacy WebKit source verification — 2026-10-31

[Implementation #212](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/212)
was merged into `release/next` as `659c1a44f855eb9b9d0c4ee195fd30b53bee7f5c`.
The merge tree matches tested source `60a9e89fc9640a57b3e771fa209619d738162522`.
This records source/host verification, not an installation report or TV acceptance.

## Scope and observed host checks

- A definite No-root `helper-disable/-1` refusal can use a trusted ES5 stop
  program over the existing SSH session. It preserves Home preference and
  watchdog state, sets the persistent stop latch, and requires no controller or
  relay process before Restore/removal continues. Unknown outcomes remain blocked.
- Static TV CSS receives legacy WebKit prefixes through PostCSS/Autoprefixer;
  CSSOM writes and runtime theme styles cover focus, scroll and Ribbon geometry.
  The existing Chromium 38 unsupported-feature gate and theme CSS budget remain.
- Local macOS ARM64 host: `scripts/test.sh ui tv installer setup android preview`
  passed 1,860 Python cases (31 expected optional GUI/platform skips) plus
  JavaScript/native checks, with actual Node 0.10.25 and 0.12.2 enabled.
- Seven real-filesystem stop cases passed on those two legacy Node runtimes.
  Orchestration includes Restore followed by resuming a pending removal. Symlink,
  unsafe-directory, live/orphan-worker and unknown-outcome refusals remain covered.
- Compiled Home passed modern, missing-inset/API and prefixed-only WebKit browser
  profiles, 1–8-column geometry and the complete theme browser matrix in both
  editions: 67 successful scenario summaries. Removing prefixed CSSOM writes
  makes the rendered focus-frame regression fail as expected. These are modeled
  engine limitations in current Chromium, not a WebKit 538.2/TV emulator.
- [PR CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41201686125)
  passed Linux/macOS runtime, browser and optional ARM Python checks. The Linux
  privileged ownership step passed the real mixed-UID/shared-group stop-latch
  case. Independent source review approved after two findings were reproduced
  and corrected: runtime theme prefixes and controller write access to a new latch.

## Candidate and acceptance limits

Candidate #210 is unfrozen. Versions remain the published 1.5.4 baseline; no
target version, full candidate build, artifact pin or acceptance is selected.
Affected Home/Root/updater web packages and desktop/Android installers require
rebuilding and version review at freeze. Helper controller/service/relay sources
are unchanged; retaining Helper 0.6.21 requires the normal final artifact checks.

No TV was connected or modified. The original EF950V report
[#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152) remains open:
actual restoration/removal, Home/Back/key release/triple-Home, icon inventory,
audio, standby/wake, true cold boot, OTA and rollback are unverified on new bytes.
No recovery proof or installation report is inferred from host tests. Preserve
the existing profile/recovery state; this integration requests no device action.

Reviewed/updated references: `docs/RECOVERY.md`, `docs/TV-WEB-BUILD.md`,
`docs/development/HOME-INSTALL-GATES.md` and all twelve `docs/i18n/` user guides.
They identify the correction as unreleased. README/downloads/component versions
retain their published baseline; no setup command, dependency or network endpoint
was added. Final candidate documentation and exact-artifact/device gates remain.
