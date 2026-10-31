# v1.5.3 — Themes, Root startup and recovery

Status: unpublished combined fix batch integrated into `release/next`. The previous complete build
[41118810865 / attempt 1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41118810865)
from `160f3294d565b25925a8bf128d92a4146860a0b9` remains historical evidence;
its selection is invalidated by the integrated receiver and startup/recovery batch. No replacement
build is selected and acceptance remains empty. All 17 implementation PRs are integrated. First perform focused signed Root QA
for the old-runtime update window, then dispatch one complete replacement build.

[Previous verification](history/2026-10-31-release-1.5.3-combined-verification.md)
records its ten artifacts, nine installer payloads, macOS execution and Android
checks. The [physical matrix](history/2026-10-31-release-1.5.3-physical-qa.md)
records two update Home-resume failures and a separate standby failure. These
results do not accept replacement bytes or universal TV compatibility.

## Changes

- #199 (#198): hold the receiver service activity until its session ends, so the
  standalone service idle timer cannot close the HTTP listener while a PIN waits.
  Integrated in `release/next`; normal delivery and original webOS 5/No-root
  confirmation remain pending.
- #205: #204 owned native EIM first-screen startup and cleanup;
  #202 automatic recovery preserving update Home resumption; #203 bounded
  compressed maintainer SSH admission; refreshed Classic README main screenshot
  and three built-in theme previews. [Batch verification](history/2026-10-31-release-1.5.3-native-startup-batch.md) records final PR CI and limits.
  The EIM enabled-mode C3 experiment is not final package acceptance or a fix for
  #171. Additional shutdown-decision diagnostics preserve existing safety policy.
  An old callback can still run before its runtime is replaced; #202 therefore
  needs actual old-baseline update acceptance, not cancellation-receipt clearing.

- #193: refresh the Ribbon README screenshot and link theme browsing to the main
  interactive preview. Remove the standalone public theme catalogue page and its
  navigation link; on-TV Showcase and offline author review remain available.
- #192 (#152): avoid false active-Helper detection when legacy grep ignores exact
  matching, preserving real-process and uncertain-state guards. Add bounded LS2
  diagnostic categories. Original EF950V installation/control failures remain
  unresolved; reporter history and target-device confirmation are still needed.
- #189: use smaller complete GitHub job pages for signed Root QA admission while
  retaining exact-attempt, source, package and signature verification.

- #191: separate Appearance layout/app controls from Themes, add ID-first theme installation, show the effective Columns count and place language choices directly in their category. Remote navigation, delayed-status focus and twelve-language browser checks passed; physical TV acceptance remains pending.

- #188: bundle Ribbon for offline selection in both editions, with theme-driven
  scenic ribbon geometry, slanted cards and shortcut placement. Navigation enters
  Settings at the visible left edge, including after the application window moves.
  The existing Classic default remains. Theme authoring uses the optional
  `ribbon-layout-v1` capability; older Home versions reject unsupported imports
  before replacing the selected theme. Physical remote acceptance is pending.

- #175 and #183 (#160, #164): visible prerequisite results in console, desktop
  and Android, retained failure rows and diagnostic-report guidance. Root still
  requires TV Node.js 8+ and supported Python/Home interfaces. This improves
  diagnosis, not the original reporters' unsupported runtime or connection.
- #176 (#170): fixed-layout themes preserve hidden Columns geometry during
  Appearance Apply; hidden controls remain unavailable to pointer, keyboard and
  accessibility navigation. Installed-package acceptance is still required.
- #181 (#152): compile Helper for Node 0.10.25+, use descriptor-safe pairing-key
  reads and compatible vendored WebSocket calls. Published baseline pairing and
  emergency/watchdog guards remain authoritative. EF950V installation, input,
  power behavior and rollback remain unverified until actual target-TV results.
- #177 (#133): isolate maintainer read-only admission from retained Python code
  and obtain the original candidate from its authenticated operation. This does
  not perform individual recovery or add a Settings-only firmware adapter.
- #180 (#171): record guarded wake refusal stages and bounded private power-stream
  outcomes. This is diagnostic coverage, not a fix for automatic Home after wake.
- #117 (#116): explain exact Homebrew exec denial in twelve languages, preserve
  original request IDs and inspect before retry. Supported upstream prerequisite,
  exact-artifact acceptance and public Homebrew promotion remain pending.

## Component versions

| Component | Published 1.5.2 | Candidate 1.5.3 | Reason |
| --- | --- | --- | --- |
| cytv | 0.6.0 | 0.6.1 | Changed preflight, visible checks and recovery tooling |
| Home | 1.6.0 | 1.6.1 | Ribbon, shared layout module and Appearance CSS |
| Home Helper | 0.6.20 | 0.6.21 | Node 0.10.25/runtime and pairing-key handling |
| Root | 0.6.1 | 0.6.2 | Shared UI, Home resume, native startup and infrastructure diagnostics |
| Both edition Updaters | 0.3.3 | 0.3.4 | Both embed changed Appearance CSS |
| Android / versionCode | 0.5.0 / 15 | 0.5.1 / 16 | Changed UI/native replay/bridge and embedded payload |
| System supervisor | 1.1.2 | 1.1.2 | Executable supervisor/IPK closure unchanged |

Home, Helper, Root/infrastructure, both Updaters and all computer/Android installers
must rebuild together after the batch is integrated. The changed Helper runtime requires a new
version; published 0.6.20 must not be replaced with different bytes. Existing supervisors remain pinned;
normal admission, signatures and minimum-supervisor checks remain unchanged.

## Delivery and acceptance limits

The existing Helper rollback record approves only the exact 0.6.19 to 0.6.20
transition. It does not approve 0.6.20 to 0.6.21 or cover the vendored/runtime
changes under a permission-only exception. The new raw/canonical Helper hashes
and authenticated published Home 1.6.0 / Helper 0.6.20 rollback bytes are recorded
in the final verification report. The new transition still needs applicable
acceptance or explicit exact-scope approval;
publication must remain blocked until that gate is truthfully satisfied.

The [unattended C3 record](history/2026-10-30-unattended-c3-ui-proof.md) tested the
installed Root 0.6.1 baseline plus a temporary in-memory footprint proof. It is
not acceptance of these new packages. Its clean restoration and renderer result
retain their original artifact scope.

#171 standby remains unresolved. The previous release's limited-risk decision
is not a new passing result or automatic approval of this release. Record an
explicit fix/follow-up decision and the affected artifact tests before final
release approval. Root firmware support and other users' retained recovery remain
separate unresolved work. The independent Homebrew Installer stays unreleased
with promotion disabled.

Build 41118810865 / attempt 1 and older 41095949258 / attempt 2 retain only
their historical artifact scope. The replacement candidate needs complete CI,
artifact verification, signing and affected physical acceptance. Standby #171
and the Helper transition gate remain explicit publication blockers. No new
physical compatibility, phone acceptance or completed device recovery is claimed.

## Accepted remaining limitations

The maintainer deferred further fixes/retests for [Home preference loss during
update/rollback (#202)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/202)
and [stale Home settings after emergency/resume (#206)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/206).
After a transition, explicitly enable Change Home in normal settings if needed;
close and reopen Settings if its toggle is stale, then wait for the Clean status.
These are known failures, not successful automatic Home resumption.
The [signed C3 QA record](history/2026-10-31-release-1.5.3-signed-root-qa.md)
separates startup/controls passes from failures and untested paths.
