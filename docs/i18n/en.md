# Clean Your TV — user guide

The installer asks for a TV name, default **Home**; scripts can use `--tv-name "Aashiyaan"`. After upgrading an older installation, **Settings → Home → TV name** is available automatically. Save a new name or reset to Home at any time. A saved name survives restart and supported updates; existing settings remain intact. Names allow up to 48 characters. Settings saves the launcher name. To change LG’s startup screen, apply the same name through the installer. Home adds no second loading screen; the network name is unchanged.

Unreleased installer change: before a new installation, the computer installer checks for a newer stable installer on GitHub. Choose “Open GitHub and download the latest version” to stop and download it, or “No, install this version” to continue explicitly. If the check fails, you can continue. Pending operations and recovery skip the check.

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

For Root, the installer checks and selects an available Home control method. If compatibility cannot be verified, setup stops; do not bypass the failed check.

**No-root → Root:** If No-root was installed again after full removal, switching to Root may require cleanup first. Back up Home preferences, choose **Uninstall Clean Your TV** with the saved Root connection and wait for verified removal. This also removes No-root Home and Helper. Then install Root; keep recovery records.

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

Root setup continues with a warning if TV inputs cannot be read but the application list is valid. Inputs may be missing from Home; a failed or empty application list still stops setup. Save the diagnostic report if the warning persists.

## 5. Check your remote

1. Open another TV app and briefly press **Home**. Clean Your TV should open. Tell the wizard what you saw; leave the check skipped if you did not test it.
2. Check arrows, OK, Back, volume and sound. Test standby/wake and a start after disconnecting power separately. A successful installation alone does not check these actions.

<a id="everyday-use-and-recovery"></a>

## 6. Everyday use and recovery

No-root IR support: a short Home release schedules Clean after about 700 ms; LG Home may flash first. Held Home stays with webOS, and triple Home still stops Helper. Access on stock Developer Mode TVs remains unverified; do not change input permissions.

Arrows select tiles; OK opens them; hold OK to reorder. Short Back retains the app's navigation and exit confirmation. Short Home opens Clean Your TV while Home control is active. Hold Back for 1.2 seconds to open LG Home once. The Home-control switch and your settings remain unchanged.

**Press Home three times within two seconds**, releasing between presses, to return to LG Home and stop Home control. This preserves preferences.

No-root: To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept. Root: turn **Change Home** on in Home settings to resume. **Open LG Home** opens LG Home once without changing routing. To restore LG Home as the persistent destination, turn **Change Home** off. Do not run both controllers together. If a failure repeats, leave LG Home active.

An update does not restart a stopped No-root Helper. Resume it explicitly as described above; do not delete stop markers manually.

## Need help?

