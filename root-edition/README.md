# Root Edition

> Unpublished 1.5.3 candidate: see the [release scope and pending acceptance](../docs/RELEASE-1.5.3.md). Published stable is 1.5.2; historical acceptance retains its original scope.

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

## Exit or recover

Press **Home three times within two seconds**, releasing between presses, to
restore LG Home and disable Root intent independently of the web interface.
**Change Home off** also restores LG routing. **Open LG Home** visits LG Home
once while preserving the routing preference. Long Home can invoke LG features;
it is not the Root emergency gesture.

After a failure, run `cytv status` before taking another action.
`cytv doctor --report` collects read-only diagnostics; `cytv restore` requests
routing recovery. Keep journals, backups and referenced Python slots. See
[recovery](RECOVERY.md) before retrying setup, removing packages or returning to No-root.

## Current release and limits

Published **1.5.2** uses **Root 0.6.1 / Root Updater 0.3.3**, with System
Updater 1.1.2. The unpublished **1.5.3** candidate selects **Root 0.6.2 / Root
Updater 0.3.4** and retains System Updater 1.1.2. Automatic Home presentation
after standby remains unresolved in [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171);
the candidate adds diagnostics, not a demonstrated standby fix. New packages
require their own affected acceptance.

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
[current release limits](../docs/RELEASE-1.5.3.md).
<a id="requirements-and-limits"></a>
See [installation prerequisites](#install-and-activate) and [current limits](#current-release-and-limits).
<a id="recovery-startup-diagnostics-130-issue-55"></a>
See [developer startup diagnostics](DEVELOPMENT.md#recovery-startup-diagnostics-130-issue-55).
<a id="unreleased-hdmi-sound-recovery"></a>
See [HDMI sound recovery](../docs/development/ROOT-AUDIO-RECOVERY.md).
