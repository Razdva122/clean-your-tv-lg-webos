# Clean Your TV — user guide

Unreleased (#290): **+ / Add app** offers Live TV under the TV’s own name only when the tuner is detected as installed. Other hidden system apps stay excluded. No-root needs the updated Helper and installer; Root needs the updated Home package. Tuner launch still needs TV verification.

**1.7.0 — Root startup sources:** In Settings → Your Home screen, turn on **Change Home** to edit **Open Clean Your TV first**. **LG Channels / Live TV** is on by default; **YouTube** is off. When Change Home is off, the two switches remain visible but unavailable, and their saved values are retained. Preferences are stored privately on this TV; portable profile export does not include them. This control is not a claim of verified TV startup or wake behavior. A source switched off leaves the startup decision to the TV firmware; it does not guarantee resuming that source. There is no HDMI startup switch. [Native startup limits (English)](../../root-edition/README.md#candidate-native-startup-choices).

> This guide describes 1.7.0. For available packages, use [published GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). It includes all five installer improvements and refreshes Root Settings from actual status after reopening; a failed check does not enable Home. System Updater 1.2.0 is for new eligible setup or verified replacement of 1.1.0/1.1.1. Existing 1.1.2 stays pinned with its old channels; no general migration is provided. Keep recovery data and do not force replacement. [Versions and limits](../RELEASE-1.7.0.md).

> v1.5.0: themes, Showcase and PC-to-TV transfer. Known Root limits: Appearance can shift 110 px; automatic Home after standby can fail. Device-specific acceptance remains limited. [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** fixed-layout themes keep the empty Columns row to preserve Appearance scroll position during Apply. Hidden Columns is skipped by pointer, keyboard and accessibility navigation.

[Documentation](../README.md) · [Report a problem](../FEEDBACK.md)

**Historical 1.5.4 evidence:** C3 acceptance covers the recorded power, Home, focus, off-state and manual rollback tests. Other TVs, eARC audio and physical Android devices remain unverified; installation alone does not prove compatibility. [Tested scope (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

**1.5.4:** TV checks show each requirement as not checked, checking, passed, failed or unverifiable in the console, desktop and Android interfaces. Results remain visible after an error. A failed Node.js/Python check concerns the TV runtime; `doctor` does not prepare Python or request control pairing. Save the report before retrying.

## Choose an edition

No-root and Root are equal options for different TV setups. Choose No-root for LG Developer Mode or Root for existing root SSH access. Compatibility and test coverage remain specific to each edition.

- **No-root:** enable LG Developer Mode and Key Server. Enter the passphrase displayed on the TV and accept the separate TV pairing request. Developer Mode must remain active; expiry can remove sideloaded apps. Monitor its official timer even with Beta renewal enabled. Helper monitoring needs local networking.
- **Root:** existing root SSH access is required. The installer does not root the TV. Do not enable Developer Mode on an existing rooted setup. Keep root access and recovery services available.

Root requires working Settings Service and System Profile Home interfaces (`com.webos.service.systemprofile`); existing root access alone does not establish compatibility.

> **1.6.0:** Root setup checks the required Home interfaces before preparing private Python or packages. A failed check stops setup; passing it does not prove firmware compatibility or physical Home operation. Known connection errors now show specific advice. Keep saved profiles, trust and recovery data; unresolved operations require verified recovery, not a blind retry. Save and review the diagnostic report. [Details](../development/INSTALLER-PREFLIGHT-HELP.md).

## Before installation

Keep the TV on and the computer on the same trusted local network. No always-on computer is needed afterward. Compatibility depends on model, firmware and remote; Root has outstanding hardware checks.

1.5.4 includes Home Helper **0.6.21** with TV Node.js **0.10.25+** support; Root still requires Node.js **8+**. [Compatibility](../COMPATIBILITY.md).

**Unreleased webOS 1.x follow-up:** the next No-root installer accepts TV Node.js **0.10.15+** after exact-runtime Helper checks; published 1.7.1 installers still require **0.10.25+**. This does not establish old WebKit/native-input/Home compatibility. Do not replace the TV runtime or bypass its checks. Root still needs Node.js 8+. [Evidence and limits](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased).

No-root Helper needs TV Node.js **0.10.25+**. Root needs Node.js **8+** and working Python **3.9+**. Setup can download a verified private Python if needed; initial staging needs **320 MiB** free. It does not replace system Python. Keep runtime slots used by recovery. [Optional Python (English)](../OPTIONAL-PYTHON.md). Developer Mode auto-renewal is **Beta, off by default**, and real renewal on unrooted TVs is not confirmed; keep checking the official timer.

### Developer Mode setup (No-root)

Developer Mode lets CYTV install apps on a TV without root.

1. On the TV, open LG Apps, search for Developer Mode and install it.
2. Open Developer Mode and sign in with your LG Developer account. Create an account at webostv.developer.lge.com if needed.
3. Turn on Dev Mode Status. The TV restarts. Open Developer Mode again.
4. Turn on Key Server and leave Developer Mode open. Its IP Address is the TV address to enter in CYTV.
5. Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters.

Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.

Pairing is a separate step: when the TV asks, approve CYTV with your remote.

Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.

## Install and select a language

- **Windows x64:** Download `cytv-windows-x64-desktop.zip`, choose **Extract All** in File Explorer, then open `cytv-desktop/cytv-desktop.exe`. Keep the `_internal` folder beside it. Windows publisher signing is not configured. The separate console is `cytv-windows-x64.exe`; rename it to `cytv.exe` and use `.\cytv.exe` in PowerShell for the commands below.
- **macOS 13+:** extract `cytv-macos-arm64.zip` (Apple Silicon) or `cytv-macos-x64.zip` (Intel), move `cytv.app` into Applications and open it. Allow Local Network access. If blocked, use Privacy & Security → Open Anyway only for a trusted project download; do not disable Gatekeeper. Older-system acceptance is not established.
- **Linux x64:** on Ubuntu 22.04+, Debian 12+ or Mint 21+, open `cytv-linux-x64.deb` in the graphical package installer, install, then open Clean Your TV from the applications menu. Desktop libraries may require Internet access. Linux ARM is not included. The standalone `cytv-linux-x64` executable is the CLI; use the `.deb` for the graphical app.

[Android installer (English)](../../android/README.md): choose the language at the top right. Update without uninstalling or clearing data. Android 7 / WebView 108 is the minimum, not a verified phone configuration; acceptance used Android 15 ARM64 / WebView 124 in an emulator. Physical phones and live phone-to-TV recovery remain unverified.

**Unreleased Android candidate:** for an original Root `install / coordinator-submitted` operation, Review recovery options can perform an explicitly confirmed read-only inspection using the original saved profile and SSH pin. Do not uninstall/clear app data, replace the profile or repeat installation. Use only the signed rebuilt APK named in the maintainer handoff; the public APK does not include this path. [Procedure and limits](../../android/README.md#interrupted-root-installation-inspection-unreleased).

The desktop wizard selects your system language automatically; its language selector saves an explicit choice. On the TV, open **Settings → Language** and select a language, or the system/automatic option to follow the TV language. Installer and TV preferences are separate. The supported codes are listed in the [language index](../LANGUAGES.md).

For a separately downloaded CLI on macOS/Linux, open a terminal in its extracted directory:

```sh
chmod +x cytv
./cytv --language en install
```

Choose the TV (or enter its IP), choose the edition and review the summary. Approve first-use SSH trust only for your own TV on a trusted network; a changed saved key blocks access. Root credentials are distinct from the Developer Mode passphrase. Root installs recovery and activates Home immediately, without a trial or Keep step. Check arrows, OK, Home, Back/Cancel, volume, standby/wake and cold boot on your own TV.

**1.6.0:** setup shows package verification, startup readback and your physical Home observation separately. A launch acknowledgement or observed Helper process does not prove Home interception. Open another TV app, press Home once briefly, then choose what you saw; the default is **Not tested / skip**. `--yes` does not answer this check, and noninteractive setup leaves it untested. A failed or skipped Home check does not undo installed packages or start a reinstall. Save the local report for help; it is not published automatically. Other controls, sound, standby and cold boot remain separate checks.

## Everyday use and recovery

Arrows select tiles; OK opens them; hold OK to reorder. Short Back retains the app's navigation and exit confirmation. Short Home opens Clean Your TV while Home control is active. Hold Back for 1.2 seconds to open LG Home once. The Home-control switch and your settings remain unchanged.

**Press Home three times within two seconds**, releasing between presses, to return to LG Home and stop Home control. This preserves preferences. Older No-root Helper versions through 0.6.13 instead use holding Home for about two seconds; holding Home is not the Root emergency gesture.

No-root: To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept. Root: turn **Change Home** on in Home settings to resume. **Open LG Home** opens LG Home once without changing routing. To restore LG Home as the persistent destination, turn **Change Home** off or run `cytv restore`. Do not run both controllers together. If a failure repeats, leave LG Home active.

> **1.5.4 — Root:** explicitly enabling **Change Home** while Root is healthy creates CYTV's native **Clean** input and sets the remembered input to Clean. Disabling Home control, emergency stop, a fault, update suspension or uninstall removes CYTV's entry and restores the previous remembered input only if CYTV's value is still current; unrelated inputs and foreground apps are preserved. Unsupported TVs or entries CYTV does not own use ordinary guarded Home routing. There is no immediate-first-screen guarantee. The recorded C3 first-screen, standby and AC-off cold-boot checks passed; this is not universal compatibility. Home can remain disabled after update/rollback (#202), and Settings can show stale status (#206): close/reopen Settings, then explicitly enable Change Home and wait for Clean status. [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language en status
./cytv --language en doctor --report
./cytv --language en restore
./cytv --language en uninstall
```

> **1.6.0 (#152):** the No-root Restore/removal flow can use a guarded SSH stop if Helper disable is rejected. Stop state is retained; uncertain recovery keeps the journal. Do not delete state files. EF950V device confirmation is pending. [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** No-root status retains an interrupted install/removal journal. Matching files or absent apps do not prove installer completion. If verification is denied, stop and retain diagnostics; there is no file-only bypass. [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

After interruption, run `status` before retrying; retain journals and recovery files. `restore` returns LG Home without removing apps. `uninstall` restores before removal. Root recovery state is deliberately retained; never delete it to force reinstallation. Review diagnostic reports before sharing; do not publish keys or profile folders.

Open **Home settings → Appearance → Columns** and choose 1–8 columns, or **By theme** to use the theme’s value (Classic defaults to 5). An explicit number takes priority over the theme. Themes with a fixed layout hide the Columns option and use the author’s value. Your saved choice returns when you switch to a theme that supports this setting. In downloaded Alpine, apps form one looping horizontal ribbon: Left/Right scrolls and wraps, Up opens shortcuts, and Down returns to the same app. In Alpine, the mouse wheel or touchpad also scrolls the ribbon; it does not move Home behind an open dialog.

1.5.4: in **Home settings → Appearance**, turn off **Show Add app tile** to hide the + tile. It is on by default. Use **Add app** in the same section to add or restore apps while + is hidden. Ordering and hiding remain available; the choice survives restart. If every app is hidden, the top controls and Settings remain available.

1.7.0: the selected theme chooses the header **Inputs** menu or an HDMI shelf; there is no global placement or **Show inputs on Home** switch. The shelf currently supports only `dock-grid`. Liquid Glass selects it; Classic and themes without this option keep the header menu. On the shelf, Up from the dock enters the shelf, Up again reaches the header, Down or Back returns to the dock, and OK launches the source. When source tiles exist, the shelf replaces the header Inputs menu. A device name comes from firmware-provided input metadata only if the firmware supplies it; otherwise a connected source shows **Connected**. Home does not invent a PlayStation name or guarantee CEC identification. Empty ports remain selectable. Previews are **on by default**; an explicitly saved Off stays off. Turn off **Home settings → Appearance → Preview inputs on focus** to disable them. While enabled, a connected HDMI source can preview after about 0.8 seconds of focus, only while the selected theme has a shelf. HDMI previews may play sound or switch HDR on some TVs; silence is not guaranteed. Home does not automatically change global TV mute or HDR settings. Live TV and empty ports keep static tiles. Root reads input status through its own service. No-root keeps direct EIM where allowed; a permission refusal uses a read-only request through the paired Helper. Failed reads leave status unknown; no new control or pairing prompt is added.

In 1.5.4 theme previews with the optional sidebar layout, Up/Down selects a menu item, Right enters the apps, and Left from the first visible app column returns to the menu.

No-root 1.5.0: Helper can recover a transient watchdog timeout after standby, with at most five attempts in ten minutes. Stop and triple Home still require an explicit Start Helper; repeated failures stay stopped. TV acceptance is pending. [Behavior and limits (English)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Updates and removal

Keep known-working packages and private settings backups. For computer-assisted No-root package replacement, stop Helper first and update without uninstalling, which may erase settings. Removing the desktop app does not remove TV apps. Do not replace a live Root runtime with a standalone IPK; use cytv's explicit recovery/reinstallation flow.

Open Home settings → Software updates and review the offered versions before confirming. On-TV updates/rollback require **root, Homebrew Channel** and prepared matching updater infrastructure, even for the No-root edition. An unrooted TV uses the computer installer. Full-system preparation is a separate explicit action; follow [updates (English)](../UPDATES.md). Check Recovery for the saved rollback version; later settings may be lost during rollback.

The Home settings transport correction shipped in 1.5.0. Update Home and Helper together with a matching published installer; a Home-only update omits the Helper change. Model-specific acceptance remains limited. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

**Existing 1.3.0:** its original System Updater can refuse changed infrastructure. Preserve an aborted operation and follow the checked recovery/replacement preparation documented for 1.5.0+; do not clear journals or retry blindly. An app-only update does not replace pinned Root infrastructure. [Migration and recovery (English)](../UPDATES.md#one-time-computer-preparation).

Root HDMI sound recovery is experimental and **off by default**; opt in only if needed. It can interrupt healthy audio and does not establish eARC compatibility. [Sound recovery (English)](../development/ROOT-AUDIO-RECOVERY.md). The separate Homebrew **CYTV Installer remains unreleased**; use the published computer/Android installer.

Homebrew Channel denied access to this installer. On webOS 11, Homebrew 0.7.3 needs an upstream compatibility update. Use the published computer or Android installer until a supported Homebrew release includes the fix. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: if firmware API access is refused because an old Root package retained writable directories, the explicit command `cytv enable-firmware-access --edition root --repair-package-permissions` verifies the current private package before removing write access for group/others from Root-owned paths. Unknown or changed files stop repair. It preserves your profile, Home choice and firmware-blocking preference; see [repair details](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` handles a verified Root rollback whose package installers completed but launcher readiness timed out. It requires genuine launcher health, refuses unknown installer outcomes, and preserves packages, pinned code/keys, failure evidence and an explicit Home-off choice. A private audit records the bounded attempt. Ordinary retries never extend the same attempt. Only after its 120-second deadline expires, with no accepted health or unknown installer result, add `--new-recovery-attempt` to archive the full prior audit under its UUID/hash and explicitly open a fresh attempt. Completed recovery stays idempotent; there are no automatic repeated attempts. [Procedure and limits](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.6.0: System Updater 1.2.0 is for eligible new setup or verified replacement of 1.1.0/1.1.1 using `cytv replace-system-updater --edition root`. Only System Updater is replaced; Root/Root Updater apps, the full profile and Home choice are preserved, and old state is archived. Unknown or unfinished operations stop replacement. Existing 1.1.2 stays pinned with its old channels; there is no general migration and replacement must not be forced. This does not gate No-root feeds. [Replacement procedure](../RECOVERY.md#replace-the-root-system-updater-candidate)

## Help and further reading

**1.6.0:** choose **Review recovery options** for the same saved TV, or run `cytv recover`. Checking and changes require separate confirmation, with No selected by default; `--yes` cannot approve them. Root continues only after its existing verification. No-root offers removal only when the existing package-service guard permits it; removal may reset Home preferences. New setup never starts automatically. If state is unknown or access is denied, save the report and stop; retain journals and do not repeat removal. This does not resolve the missing terminal evidence in #201 or establish device recovery in #216. [Recovery](../RECOVERY.md). For help, include model, firmware, edition, installer version, failed step and expected/actual behavior; review and redact the report before sharing.

1.7.0: recovery can resume a No-root removal stopped before its first package request without global package-status access, if the original journal proves that state. Confirm removal separately, then start setup separately after verified removal. Unknown/submitted operations still stop; keep the saved connection and journals. This is not in 1.6.0. [Details](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased).

[Documentation](../README.md) · [Report a problem](../FEEDBACK.md)

1.7.0 recovery guidance: if no package removal request was submitted, a failed removal offers **Review recovery options** for the same saved TV. Inspection and removal still need separate confirmation. A refused package-status check stops recovery and offers a report. Its `recovery` summary distinguishes an unstarted removal, inherited operation and interrupted package work without exposing the full journal; it cannot authorize recovery.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="optional-python-for-root-in-v110"></a>
<a id="lg-firmware-blocking-in-120"></a>
<a id="new-in-130-guided-desktop-recovery"></a>
<a id="new-in-130--12"></a>
<a id="unreleased-candidate-root-setup-through-homebrew"></a>
<a id="unreleased-candidate-hdmi-sound-recovery-root"></a>

<a id="themes-154"></a>

## Themes

1.7.0: **Settings → Themes**. **Classic**, **Liquid Glass**, **Ribbon** are included and work without downloading a theme; Classic remains the default. **Channel** is an external showcase theme. In showcase trials: Choose a theme, then **Keep theme** within **20 seconds**. **Revert**, Back or timeout restores the previous appearance. If Home closes during an unconfirmed preview, the next launch returns to Classic. Built-in and downloaded themes chosen in the installed list apply and save immediately, without a confirmation timer. Themes received from a computer or installed by URL also use this list. Only Try theme inside Theme showcase starts a 20-second trial.

1.7.0: **Classic**, **Liquid Glass** and **Ribbon** are built in. **Alpine 1.4.4** moves to the downloadable **Theme showcase**. A saved `builtin:alpine` selection falls back to Classic with the existing visible recovery notice; Home neither downloads Alpine automatically nor replaces it with Liquid Glass. Version 1.6.0 includes Classic, Alpine and Ribbon.

Installed themes appear in one horizontally scrollable row. The active theme is always first and has a highlighted card. Use Left/Right to browse the row.

Showcase lists only themes that are not installed on this TV. Classic, Liquid Glass, Ribbon and downloaded themes are hidden, including when a newer catalogue version exists. After removing a downloaded theme it appears again. Update a theme through Add by ID or Receive from computer.

Theme cards are embedded directly in Themes beside the settings categories. Showcase, link installation and computer transfer open within that pane; only a showcase trial temporarily reveals Home.

Opening Theme showcase or choosing Refresh checks the main project repository for reviewed catalogue updates without updating Home or reloading the page. After a normal merge, new entries become available; an unmerged candidate may still show the bundled fallback. Offline or failed requests use bundled previews and entries. Built-in themes match your installed Home version. Select a preview for details, then **Download theme** for Channel (internet required). After download, try it and choose **Keep theme** within **20 seconds**. Installed themes work offline. **Add by ID** remains available for pinned links.

To test an unpublished theme, first open **Settings → Themes → Receive from computer** on TV. Enter the TV address and six-digit PIN shown there into **Send to TV** in the computer preview, then send and choose **Apply theme** on TV. This primary direction uses an outgoing PC connection to TV TCP **8879**, without changing the computer firewall. Both devices must be on the same trusted home network. The receiver closes after one upload, cancellation, leaving the pane or **10 minutes**. PINs are not saved; the installed theme works offline. GitHub publication is not required.

For a published theme, open **Add by ID** and enter its ID (for example `102300a209`), `da.gd/102300a209`, or the full GitHub link. Home shows the expanded da.gd address before loading and then checks the GitHub destination and theme package. The author can provide the ID in the release notes or with **TV link → Copy ID** in the computer preview.

**1.6.0:** **Show diagnostics** in the Home Helper panel displays a small, filtered snapshot of its own status requests. Viewing it does not start Helper or change Home control. Share only that JSON when requested, after reviewing it; see [details](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

Themes shows previews of built-in themes and every theme you installed yourself, including offline. A separate Theme showcase button opens the published catalogue; personal installation does not publish a theme.

Appearance contains Columns (with the current count), Show Add app tile and Add app. Themes is a separate category with installed previews, Theme showcase, Receive from computer and Add by ID. Add by ID is on the right and accepts a theme ID such as 102300a209. Choose Classic to restore it; downloaded themes can be removed individually. The Language category offers language choices directly, without another dialog.

In the browser preview, Receive from computer explains the steps to perform on the TV; it does not start a TV receiver on the computer. Use Send to TV above the preview. Removing a downloaded theme asks for confirmation; removing the active theme restores Classic first. Cancel keeps the theme.

Parameterized ribbon themes in 1.5.4 can place the small Inputs, Wi-Fi and Settings buttons at the bottom left. When a theme enables this navigation, Left from the first visible app selects Settings, then Wi-Fi and Inputs; Right from Settings returns to the same visible edge. A theme that requires a newer Home capability is rejected during installation on an unsupported version, keeping the current appearance and selection. Update Home before retrying. Downgrading Home after selecting such a theme can instead trigger the existing recovery to Classic at startup.

<a id="settings-categories-unpublished-candidate"></a>

## Settings categories (1.5.4)

In both editions, Home settings has categories on the left and the selected settings on the right: Your Home screen, Appearance, Themes, Language, Software updates and Advanced. No-root also has Developer Mode; Root includes LG firmware updates under Software updates and HDMI sound under Advanced. Use Up/Down within a column, Right to enter its settings and Left to return to categories. Back returns to categories first, then closes settings; Tab also reaches Back to Home.

A yellow dot on both Software updates and its update button means an update is available. Both indicators clear after a successful check confirms no update; a failed check retains the last confirmed state.

<a id="automatic-graphics-resolution-candidate"></a>

## Automatic graphics resolution (1.6.0)

The 1.6.0 computer/Android installers and migrated OTA clients select 720p or 1080p from the TV’s reported capability. If it cannot be verified, the operation stops. Older independently installed updaters need the documented computer migration; recovery keeps its original packages.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** save the original failed-attempt report. New reports separate a recorded first error from later checks and include a filtered Doctor/status summary; successful setup/status/restore also offer an export. Missing older evidence remains unknown; this does not authorize recovery. [↗](../development/INSTALLER-DIAGNOSTICS.md).