If `ssh-identity-changed` appears after a reset or SSH change, stop: CYTV blocked the changed saved key before sign-in. The first-use trust prompt cannot replace it, and a pending uninstall does not explain the mismatch. Keep the original saved profile, keys and recovery records. No supported automatic re-trust command is supplied. Independent TV identity/fingerprint verification and a reviewed procedure preserving the profile are needed: [changed SSH identity recovery](../RECOVERY.md#ssh-identity-changed).

If installation was interrupted, use the same saved connection and choose **Check TV status** first. Continue only through the recovery action offered by the wizard. If the state is unknown, save the diagnostic report and stop; keep recovery data and do not blindly repeat installation.

During recovery, keep Home control off and retain the original diagnostic reports and saved connection. Confirm inspection and changes separately. Follow the detailed recovery guide for your installed version; do not force reinstallation or clear recovery state.

For help, include TV model, firmware, No-root or Root, installer device, failed step and error message. Remove passwords, keys, addresses and personal data before sharing a report. Reports are not published automatically.

[Report a problem](../FEEDBACK.md) · [Detailed recovery](../RECOVERY.md) · [Update or remove](../MAINTENANCE.md) · [Other languages](../LANGUAGES.md)

### Straightforward removal

Choose **Uninstall Clean Your TV** in Maintenance with the same saved TV connection. Confirm once. Removal deletes known project apps and files that are present and skips absent items, including after a partial installation.

On older TVs without a separate LG Home app, No-root removal may switch to Live TV. Keep the TV on and follow any requested restart; do not delete recovery records or reset the TV.

When asked, disconnect the TV from power, reconnect it, wait for the network and choose **Try again**. Standby or Quick Start is not a full restart; CYTV does not restart the TV automatically. A connection loss needs a connection check and Try again on the same goal, without another recovery wizard. If access is denied, use the requested Root connection; if the TV is busy, wait and retry. Success appears only after final cleanup is verified. Keep your keys and original reports. The emergency controls and sharing consent above still apply.

Failed or interrupted setup offers recovery directly. If No-root setup cannot continue, confirm full removal once. Removal automatically retries transient connection loss and a busy CYTV worker up to three attempts. If Root access is required, choose **Connect using Root** for the same TV; verified Root cleanup also finishes its blocked No-root removal. A failed Root activation attempts to restore and verify LG Home without repeating activation. Cancellation with unfinished work keeps a diagnostic report and recovery actions. Emergency-stop state remains unchanged.

After a removal connection error, open the connection details, check network access or choose an existing Root SSH key, then retry. The TV address, edition, port and host-key checks stay fixed. No-root checks Helper before pairing: stop it and confirm the recheck in the same setup. An empty TV can skip restart only with verified absence and no unresolved setup; actual removal still requires the requested restart. Input-service failure allows safe package cleanup, but success still requires verified shortcut cleanup.

**Reinstall Root:** Choose **Set up my TV → Root** with the saved connection and confirm **Reinstall Root?**. The installer restores LG Home and fully removes Clean Your TV, including its updaters, Home Helper and saved preferences. After verified removal, it installs and activates the packages and Root runtime bundled with that installer. Other TV apps and existing root/SSH access are preserved. If removal stops or requests a full restart, finish it before starting setup again. **Uninstall Clean Your TV** alone never starts another installation.

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

<a id="unreleased-candidate-older-tv-nodejs"></a>
<a id="older-tv-nodejs-published-v1120"></a>
<a id="straightforward-removal-v1110"></a>

## Weather

Open Settings → Weather, below Wallpapers. Turn weather on, choose City, then search manually and select the correct region and country, or choose Automatic for an approximate city based on your internet connection. A VPN may change the automatic result; if the city is missing or wrong, use manual search. The detected or selected city is shown in settings. Choose °C / m/s or °F / mph and an available format: Compact, Now, In detail or 4 days. The preview follows your theme; Example means sample data. Liquid Glass supports Compact only. Ribbon and Atmosphere do not show weather. Turning weather off stops requests and hides city, units and format controls; source selection remains available. During an outage recent data can remain temporarily; after a longer outage weather disappears until it can refresh.

Choose the forecast provider: Auto, MET Norway or Open-Meteo. Auto starts with MET Norway, tries Open-Meteo once on failure, then reuses the last successful source and cached data. Manual selection never switches sources automatically. New settings use Auto; previously saved settings without a provider keep Open-Meteo. The actual source appears in settings. Availability depends on your network. MET refreshes no more often than every three hours; cached data expires after six hours. Missing fields are hidden: MET does not provide feels-like temperature or precipitation probability. Daily ranges summarize forecast points, not measured extremes.

Forecast coordinates go to api.met.no or api.open-meteo.com; city searches go to geocoding-api.open-meteo.com. Optional automatic city lookup sends your public IP to get.geojs.io. Connections use HTTPS; no API key is needed. Location, source and cache stay on the TV. Data sources includes provider terms and credits, including the Norwegian Meteorological Institute (MET Norway, CC BY 4.0).

The Data sources button in the Weather heading opens provider and license information.
