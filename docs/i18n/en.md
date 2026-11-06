# Clean Your TV — user guide

Clean Your TV gives your LG webOS TV a personal Home screen: your apps in your order, without sponsored rows in this menu. Install from a computer or Android phone; the computer can be switched off afterward.

## 1. Download the installer

Click the picture for your device. The buttons download the latest published release. For a Mac, choose Apple Silicon (M1 or newer) or Intel; check Apple menu → About This Mac.

[![Download — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Download — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Download — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Download — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Download — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="choose-an-edition"></a>

<a id="before-installation"></a>

## 2. Choose an edition

Turn on the TV and connect it and your computer or phone to the same home network. Allow CYTV Local Network access when asked.

- **No-root** — if you do not have root access. Set up Developer Mode below.
- **Root** — if you already have root SSH access. The installer does not root the TV. Do not enable Developer Mode on that TV; keep SSH access and recovery data.

### Developer Mode setup (No-root)

Developer Mode lets CYTV install apps on a TV without root.

1. On the TV, open LG Apps, search for Developer Mode and install it.
2. Open Developer Mode and sign in with your LG Developer account. Create an account at [LG Developer](https://webostv.developer.lge.com) if needed.
3. Turn on Dev Mode Status. The TV restarts. Open Developer Mode again.
4. Turn on Key Server and leave Developer Mode open. Its IP Address is the TV address to enter in CYTV.
5. Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters.

Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.

Pairing is a separate step: when the TV asks, approve CYTV with your remote.

Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.

<a id="install-and-select-a-language"></a>

## 3. Open the installer

- **Windows x64:** Download `cytv-windows-x64-desktop.zip`, choose **Extract All** in File Explorer, then open `cytv-desktop/cytv-desktop.exe`. Keep the `_internal` folder beside it.
- **macOS 13+:** extract `cytv-macos-arm64.zip` (Apple Silicon) or `cytv-macos-x64.zip` (Intel), move `cytv.app` into Applications and open it. Allow Local Network access. If blocked, use Privacy & Security → Open Anyway only for a trusted project download; do not disable Gatekeeper.
- **Linux x64:** on Ubuntu 22.04+, Debian 12+ or Mint 21+, open `cytv-linux-x64.deb` in the graphical package installer, install, then open Clean Your TV from the applications menu. Desktop libraries may require Internet access. Linux ARM is not included.

**Android ARM64:** use a 64-bit ARM phone with Android 7+ and WebView/Chrome 108+. Open the downloaded APK and allow installation from that source if Android asks. Open CYTV; choose the language at the top right. Update without uninstalling or clearing data.

The desktop wizard selects your system language automatically; its language selector saves an explicit choice. On the TV, open **Settings → Language** and select a language, or the system/automatic option to follow the TV language. Installer and TV preferences are separate. The supported codes are listed in the [language index](../LANGUAGES.md).

## 4. Install on your TV

1. In CYTV, choose **Set up my TV**. On a computer, select a discovered TV; on Android, enter its IP address. If discovery finds nothing, enter the address manually.
2. Choose **No-root** or **Root** and check the selected TV before continuing.
3. For No-root, enter the code from Developer Mode and approve the TV prompt. For Root, use your existing SSH credentials; approve a new SSH identity only for your own TV on a trusted network. If a saved key has changed, stop and investigate.
4. Follow the wizard. Keep the TV on, stay on the same network and leave CYTV open until it finishes. Do not force-stop the Android app. Root activates Home control immediately after preparing recovery.

## 5. Check your remote

1. Open another TV app and briefly press **Home**. Clean Your TV should open. Tell the wizard what you saw; leave the check skipped if you did not test it.
2. Check arrows, OK, Back, volume and sound. Test standby/wake and a start after disconnecting power separately. A successful installation alone does not check these actions.

<a id="everyday-use-and-recovery"></a>

## 6. Everyday use and recovery

Arrows select tiles; OK opens them; hold OK to reorder. Short Back retains the app's navigation and exit confirmation. Short Home opens Clean Your TV while Home control is active. Hold Back for 1.2 seconds to open LG Home once. The Home-control switch and your settings remain unchanged.

**Press Home three times within two seconds**, releasing between presses, to return to LG Home and stop Home control. This preserves preferences.

No-root: To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept. Root: turn **Change Home** on in Home settings to resume. **Open LG Home** opens LG Home once without changing routing. To restore LG Home as the persistent destination, turn **Change Home** off. Do not run both controllers together. If a failure repeats, leave LG Home active.

## Need help?

If installation was interrupted, use the same saved connection and choose **Check TV status** first. Continue only through the recovery action offered by the wizard. If the state is unknown, save the diagnostic report and stop; keep recovery data and do not blindly repeat installation.

During recovery, keep Home control off and retain the original diagnostic reports and saved connection. Confirm inspection and changes separately. Follow the detailed recovery guide for your installed version; do not force reinstallation or clear recovery state.

For help, include TV model, firmware, No-root or Root, installer device, failed step and error message. Remove passwords, keys, addresses and personal data before sharing a report. Reports are not published automatically.

[Report a problem](../FEEDBACK.md) · [Detailed recovery](../RECOVERY.md) · [Update or remove](../MAINTENANCE.md) · [Other languages](../LANGUAGES.md)

In upcoming builds, the warning and **Disable HDMI previews** action appear only for themes with input previews enabled when 4K is selected or active. During HDMI previews, the 4K video wallpaper temporarily switches to a static 1080p image. Disable input previews to keep the wallpaper in 4K.

### Candidate: recovery and full removal

The download buttons above remain the published release. The next candidate adds guided original-operation continuation and **Uninstall Clean Your TV** on desktop and Android. Use the same saved TV connection; approve inspection and each change separately. You may finish eligible Root setup with LG Home and Home control off. That achieves the selected goal; physical Home, sound, standby and cold boot remain separate checks.

Removal keeps the earlier installation result and reports success only after checking that owned apps, services, startup and private setup data are removed. Pending work, unknown vendor results, ownership conflicts or unavailable checks can block it; removal is not guaranteed on every failed setup. Keep the existing report and recovery data. Do not reinstall, clear app data, reset Developer Mode or force deletion to bypass a blocker. A future observer cannot reconstruct legacy results. Emergency controls above still apply; reports require your approval before sharing.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="optional-python-for-root-in-v110"></a>
<a id="lg-firmware-blocking-in-120"></a>
<a id="new-in-130-guided-desktop-recovery"></a>
<a id="new-in-130--12"></a>
<a id="unreleased-candidate-root-setup-through-homebrew"></a>
<a id="unreleased-candidate-hdmi-sound-recovery-root"></a>
<a id="themes-154"></a>
<a id="settings-categories-unpublished-candidate"></a>
<a id="automatic-graphics-resolution-candidate"></a>
<a id="updates-and-removal"></a>
<a id="help-and-further-reading"></a>
<a id="themes"></a>
<a id="settings-categories-154"></a>
<a id="automatic-graphics-resolution-160"></a>
<a id="storage-space"></a>

[Requirements](../COMPATIBILITY.md) · [Remote controls](../CONTROLS.md) · [Themes](../THEMES.md) · [Updates](../UPDATES.md).
