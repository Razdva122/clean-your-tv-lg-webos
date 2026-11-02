# v1.6.0 — Installer recovery, diagnostics and adaptive Home

**Frozen candidate, not published.** Public stable remains v1.5.4. The complete
build is pinned. Scoped C3 Root update/controls/power/retained-rollback and Android
emulator upgrade observations are recorded below; full acceptance and normal
signed publication remain pending. No TV result is inferred from source checks.

## Changes

- The installer preserves the initiating failure separately from later checks,
  exports filtered metadata/status, offers separately confirmed recovery, separates
  package/startup/owner-observed Home outcomes, checks required Root Home interfaces
  before private runtime/package preparation, and explains known connection errors.
  Default-No recovery and default-skip Home observation remain explicit; no blind
  reinstall, trust deletion or pending-record bypass is introduced.
- Fresh desktop/Android setup selects verified HD/FHD Home and Root packages.
  New updater clients use separate signed graphics feeds and retain exact rollback.
  Unknown capability stops safely. Existing pinned clients retain their old logic;
  migration limitations below are material.
- Home adds Czech TV localization, Minimal/Retro themes, automatic compact Chinese
  fonts prepared on the build host, and guarded Root Settings refresh after
  lifecycle changes. Installers retain their twelve languages. The standalone web
  Showcase builder is retired; the inline preview/catalogue remain.
- Root retains bounded worker/host diagnostics and pinned individual recovery
  handoff preparation. Retained rollback captures Home intent earlier; forward
  cancellation and individual recovery reports remain unresolved. The Node 0.12.2
  prototype remains opt-in and is not enabled in candidate packages; Root requires
  TV Node 8+.

## Versions and package decisions

| Component | Published v1.5.4 | Candidate v1.6.0 | Reason |
| --- | --- | --- | --- |
| Home | 1.6.1 | 1.7.0 | HD/FHD, Czech, themes, compact Chinese fonts |
| Home Helper | 0.6.21 | 0.6.21 | Production input/service sources unchanged; compare rebuilt package to published bytes |
| cytv | 0.6.1 | 0.7.0 | Five installer improvements and dual payloads |
| Android | 0.5.1 / code 16 | 0.6.0 / code 17 | Shared installer behavior, payloads and in-place update identity |
| Root / infrastructure | 0.6.2 | 0.7.0 | Shared frontend, Settings, retained-rollback guards and worker evidence |
| Independent No-root / Root Updaters | 0.3.4 | 0.4.0 | Graphics selection, fonts and copied recovery/support bytes |
| System Updater | 1.1.2 | 1.2.0 | New selector/policy/support package identity; protocol1 retained |

All affected packages/installers must be rebuilt together. Root and infrastructure
share the Root version; the System supervisor is independently pinned. Component
versions do not inherit the overall release number. No application ID, public
signer, trust rule or recovery schema is changed by version selection.

## Upgrade and known limitations

- Already provisioned updater code is not replaced by ordinary component OTA.
  Existing System 1.1.2 stays pinned with its previous channel behavior; this release
  has **no general replacement path for that owner**. Do not reinstall, delete its
  state or force an equal-version replacement to obtain graphics selection.
  The explicit replacement command still admits only verified old 1.1.0/1.1.1,
  targets 1.2.0 and preserves its historical1.1.1 proof. Fresh eligible setup may
  provision1.2.0. Each real transition requires separate exact-package acceptance.
- Signed Root feeds retain minimumSupervisorVersion1.1.1, preserving existing
  admission without claiming new selector behavior. The first legacy Home HD feed
  is withheld until a genuine compatible published HD rollback exists. Root/System
  recovery continues to use the original authenticated baseline.
- #202 forward-update Home cancellation and its actual caller remain unresolved;
  active retained rollback now has scoped C3 evidence in the dated QA record. #171's
  earlier wake failure and #207's standard-remote Home interception remain separate.
  Preserve explicit Off/emergency cancellation. Control/data/audio loss or broken
  update/recovery blocks delivery.
