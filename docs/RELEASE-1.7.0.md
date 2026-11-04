# v1.7.0 — Native Root startup choices and theme-owned inputs

This release adds two-source native Root startup choices and theme-owned inputs.
Acceptance is limited to the exact artifacts and scenarios in the linked records;
source integration, CI and package installation do not certify other devices.

## Changes

- Root prepares Clean as the native startup input for selected prior sources.
  In Home settings, **Open Clean Your TV first** defaults to **LG Channels / Live
  TV** on and **YouTube** off. There is no HDMI startup setting, including for
  legacy saved HDMI choices. A source switched off leaves startup to firmware,
  rather than guaranteeing that source resumes. Native preparation still requires
  LG Home Auto Launch on; its global behavior can open Home after HDMI or an
  unselected source. Recent external input mode is not supported by the current
  guard; ordinary Home-button replacement remains separate. See the
  [startup-setting dependency](../root-edition/README.md#candidate-native-startup-choices).
  With **Change Home** off, the two controls
  remain visible, muted and disabled with an explanation; saved choices remain.
  All late boot/wake application-launch paths are removed. Unknown/native API
  failures do not trigger a delayed redirect or automatic Home re-enable.
  Settings reads startup and Home state serially, keeping controls unavailable
  until the service has finished both checks and preserving read-failure advice.
- Root keeps normal-start, shutdown proof, current session/binding, input and
  guardian health, explicit Off, emergency, key-up and watchdog guards. Native
  selection is event-driven, bounded and reversible under the existing lock.
  An acknowledged observer is bound to the actual guardian transaction/session/PID;
  loss withdraws owned priority across activation/operation-lock races without
  depending on Settings availability or replaying native RPCs.
  A separate root-private source-policy file does not extend the installed System
  supervisor's legacy profile schema. It is local to the TV, not portable export.
- Themes choose header menu or input shelf. Built-ins are Classic, Liquid Glass
  and Ribbon; pinned Alpine remains available through Showcase. Preview layers
  switch together, inherit rounding and label unnamed connected inputs. Live
  preview defaults on while preserving an explicitly saved Off. Users can disable
  **Settings → Appearance → Preview inputs on focus**. It remains experimental:
  firmware can play audio or switch HDR; silence is not guaranteed. Home does not
  automatically change global TV mute or HDR settings. Optional date appears below the clock; Retro bytes are unchanged.
- Root input labels use an authenticated read-only service broker where firmware
  denies direct WebApp EIM access. The fixed, bounded query adds no permissions
  or TV-setting writes. Home visibility, a newly focused input and Settings each
  trigger one fresh read; failures leave status unknown. There is no polling,
  automatic retry or continuous hot-plug guarantee. No-root keeps its direct EIM
  subscription where allowed and uses Home's own service plus the paired Helper
  after a definitive access refusal. The fixed read keeps the pairing key in
  Helper and uses a separate metadata exchange, leaving Home commands available.
  On the maintainer C3, exact Home 1.8.1 / Helper 0.6.22 restore all HDMI labels
  and the owner confirmed the live preview. With the console asleep, the paired
  API reports disconnected despite a plugged cable; the owner accepted this
  No-root distinction. Status refreshes on explicit foreground/focus interactions;
  waking an input does not promise continuous hot-plug updates.
- Home broker settings retain access after an explicit cross-package Helper
  status refusal. Original device acceptance for #196 is still outstanding.
- Desktop/Android installers add pinned inspect-only Root collection and preserve
  recovery for a No-root removal stopped before package submission. Uncertain
  submitted operations still require terminal authority and confirmed LG Home.
  Passive collection does not stage or execute device changes. Original device
  recovery reports remain unresolved. A pre-submission removal failure offers
  **Review recovery options** for the same saved TV/port with separate default-No
  confirmations. Fixed diagnostic categories distinguish package-status refusal
  and unsubmitted removal without exporting private journals (#260).
- Legacy vendor/bootstrap prerequisites and Root wake/forward-cancellation
  characterization improve diagnostics without granting unsupported hardware
  compatibility. The multilingual website source is included; deployment follows
  the authorized main-release merge.

## Versions and packaging

| Component | Version 1.6.0 | Version 1.7.0 | Reason |
| --- | --- | --- | --- |
| Home | 1.7.0 | 1.8.1 | Theme/input panel, paired input-label fallback, preview and date behavior |
| Home Helper | 0.6.21 | 0.6.22 | Bounded paired read-only input metadata fallback |
| cytv | 0.7.0 | 0.8.0 | Inspection and recovery behavior; rebuilt payloads |
| Android | 0.6.0 / code 17 | 0.7.0 / code 18 | Shared installer and embedded payload changes |
| Root / infrastructure | 0.7.0 | 0.8.4 | Two-source native policy, Root input status and serialized Settings |
| Both independent Updaters | 0.4.0 | 0.4.2 | Rebuilt shared UI/locales and recovery support; distinct package bytes |
| System target / protocol | 1.2.0 / 1 | 1.2.0 / 1 | Supervisor unchanged; retained 1.1.2 remains separate |

Root, infrastructure, both edition Updaters, HD/FHD Home/Root and all installers
must be rebuilt together. Updater 0.4.1 was not a public release; 0.4.2 avoids
reusing preliminary package identities. Helper 0.6.22 includes the independent paired input-metadata read; earlier Helper acceptance does not establish acceptance of these new bytes.
Root 0.8.4 retains service-read and lifecycle-refresh serialization, the
two-source policy and authenticated input-status snapshot, and rebuilds the shared
input-source frontend with the No-root fallback. It distinguishes
the final package from unpublished 0.8.0, 0.8.1, 0.8.2 and 0.8.3 QA packages.
The initial build pin is superseded; a new full candidate and signed Root set
are required. No equal-version replacement is authorized.
No application ID, signing identity or trust rule changes. Home adds an
authorized same-package `inputStatus` method to its existing service; no new
privilege grant or service registration is required.

## Acceptance and known limits

- #171 stays open for exact-package startup confirmation. Earlier 0.8.3 C3
  observations retain their own hashes: native Clean first from Channels, firmware
  choice with YouTube off, Clean with YouTube on, explicit Home off and physical
  emergency/audio were observed. Root 0.8.4 installed normally with retained
  profile, all 222 signed files verified and native routing active. Its additional
  physical startup/cold-boot/controls/audio/emergency and retained rollback were
  not repeated at the maintainer's explicit request. Unchanged runtime sources
  alone do not accept changed package hashes or waive past observer failures.
- Existing System 1.1.2 remains pinned with its prior channel behavior. Ordinary
  component OTA does not replace the supervisor; there is no general migration
  from that installed version. Do not delete state, reinstall or force equal
  versions. Existing signed rollback and admission requirements remain in force.
- #202 old forward callback, #201 uncertain No-root termination, #259 original
  removal/recovery report, #152 original
  EF950V recovery, #101/#200/#216/#240 recoveries and #160/#164 legacy support
  remain unresolved. Partial diagnostics and source fixes do not close reports.
- The exact signed Android APK passed original-signer/payload verification and
  in-place code17-to-code18 upgrade with synthetic-data retention on the owned
  API35 ARM64 userdebug emulator. No physical phone-to-TV pass is claimed.
- Homebrew catalogue promotion stays disabled. Audio/HDR preview limitations,
  additional models/remotes, physical phone-to-TV paths and universal compatibility
  are not accepted by CI.

The frozen inventory is in `release-plan.json` and release PR
[#246](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/246). Full build
41657841592:1, protected Root signing 41661307514:1, exact artifact hashes,
actual observations and untested paths are in the
[package acceptance record](history/2026-11-03-release-1.7.0-final-packages.md).
The maintainer authorized publication with this bounded evidence and without
repeating previously passed physical tests; unobserved paths remain unobserved.
