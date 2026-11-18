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

If the installer offers **No-root**, you can continue with your existing root SSH connection. Developer Mode is unnecessary for this option.

[Detailed installation guide](../INSTALL.md) · [Compatibility](../COMPATIBILITY.md)

### Developer Mode setup (No-root)

Developer Mode lets CYTV install apps on a TV without root.

1. On the TV, open LG Apps, search for Developer Mode and install it.
2. Open Developer Mode and sign in with your LG Developer account. Create an account at [LG Developer](https://webostv.developer.lge.com) if needed.
3. Turn on Dev Mode Status. The TV restarts. Open Developer Mode again.
4. Turn on Key Server and leave Developer Mode open. Its IP Address is the TV address to enter in CYTV.
5. Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters.

Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.

Pairing is a separate step: when the TV asks, approve CYTV with your remote. If the TV rejects the request, confirm the retry in CYTV. It uses the same TV connection.

If a first No-root setup warns that it could not read HDMI inputs, you can continue with the applications it found.

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
4. Follow the wizard. Keep the TV on, stay on the same network and leave CYTV open until it finishes. Do not force-stop the Android app.

On desktop, after a successful connection check, choose **Continue setup** to keep the same TV connection and edition. The wizard explains any previous installation; technical results are under **Details**. If an earlier operation needs recovery, use the offered recovery action first. Setup checks installed versions and asks for confirmation before changes. The wizard rechecks saved restart requests; a restart is requested only when the current cleanup confirms it is needed.

## 5. Check your remote

1. Open another TV app and briefly press **Home**. Clean Your TV should open. Tell the wizard what you saw; leave the check skipped if you did not test it.
2. Check arrows, OK, Back, volume and sound.

<a id="everyday-use-and-recovery"></a>

## 6. Everyday use and recovery

To open the TV's notification center from Clean Your TV, choose **Home settings → Advanced → LG Notifications**.

To pin an HDMI input, select it in **+ / Add app**. Press OK to switch to it. Hold OK to move or hide its tile.

Arrows select tiles; OK opens them; hold OK to reorder. Short Back retains the app's navigation and exit confirmation. Short Home opens Clean Your TV while Home control is active. Hold Back for 1.2 seconds to open LG Home once. The Home-control switch and your settings remain unchanged.

To edit with short presses, open **Home settings → Appearance → Edit tiles**. Press OK to pick up a tile, move it with the arrows, then press OK to place it. Back cancels the move or exits tile editing.

**Press Home three times within two seconds**, releasing between presses, to return to LG Home and stop Home control. This preserves preferences.

No-root: To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept. Root: turn **Change Home** on in Home settings to resume. **Open LG Home** opens LG Home once without changing routing. To restore LG Home as the persistent destination, turn **Change Home** off. Do not run both controllers together. If a failure repeats, leave LG Home active.

If Home Helper is stopped, you can also choose **Start Helper** in the Home screen or Screensaver settings. The status updates automatically after startup.

## Need help?

If you see `ssh-identity-changed`, stop and verify the TV’s SSH key. [Recovery after an SSH key change](../RECOVERY.md#ssh-identity-changed)

For your own No-root TV after a factory reset, choose **Reconnect after factory reset** when the installer reports a changed key. Follow the prompts on your trusted home network. The installer keeps the previous profile and removal record.

If installation was interrupted, use the same saved connection and choose **Check TV status** first. Continue only through the recovery action offered by the wizard. If the state is unknown, save the diagnostic report and stop; keep recovery data and do not blindly repeat installation.

During recovery, keep Home control off and retain the original diagnostic reports and saved connection. Confirm inspection and changes separately. Follow the detailed recovery guide for your installed version; do not force reinstallation or clear recovery state.

For help, include TV model, firmware, No-root or Root, installer device, failed step and error message. Remove passwords, keys, addresses and personal data before sharing a report. Reports are not published automatically.

If No-root offers **Retry storage check**, choose it to repeat the read-only check on the same TV. Confirm installation separately after the check passes. If the installer finds an unfinished operation, use **Review recovery options**.

If the desktop installer verifies the packages but Home doesn't open Clean Your TV, choose **Home button diagnostics** for No-root or **Check TV status** for Root on the results screen. No-root shows your recorded result. Use **Save diagnostic report** to keep a copy.

After a desktop installer failure, select **Open an issue** to review and copy your draft. Attach the saved diagnostic report in the issue form if available.

[Report a problem](../FEEDBACK.md) · [Detailed recovery](../RECOVERY.md) · [Update or remove](../MAINTENANCE.md) · [Other languages](../LANGUAGES.md)

### Straightforward removal

Choose **Uninstall Clean Your TV** in Maintenance with the same saved TV connection. Confirm once. Removal deletes known project apps and files that are present and skips absent items, including after a partial installation.

When asked, disconnect the TV from power, reconnect it, wait for the network. Standby or Quick Start is not a full restart; CYTV does not restart the TV automatically. If cleanup requires Root access, use your existing Root connection to the same TV. Without existing Root access, cleanup remains incomplete. If the TV is busy, wait and retry. Success appears only after final cleanup is verified. Keep your keys and original reports. The emergency controls and sharing consent above still apply.

If the desktop installer waits for the TV, choose **Continue removal** when it appears. Choose **Cancel** to stop waiting or **Try again** to check manually.

If **Return to LG Home** appears on the removal screen, choose it. Once the installer verifies the restoration, select **Continue removal**. Choosing **Return to LG Home** directly from Maintenance keeps the apps installed.

If the installer cannot verify removal, final cleanup, TV controls or the package result, or reports changed project paths, choose **Review recovery options** with the original saved connection. Confirm continuation separately if the installer offers it. If No-root installation recovery offers **Check TV status**, choose it and keep the recovery data.

If the installer cannot verify the requested full restart, save and attach its diagnostic report. Keep the saved connection and recovery data. Do not keep repeating power cycles or clear the unfinished operation manually.

After verified removal, you can close the desktop installer or choose **Set up my TV** to start a new setup on the same TV with the same edition and connection.

**Reinstall Root:** Choose **Set up my TV → Root** with the saved connection and confirm **Reinstall Root?**. The installer restores LG Home and fully removes Clean Your TV, including its updaters, Home Helper and saved preferences. After verified removal, it installs and activates the packages and Root runtime bundled with that installer. Other TV apps and existing root/SSH access are preserved. If the desktop wizard pauses, open the same installer and choose **Continue Root reinstallation**. After it verifies removal, choose **Continue Root installation**. **Uninstall Clean Your TV** alone never starts another installation.

### Adjust LG settings and finish a Root rollback

In the desktop installer, open **Maintenance action → Adjust LG settings (Debloat)** with your saved TV connection. Select the settings you want to change, choose **Apply selected settings**, then review the results. If an earlier operation is unresolved, choose **Review recovery options** with its original saved connection first.

- [Root Updater](../RECOVERY.md#standalone-root-updater-rollback-readiness)
- [Root System Updater](../RECOVERY.md#root-system-rollback-readiness-candidate)

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

## Settings

Under **Settings → Appearance**, turn on **Sort by most used** to bring apps you launch often to the top of the grid. The dock keeps its order. Hold OK to edit in manual order, including moving a tile to Hide. Turn the switch off to return to your manual order. You can also choose this at the end of the cytv installer’s Settings step.

Use ↑ ↓ to choose a category and → or OK to enter it. ← returns to categories; Back returns there first, then closes settings. Within a section, returning from categories restores the last available control. In Columns, arrows follow the three-column grid. In Language, entry focuses the selected language.

In **Settings → Your Home screen → Clock format**, choose **Automatic (TV locale)**, **12-hour**, or **24-hour**.

If No-root cannot read Home status, choose Try again. The unavailable control does not mean Home routing is off. Under Wallpapers, upload a personal image from a phone or CYTV; quality and dimming appear when a wallpaper is available. Removing a personal wallpaper asks for confirmation; Cancel keeps it.

## Weather

Open Settings → Weather, below Wallpapers. If you have no saved city, Home estimates it from your internet connection when weather is on. To choose it yourself, open City → Manual, search, and select the correct region and country. A VPN may change the automatic result; if the city is missing or wrong, use manual search. The detected or selected city is shown in settings. Choose °C / m/s or °F / mph and an available format: Compact, Now, In detail or 4 days. The preview follows your theme; Example means sample data. Liquid Glass supports Compact only. Ribbon and Atmosphere do not show weather. Turning weather off stops requests and hides city, units and format controls; source selection remains available. During an outage recent data can remain temporarily; after a longer outage weather disappears until it can refresh.

Choose the forecast provider: Auto, MET Norway or Open-Meteo. Auto starts with MET Norway, tries Open-Meteo once on failure, then reuses the last successful source and cached data. Manual selection never switches sources automatically. New settings use Auto; previously saved settings without a provider keep Open-Meteo. The actual source appears in settings. Availability depends on your network. MET refreshes no more often than every three hours; cached data expires after six hours. Missing fields are hidden: MET does not provide feels-like temperature or precipitation probability. Daily ranges summarize forecast points, not measured extremes.

Forecast coordinates go to api.met.no or api.open-meteo.com; city searches go to geocoding-api.open-meteo.com. Optional automatic city lookup sends your public IP to get.geojs.io. Connections use HTTPS; no API key is needed. Location, source and cache stay on the TV. Data sources includes provider terms and credits, including the Norwegian Meteorological Institute (MET Norway, CC BY 4.0).

The Data sources button in the Weather heading opens provider and license information.

## iPhone wallpaper upload

Open Settings → Wallpapers → Upload from phone and scan the code. Choose a JPG, PNG or HEIC/HEIF photo, crop it, acknowledge the quality limit and send it. Choose Apply on the TV. Safari uses native HEIC support; Chrome, Firefox and other modern browsers use the bundled local decoder when needed. Conversion runs on your phone, without a conversion website. Cancel or choosing another file stops conversion. Input limit: 32 MiB and 50 million pixels; output: at most 1080p and 2 MiB. If conversion fails, try another photo or JPG/PNG. This support is for the phone page, not the Mac file picker.

## Set up your Clean Your TV

Before choosing a theme, use **Debloat** to select which LG ads, recommendations, privacy settings and notifications to change. The desktop installer selects every option by default. Clear any options you want to keep as they are before clicking **Continue**. Check each result before continuing. If the installer could not read the original value, it cannot save it for an automatic undo. Choose **Skip Debloat** to keep your current settings.

During removal, you can choose to restore the saved original Debloat settings. If you skip restoration, removal continues with those settings as they are.

After successful installation, choose Classic, Liquid Glass or Ribbon and turn Home weather on or off. Ribbon does not support weather; Liquid Glass uses the compact format. Weather can find an approximate city through your internet connection; change it later in Home settings.

No-root with Developer Mode offers optional auto-renewal; keep monitoring the official timer. New No-root installations through existing root SSH hide the Developer Mode tab. Root offers LG firmware update blocking through Homebrew Channel, including security updates; a real restart through Homebrew Channel is required. This is separate from CYTV updates.

Choose Keep current settings to skip customization. The mode switch shows its current On/Off state. Unchanged mode settings are kept. Root reinstallation still removes saved CYTV preferences as described above. Check the chosen appearance on the TV; an optional setting reported as unconfirmed needs checking in Home settings before retrying.

## Updates on a rooted TV

If a self-updating System Updater has been set up, use **Software updates → Update all** for Root or No-root on a rooted TV. Keep the TV powered on until it finishes. To repair only the updater, open Home and choose **Software updates → Recovery → Reinstall System Updater**; Home and your settings stay unchanged. No-root without root still uses the computer installation method.