- Individual Root recoveries (#101/#133/#161/#200/#216), uncertain No-root package
  termination (#201), and reporter requests (#217/#229/#230) remain open under
  their actual statuses. Missing firmware interfaces have no Settings-only adapter.
- No native-speaker Czech, physical Chinese rendering, physical phone-to-TV,
  additional model/remote, eARC or universal compatibility acceptance is claimed.
  Older evidence retains its exact artifact and firmware limits. Homebrew catalogue
  promotion remains disabled; an optional build is not release acceptance.

## Frozen inventory

New feature PRs, including currently open site/theme work, are held for the next
cycle. The 22 integrated changes below form the implementation scope; release
preparation/verification is collected separately without expanding that scope.
Partial issue summaries remain partial; no automatic issue closure is requested.

| PR | Included scope |
| --- | --- |
| [#194](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/194) | Add opt-in host-only Root Node 0.12.2 prototype and legacy HTTPS options correction; Node 8+ admission retained, #160/#164 installation paths remain unresolved |
| [#197](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/197) | Add Minimal 1.0.1 and preserve existing theme order; append new community themes, with maintainer browser acceptance only |
| [#212](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/212) | Guarded No-root Helper stop after service refusal and prefixed WebKit layouts; #152 actual device recovery/control acceptance remains pending |
| [#213](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/213) | Document passive bounded Root worker diagnostics before admission; #161 actual recovery remains unresolved pending owner evidence |
| [#214](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/214) | Simplify theme suggestions and move review work to maintainers |
| [#215](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/215) | Integrate Retro 1.0.0 API 1 with verified corrected distribution pin and offline catalogue; original font/effect/date requirements in #69 remain follow-up |
| [#218](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/218) | Preserve pending No-root journals when installer termination is unproven; #201 reconciliation remains unresolved |
| [#219](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/219) | Remove retired standalone web Showcase builder/assets/tests; retain inline theme preview, TV catalogue and author runtime cards |
| [#220](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/220) | Add allowlisted host Python download/cache failure reasons; #200 original macOS cause and pending Root recovery remain unresolved |
| [#221](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/221) | Prepare pinned individual Root recovery handoffs and fixed host command-boundary diagnostics; original #101/#133/#161/#216/#200 recovery remains unresolved |
| [#222](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/222) | Refresh Root Settings status before resumed actions and preserve retained-rollback Home capture; partial #202, old forward cancellation and exact-package device acceptance remain unresolved |
| [#223](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/223) | Skip closed-PR policy preflight writes; preserve SHA-shared open gates; workflow prevention activates on normal main release |
| [#224](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/224) | Add Czech TV Home/Root/settings/theme/audio/updater localization and preserve cs profiles; installer language scope unchanged |
| [#225](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/225) | Add adaptive 720p Home and explicit HD source builds plus read-only IR/panel diagnostics; standard-remote routing and normal-channel HD delivery remain unresolved |
| [#226](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/226) | Select verified HD/FHD packages across desktop/Android and signed OTA; preserve exact rollback, require updater migration and retain unresolved IR/physical acceptance |
| [#228](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/228) | Generate compact Chinese subsets automatically from catalog/compiler inputs with pinned host-only sources, offline cache and SC/TC fallback; physical rendering remains unverified |
| [#231](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/231) | Export allowlisted existing Helper preflight state and incorporate answered C2 dev/listApps evidence; original #229 device report and #201 recovery remain unresolved |
| [#232](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/232) | Preserve operation-bound initiating failures and safe worker categories; export Doctor/status/check/version context across installers; original #229/#230 device reports remain unresolved |
| [#233](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/233) | Add separately confirmed installer recovery with existing guard revalidation and no implicit reinstall; original #201/#216 recovery remains unresolved |
| [#234](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/234) | Separate package/launch/startup and explicitly owner-reported Home with default skip and local reports; #207 IR routing remains unresolved |
| [#235](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/235) | Check existing Root Home interfaces before runtime/package preparation and show typed localized connection guidance; original #133/#216 recovery and #217 connection remain unresolved |
| [#236](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/236) | Align Android smoke checks with safe error navigation: no blind Status/Restore, no automatic request and preserved connection; product behavior unchanged |

## Verification and remaining gates

[Combined source regression audit](history/2026-11-02-installer-five-stage-regression.md)
records the earlier host/UI checks; it does not substitute for the frozen build.
[Freeze/build record](history/2026-11-02-release-1.6.0-freeze.md) records the selected
source, run/attempt, artifact checks and remaining work as execution proceeds.

The complete candidate run41343868494:2 passed and is pinned; see the
[verified artifact hashes](history/2026-11-02-release-1.6.0-artifacts.md).
The [2026-11-02 hardware and emulator record](history/2026-11-02-release-1.6.0-hardware-qa.md)
binds owner-supervised C3 observations to these exact packages and protected Root
signing run41438353337:1. It records original-signer Android code16-to-code17
emulator file retention, Root update with Off preserved, physical controls/audio,
emergency release, separate power modes and active retained rollback. Supervisor
1.1.2 remains installed; fresh1.2.0 provisioning was not tested.

The first On-standby attempt lost intent; the owner reported another application's
code interfered and requested a repeat. That is not a proved cause, and the first
evidence is retained. The repeat reached Clean after an unmeasured LG Channels
screen; true cold start from running Clean showed Clean first. These observations
do not resolve #171 or accept immediate first-screen behavior for standby.

Native Android pending-operation semantics, live phone-to-TV, No-root/HD/IR,
fresh provisioning, interrupted installation and the other untested paths remain
explicit in that record. Full hardware acceptance remains unset and #210 stays
draft; no publication or new risk acceptance is inferred from these scoped passes.
