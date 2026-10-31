# Update Root Edition

> Unpublished 1.5.3 candidate: see the [release scope and pending acceptance](../docs/RELEASE-1.5.3.md). Published stable is 1.5.2; historical acceptance retains its original scope.

**Historical 1.3.0 supervisor → published 1.4.0 boundary:** that immutable
release has an incompatible destination inventory. An aborted pre-replacement
attempt installed nothing. Keep the journal and private pins unchanged. The
[guarded #115 compatibility and replacement preparation](../docs/development/ROOT-OTA-13-COMPATIBILITY.md)
was delivered in 1.5.0. Use the supported installer/recovery flow after reviewing
retained state; do not force the old supervisor to accept incompatible paths.
New 1.5.3 artifacts still require affected signed update/rollback acceptance.

Root updates use an independent **System Updater supervisor** for signed complete
edition sets: Root Home, Root Updater and compatible recovery infrastructure.
Third-party apps, TV firmware and No-root packages are outside that set.
Historical [1.4.0 acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md) includes manual physical
whole-product rollback on the C3; it does not validate automatic signed rollback.

## Computer-assisted bootstrap

Existing root SSH, Homebrew services, TV Node.js 8+ and suitable Python 3.9+ are
required. Supplying Python does not supply root, Node.js or compatible webOS APIs.
Unrooted TVs use computer updates. A legacy Home-only OTA cannot install the new
supervisor or managed-runtime infrastructure.

For a fresh setup, install the complete matching Root edition with LG Home selected. The cytv
installation prepares Root Updater before enabling Home. Preparing the independent
System Updater is a separate explicit action from a trusted computer:

```sh
cytv enable-system-updates --edition root
```

Use the saved TV connection, or supply `--host` and the existing root credentials.
For an existing Root installation with a retained Root Updater, first inspect its
status, transaction and matching recovery flow. Generic cytv reinstallation is
deliberately refused while that updater remains; these fresh-setup commands do
not provide a migration shortcut. Follow the [existing-TV checkpoint](../docs/UPDATES.md#one-time-computer-preparation)
and review the infrastructure transition before replacing anything. A standalone launcher update does not install the supervisor.
For the No-root edition on an already rooted TV, use the manual supervisor
command below with `--edition no-root` and an existing root SSH alias. The cytv
No-root connection logs in as `prisoner`; changing its port does not grant root.
Developer Mode access alone is insufficient. This captures the actual
installed baseline and provisions the supervisor. Existing supervisor state,
conflicting legacy transactions, uncertain package outcomes and unsupported
infrastructure stop setup; retain their evidence rather than deleting it.

When suitable TV Python is missing, this setup can provision the separate pinned
ARMv7 runtime over SSH on an eligible TV. Working system interpreters skip it.
See [Python delivery and limits](../docs/OPTIONAL-PYTHON.md), including cache
preparation with `cytv --prepare-python-runtime`. Maintenance commands never
download another interpreter.

For manual source setup, use the [shared Root installation and bootstrap
procedure](../docs/MANUAL_INSTALL.md#7-root-first-installation-checks-and-persistent-activation).
Keep complete matching bundles. Submission is detached: preserve the original
operation UUID and repeat only status until `state: complete` **and** `current: true`.
Pending, recovery-required, conflicts or unknown outcomes stop supervisor setup
and Home activation. Do not run both shared installation entry points or create
a new operation ID to escape a pending request. `--component-only` is advanced
component recovery, not normal setup or legacy migration.

The manual supervisor command defaults to `/usr/bin/python3`; `--python` accepts
only approved system/managed paths. Use the retained verified binding when needed;
manual commands never download Python. Omit `--apply` for a read-only setup plan.
Use strict OpenSSH host checking and a preconfigured authenticated alias.

For a known interrupted standalone supervisor bootstrap, `system-updater/setup.py
--resume` explicitly uses the retained baseline and exact package evidence, for
either edition. Keep the same bundle and edition; an unknown submitted outcome
is refused. This is recovery, not a retry that submits packages blindly.

The supervisor's private state is `/var/lib/clean-your-tv-system-updater`; its
normal-boot worker uses `52-clean-your-tv-system-updater`. Root Updater retains
its independent recovery role and interpreter binding. Never replace private
code, cached baselines or state files to bypass a setup failure.

If Root immediately shows `Denied methods call status` after supervisor bootstrap, close and reopen **Home Root** once to restart the GUI, then check Software updates again. If it persists, retain diagnostics and recovery state.

## Update on the TV

Open **Home → Settings → Software updates**, review the offered release and
confirm installation. The supervisor verifies the complete signed set, compatible
contracts and all cached rollback components before replacing anything. It
preserves the profile and suspends Home routing while installation is in progress.
Keep the TV powered on.

Startup health and profile readiness are confirmed automatically. Previously
enabled Home control resumes only through guarded activation when its saved
preference and recovery state still permit it. Explicit/emergency off, failsafe,
a changed boot or uncertain activation keeps it off. There is no Keep countdown.
An update does not grant permission to enable a previously disabled preference.

Downgrades, incomplete sets, conflicting installers, missing rollback material
and unknown install outcomes are refused. A successful installer run does not
validate remote buttons, cold boot, firmware APIs or recovery on another model.

## Failure and recovery

Open the separate **Root Updater** application if Home cannot open, or use
**Software updates → Recovery**. The supervisor owns the transaction and its
complete rollback set. Confirming rollback restores the saved components and
pre-update profile; later settings changes can be lost. Availability depends on
verified retained transaction evidence. Do not substitute an app-only old IPK.

Run `cytv status` after an interruption. Unknown package outcomes remain blocked;
installed-version readback or an idle installer does not reconstruct a missing
terminal receipt. Automatic recovery is bounded; an uncertain activation is not
replayed. Preserve journals, baselines and interpreter slots for investigation.
Use `cytv doctor --report` for issue-ready diagnostics and `cytv restore` to
request routing recovery. These commands do not provision a missing runtime.
For removal, use cytv's verified uninstall flow; an ambiguous removal is not
submitted twice automatically. See [CLI recovery](../docs/CLI.md#interrupted-operations).

## Release preparation and validation

Use the [release flow](../docs/RELEASE-FLOW.md),
[1.5.3 candidate scope and remaining acceptance](../docs/RELEASE-1.5.3.md) and
[published 1.5.2 notes](../docs/RELEASE-1.5.2.md). The
[1.4.0 acceptance record](../docs/RELEASE-1.4.0-ACCEPTANCE.md) remains bound to its
original artifacts; it does not accept a new candidate.
QEMU, package installation and host tests cannot establish TV compatibility.

<a id="candidate-firmware-configuration-api-permission"></a>
## Firmware configuration API permission

Firmware configuration access has a separate grant and lifecycle; it never
toggles the saved blocking preference. For repair and revocation, see
[firmware access](../docs/LG-FIRMWARE-UPDATES.md#candidate-root-home-configuration-api-access-110).

## Candidate: Homebrew setup is separate from updates

[Homebrew Installer](../homebrew/README.md) remains unreleased. It installs the
product through the shared coordinator; Homebrew updates the Installer client
only. Removing Installer leaves Root and recovery installed. Retained private
code requires checked delivery, not an Installer-only update.
See [private runtime authority and hardware gates](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#cold-boot-data-authority-correction).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="root-software-updates-and-recovery"></a>
