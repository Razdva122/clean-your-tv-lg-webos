# Root Edition

> Release 1.6.0 uses Root/infrastructure 0.7.0 and Root Updater 0.4.0. See [Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases) for published downloads, [release scope](../docs/RELEASE-1.6.0.md) and [artifact-bound acceptance](../docs/history/2026-11-02-release-1.6.0-final-acceptance.md).

Use Clean Your TV as the system Home on an **already rooted LG webOS TV**.
Short Home opens Clean; confirmed Back exit returns through native Home routing.
After setup, no computer, USB drive or router script is needed for normal use.

[Install](../docs/INSTALL.md) · [Activate and control](ROLLOUT.md) ·
[Recover](RECOVERY.md) · [Update](UPDATES.md) · [Known limits](STATUS.md)

## Install and activate

1. Keep working root SSH access and recovery backups. Root needs Homebrew
   services, TV Node.js 8+, Python 3.9+ and supported ARM32 Magic Remote input.
   Eligible TVs can use the installer's [private Python runtime](../docs/OPTIONAL-PYTHON.md).
   Installation does not obtain root, flash firmware or configure Developer Mode.
2. Use the [desktop installer](../docs/INSTALL.md) or [Android installer](../android/README.md).
   Normal cytv setup installs Root Home and Root Updater, verifies recovery,
   stops Home Helper, enables Home control and opens Clean. There is no trial
   countdown or Keep confirmation. Activation checks input, guardian and routing.
3. Check arrows/OK, short Home and Back on the TV. If activation was interrupted,
   inspect status and use **Finish Root setup** only when offered; do not reinstall blindly.

For [manual source setup](../docs/MANUAL_INSTALL.md), bundle provisioning leaves
Home control off. After verified completion, stop Home Helper and enable
**Home Root → Home settings → Change Home**. Never run both editions' input
handling together.

## Candidate native startup choices

The unpublished candidate adds **Home settings → Open Clean Your TV first**.
**LG Channels / Live TV** is on by default; **YouTube** and **HDMI** are off.
Enable a source to prepare Clean as the native first screen after that source.
Turning **Change Home** off visibly disables these controls and explains why;
your choices are retained. The candidate removes late boot/wake app launches.
Exact-package standby/cold-start, source selection and control acceptance remain
pending; this does not change the published 1.6.0 evidence below.

## Exit or recover

Press **Home three times within two seconds**, releasing between presses, to
restore LG Home and disable Root intent independently of the web interface.
**Change Home off** also restores LG routing. **Open LG Home** visits LG Home
once while preserving the routing preference. Long Home can invoke LG features;
it is not the Root emergency gesture.

Candidate cytv 0.7.0 offers `cytv recover` with the same saved connection for an
interrupted operation. Inspection and changes have separate default-No prompts;
Root inspection may stage verified support code and is not fully passive.
Keep journals, backups and referenced Python slots. Do not blindly retry,
restore or remove packages; review the [recovery rules](../docs/RECOVERY.md).

## Current release and limits

Release **1.6.0** uses **Root/infrastructure 0.7.0 / Root Updater 0.4.0 /
System 1.2.0**. Existing System 1.1.2 stays pinned with its old channels; no
general replacement path is provided. [Exact-package C3 QA](../docs/history/2026-11-02-release-1.6.0-final-acceptance.md)
covers signed update/active retained rollback, controls/audio, emergency and
independent fault recovery, cold startup and genuine failsafe in its recorded
scope. Physical fresh System 1.2.0 is untested. Earlier standby failure
[#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171) and
forward-update cancellation #202 remain unresolved. The owner accepted the
documented initial-Channels/delayed-Clean standby limitation for 1.6.0; no
immediate-first-screen guarantee or universal compatibility is claimed.

The historical **1.4.0 / Root 0.5.0 / Root Updater 0.3.1**
[C3 acceptance record](../docs/RELEASE-1.4.0-ACCEPTANCE.md) covers corrected startup,
standby, off/emergency preservation and manual whole-product rollback on
OLED55C3RLA / firmware 43.21.71 / SDK 11.2.0. Clean may appear after Live TV;
there is no immediate-first-screen guarantee. Other models and automatic signed
System Updater rollback are not established by these tests.

**Updating from the original 1.3.0 supervisor:** published 1.4.0 is incompatible
with that supervisor's destination inventory. Preserve aborted-operation evidence
and private pins; follow [update status and #115](UPDATES.md).

LG firmware blocking needs a real TV restart and can also block security updates;
the saved switch does not prove active blocking. Homebrew retains the preference
after CYTV removal. See [firmware controls and access](../docs/LG-FIRMWARE-UPDATES.md).
HDMI sound recovery is experimental; automatic boot/wake recovery is **off by default**.
See [audio behavior and acceptance](../docs/development/ROOT-AUDIO-RECOVERY.md).
Early boot artwork, system-library patches and system ad removal are outside this edition.

## Homebrew Installer: unreleased

The separate on-TV **CYTV Installer** has no published catalog listing or promotion
record. It requires existing compatible root and explicit runtime preparation/review.
Updating or removing Installer affects that client; product updates, complete
removal and recovery retain their separate ownership. It does not replace retained
private runtime code just by updating the client.
See [Homebrew status](../homebrew/README.md) and its
[pending hardware gates](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md).

## Technical references and history

[Runtime contract](runtime/README.md) · [Source bundle](package/README.md) ·
[Doctor](DOCTOR.md) · [Startup diagnostics](DEVELOPMENT.md#recovery-startup-diagnostics-130-issue-55) ·
[Current status and historical evidence](STATUS.md).
Historical acceptance is model-, build- and scenario-specific.

<a id="candidate-two-setup-clients-one-installation"></a>
The former setup-client notes are summarized under [Homebrew Installer](#homebrew-installer-unreleased).
<a id="what-works-on-the-tested-setup"></a>
See [historical C3 acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md) and
[current release limits](../docs/RELEASE-1.6.0.md).
<a id="requirements-and-limits"></a>
See [installation prerequisites](#install-and-activate) and [current limits](#current-release-and-limits).
<a id="recovery-startup-diagnostics-130-issue-55"></a>
See [developer startup diagnostics](DEVELOPMENT.md#recovery-startup-diagnostics-130-issue-55).
<a id="unreleased-hdmi-sound-recovery"></a>
See [HDMI sound recovery](../docs/development/ROOT-AUDIO-RECOVERY.md).
