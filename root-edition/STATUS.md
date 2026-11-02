# Root Edition status

Start with [installation and controls](README.md), [updates](UPDATES.md), or
[recovery](RECOVERY.md).

<a id="current-release-140"></a>
## Release 1.6.0 and scoped acceptance

Release **1.6.0** uses **Root/infrastructure 0.7.0 / Root Updater 0.4.0 /
System 1.2.0**. See [Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases)
for published downloads and [artifact-bound QA](../docs/history/2026-11-02-release-1.6.0-final-acceptance.md) for tested bytes,
C3 controls/audio, startup, emergency/fault/failsafe recovery and signed active
retained rollback. Existing supervisors stay pinned; installed 1.1.2 has no
general migration to 1.2.0. Fresh physical System 1.2.0 is untested. The documented
standby presentation limitation was accepted for 1.6.0; earlier #171,
forward-update cancellation #202 and individual recoveries remain unresolved.
See [release scope and limitations](../docs/RELEASE-1.6.0.md).

The historical **1.4.0 / Root 0.5.0 / Root Updater 0.3.1**
[acceptance record](../docs/RELEASE-1.4.0-ACCEPTANCE.md) identifies exact
artifacts and the C3 / firmware 43.21.71 / SDK 11.2.0 test scope: corrected
startup, standby, off/emergency preservation and manual whole-product rollback.
It does not establish compatibility with other models or automatic signed rollback.

**Existing original 1.3.0 System Updater:** published 1.4.0 is incompatible with
its destination inventory. An aborted pre-replacement attempt installed nothing.
Preserve its journal and private pins; see [the supported #115 replacement and
recovery boundaries](../docs/development/ROOT-OTA-13-COMPATIBILITY.md).

Other models/firmwares, original C2/C5/NANO reports, audible eARC recovery and
physical Android phone-to-TV recovery remain unverified. Homebrew Installer is
unreleased. [Release notes](../docs/RELEASE-1.6.0.md) describe the scope;
[Homebrew acceptance](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md) is separate.

## Historical evidence

The [original investigation and dated RC results](HISTORY.md) retain their
original wording, artifact identities and limitations. They are evidence for
those tests, not current setup instructions. The [Root acceptance record](RELEASE-ACCEPTANCE.md),
[testing log](TESTING.md), [0.1.1](ROOT-0.1.1.md) and
[0.1.0](ROOT-STABLE-0.1.0.md) records remain unchanged.

Old section links continue below and lead to their original evidence.

<a id="110-stable-status--2026-10-25"></a>
**1.1.0 stable status — 2026-10-25.** See [HISTORY.md](HISTORY.md#110-stable-status--2026-10-25).

<a id="what-passed"></a>
**What passed.** See [HISTORY.md](HISTORY.md#what-passed).

<a id="earlier-registration-failure-and-subsequent-isolated-success"></a>
**Earlier registration failure and subsequent isolated success.** See [HISTORY.md](HISTORY.md#earlier-registration-failure-and-subsequent-isolated-success).

<a id="what-remains-before-a-release"></a>
**What remains before a release.** See [HISTORY.md](HISTORY.md#what-remains-before-a-release).

<a id="scope-of-public-tools"></a>
**Scope of public tools.** See [HISTORY.md](HISTORY.md#scope-of-public-tools).

<a id="release-preparation"></a>
**Release preparation.** See [HISTORY.md](HISTORY.md#release-preparation).

<a id="current-installable-candidate"></a>
**Current installable candidate.** See [HISTORY.md](HISTORY.md#current-installable-candidate).

<a id="integrated-recovery-preparation--2026-10-23"></a>
**Integrated recovery preparation — 2026-10-23.** See [HISTORY.md](HISTORY.md#integrated-recovery-preparation--2026-10-23).

<a id="integrated-routing-and-reboot-recovery--2026-10-23"></a>
**Integrated routing and reboot recovery — 2026-10-23.** See [HISTORY.md](HISTORY.md#integrated-routing-and-reboot-recovery--2026-10-23).

<a id="clean-installation-and-removal--rc7-2026-10-23"></a>
**Clean installation and removal — RC7, 2026-10-23.** See [HISTORY.md](HISTORY.md#clean-installation-and-removal--rc7-2026-10-23).

<a id="rc7-failsafe-recovery--2026-10-23"></a>
**RC7 failsafe recovery — 2026-10-23.** See [HISTORY.md](HISTORY.md#rc7-failsafe-recovery--2026-10-23).

<a id="rc8-local-exit-ui"></a>
**RC8 local exit UI.** See [HISTORY.md](HISTORY.md#rc8-local-exit-ui).

<a id="rc10-ui-exit-accepted--2026-10-23"></a>
**RC10 UI exit accepted — 2026-10-23.** See [HISTORY.md](HISTORY.md#rc10-ui-exit-accepted--2026-10-23).

<a id="independent-triple-home-observer--local-candidate"></a>
**Independent triple-Home observer — local candidate.** See [HISTORY.md](HISTORY.md#independent-triple-home-observer--local-candidate).

<a id="rc13-bounded-emergency-exit-accepted--2026-10-23"></a>
**RC13 bounded emergency exit accepted — 2026-10-23.** See [HISTORY.md](HISTORY.md#rc13-bounded-emergency-exit-accepted--2026-10-23).

<a id="persistent-mode-lifecycle-foundation--local-only"></a>
**Persistent-mode lifecycle foundation — local only.** See [HISTORY.md](HISTORY.md#persistent-mode-lifecycle-foundation--local-only).

<a id="rc14-intent-bound-trial-integration--2026-10-23"></a>
**RC14 intent-bound trial integration — 2026-10-23.** See [HISTORY.md](HISTORY.md#rc14-intent-bound-trial-integration--2026-10-23).

<a id="rc15-permanent-lifecycle-implementation--2026-10-23"></a>
**RC15 permanent lifecycle implementation — 2026-10-23.** See [HISTORY.md](HISTORY.md#rc15-permanent-lifecycle-implementation--2026-10-23).

<a id="rc18-homebrew-normal-startup-gate-2026-10-23"></a>
**RC18: Homebrew normal-startup gate (2026-10-23).** See [HISTORY.md](HISTORY.md#rc18-homebrew-normal-startup-gate-2026-10-23).

<a id="shutdown-lifecycle-correction-local-validation-2026-10-23"></a>
**Shutdown lifecycle correction (local validation, 2026-10-23).** See [HISTORY.md](HISTORY.md#shutdown-lifecycle-correction-local-validation-2026-10-23).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="root-edition-status-and-evidence"></a>
