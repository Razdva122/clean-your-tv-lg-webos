# Install Clean Your TV

Unreleased: The installer asks for a TV name, default **Home**; scripts can use `--tv-name "Aashiyaan"`. After upgrading an older installation, **Settings → Home → TV name** is available automatically. Save a new name or reset to Home at any time. A saved name survives restart and supported updates; existing settings remain intact. Names allow up to 48 characters. Settings saves the launcher name. To change LG’s startup screen, apply the same name through the installer. Home adds no second loading screen; the network name is unchanged.

> **Shared experimental compositor backend:** the installer selects this
> backend for ordinary Root and Root Beta by verified capabilities, without an
> SDK/model allowlist. It requires fresh setup, confirmed absence of System Profile,
> stock ARM32 native LG Home, vendor Qt filters and compatible emergency input and
> recovery. Conflicting Home integrations are left untouched. Experimental OTA is
> disabled; physical compatibility remains unconfirmed. See [scope and recovery](development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).

Use **cytv** to install No-root or Root. It includes the computer runtime and TV
packages; no source build is needed. After setup, the computer can be switched off.
Download the [published release](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest).
See [compatibility](COMPATIBILITY.md) for tested TVs and remaining limits.

## 1. Choose your edition

| Your TV | Choose | You need |
| --- | --- | --- |
| No existing root access | **No-root** | LG Developer Mode, Key Server and an active session |
| Already rooted | **Root** | Working root SSH and supported TV services/input |

Root setup does not obtain root or flash firmware. Do not enable Developer Mode
over an existing rooted setup, or run Root routing and No-root Helper together.
[Compare everyday controls and limits](EDITIONS.md).
Normal profile-based Root also requires working Settings Service and System Profile
Home interfaces (`com.webos.service.systemprofile`). The installer's
shared [compositor backend](development/C1-NATIVE-GATE.md) supports ordinary Root
and exact-Node-0.12.2 Root Beta only when System Profile absence and all native
Home/input/recovery requirements are verified. A KeyFilters field alone is
insufficient; old in-compositor LG panels remain unsupported. This fresh-install
experimental path still has no target-TV physical acceptance or normal OTA support.
Root access alone does not establish compatibility.

If No-root was installed again after full removal, switching to Root may require cleanup first. Back up Home preferences, choose **Uninstall Clean Your TV** with the saved Root connection and wait for verified removal. This also removes No-root Home and Helper. Then install Root; keep recovery records.

## 2. Prepare your TV and computer

Turn on the TV. Connect it and your computer to the same trusted local network.
Guest-network isolation, VPNs and firewalls can block the connection. Allow
Local Network access when asked.

### Set up Developer Mode (No-root)

<a id="set-up-developer-mode-no-root"></a>

1. On the TV, install **Developer Mode** from LG Apps.
2. Open it and sign in with an LG Developer account. Create an account at
   [LG Developer](https://webostv.developer.lge.com) if needed.
3. Turn on **Dev Mode Status**, let the TV restart, then reopen Developer Mode.
4. Turn on **Key Server** and leave Developer Mode open. Enter its **IP Address** in cytv.
5. Enter the six-character **Passphrase** shown on the TV, matching letter case.

Use the TV code, not your LG password. If the code is missing, enable Key Server.
Approve the separate control-pairing request on the TV when it appears.
Before the Developer Mode timer expires, open the app and press **EXTEND** while
online. Expiry can remove sideloaded apps. Auto-renewal is optional, off by default
and [Beta](DEVELOPER-MODE-BETA.md); keep checking the official timer.

The installer checks Helper's TV Node.js requirement before changing packages.
See [LG's instructions](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app).

### Prepare an already rooted TV

Confirm root SSH access and keep recovery backups. Root needs Python 3.9+,
Node.js 8+, luna-send, Homebrew services and supported ARM32 Magic Remote input.
Investigate changed SSH host keys instead of bypassing the check.
If suitable Python is missing, cytv can transfer a separately verified ARMv7
runtime; [eligibility and space requirements](OPTIONAL-PYTHON.md) still apply.

## 3. Download and start cytv

| Device | Download and open |
| --- | --- |
| macOS 13+ Apple Silicon / Intel | `cytv-macos-arm64.zip` / `cytv-macos-x64.zip`; extract and move `cytv.app` to Applications |
| Ubuntu 22.04+, Debian 12+, Mint 21+ x64 | Install `cytv-linux-x64.deb`; open Clean Your TV from the applications menu |
| Windows x64 | Extract `cytv-windows-x64-desktop.zip`; open `cytv-desktop/cytv-desktop.exe` with `_internal` beside it |
| Android ARM64 | Install `cytv-android-arm64.apk`; follow the [Android guide](../android/README.md) |

Mac builds are not Apple-notarized; use the documented [Open Anyway steps](DESKTOP_INSTALL.md#if-macos-says-cytv-was-not-opened).
Windows publisher signing is not configured. Linux ARM desktop packages are not
included. Android physical-phone and live phone-to-TV acceptance remain unverified.

[Desktop setup and troubleshooting](DESKTOP_INSTALL.md) · [Console guide](CLI.md) ·
[Localized guides](LANGUAGES.md).

## 4. Install No-root or Root

1. Choose **Set up my TV**.
2. Select a discovered TV or enter its IP address.
3. Choose **No-root** or **Root**, then review the TV and edition.
4. No-root: enter the TV passphrase and approve control pairing on the TV.
   Root: use existing root credentials and verify the SSH identity.
5. Keep the TV on until installation and verification finish.

No-root installs Home and Home Helper, configures pairing/startup and starts
Helper. Root installs Home, independent recovery and Root Updater, prepares its
rollback baseline, verifies setup and activates Home. There is no trial countdown
or Keep confirmation. A standalone Root IPK is not a complete installation.

If interrupted, use **Check TV status** first. Use **Finish Root setup** only when
offered for a verified installation. If the state remains uncertain, save the
diagnostic report and keep recovery files. [Recovery](RECOVERY.md).

<a id="7-verify-before-daily-use"></a>

## 5. Verify before daily use

- Check arrows and held arrows, OK, Back inside apps, volume, pointer and wheel.
- Open an app, then press short Home to return to Clean Your TV.
- Press Home **three times within two seconds**, releasing between presses.
  LG Home should open with working navigation.
- Resume No-root by opening **Home Helper**, choosing **Start Helper** and confirming.
  Resume Root by turning **Change Home** on in Home settings.
- Test standby/wake and cold boot separately, including what happens without
  pressing Home. Root cold-power acceptance remains limited; read [compatibility](COMPATIBILITY.md).

**Change Home** selects persistent Home behavior. **Open LG Home** only visits
LG Home once. Opening Home alone does not restart a stopped Helper. Helper
through 0.6.13 uses a two-second Home hold instead of triple Home.
Root 1.7.0 adds native startup source choices under
**Home settings → Open Clean Your TV first**: LG Channels / Live TV defaults on,
YouTube defaults off; there is no HDMI startup setting. With **Change Home** off these controls are visibly
disabled with an explanation and retain their values. There is no late boot/wake
launch fallback. See the linked 1.7.0 acceptance record for exact-package physical limits.

If a check fails, leave LG Home active and follow [recovery](RECOVERY.md).
Installation checks cannot verify physical buttons.

## 6. Updates, recovery and removal

Use cytv's saved connection for status, diagnostics, restore and uninstall.
Removing cytv from your computer leaves the TV installation in place.
Root removal also removes installed project updaters and No-root components;
inactive recovery evidence is retained intentionally.

[Updates](UPDATES.md) · [Recovery](RECOVERY.md) · [Maintenance and removal](MAINTENANCE.md).

## Candidate: on-TV Root installation

**Unpublished:** the separate CYTV Installer for Homebrew Channel is Root-only;
no public catalog listing is established. It requires a verified candidate package,
compatible ARM32 TV, effective root services and runtime/storage checks. Home
activation and optional System Updater preparation are explicit separate steps.
Homebrew upgrades Installer itself; product updates use the product updaters.

For supervised testing, follow the [candidate acceptance and recovery contract](development/HOMEBREW-INSTALL-ACCEPTANCE.md)
and [manual continuation requirements](MANUAL_INSTALL.md#candidate-shared-product-continuation).
After interruption, inspect status and keep journals; never repeat an uncertain submission.
Deleting Installer alone leaves the installed product and recovery in place.

## Source installation without cytv


For either edition, use [manual installation](MANUAL_INSTALL.md): it covers
requirements, app inventory, build, pairing, activation, updater setup and recovery.
Use a new output directory for Root bundles and retain all support files.

For **No-root only**, `install.sh` automates source setup on macOS/Linux with
Node.js 20.19+ and npm, Python 3.9+ with pip/venv, and Git:

```sh
git clone https://github.com/Razdva122/clean-your-tv-lg-webos.git
cd clean-your-tv-lg-webos
./install.sh 192.168.1.50
```

Replace the IP. This prepares local dependencies, Zig 0.14.1 and webOS CLI 3.2.6,
pairs, syncs your apps, builds and installs Home and Helper. No global install or
sudo is needed. Internet access is required for tool downloads. The script creates
`clean-your-tv-<IP-with-dashes>` as its CLI profile; `DEVICE=another-name` selects
another profile without retargeting an existing TV connection.

Rerunning resyncs and rebuilds the current checkout while preserving
`launcher/config.js`; update the checkout first to obtain new source changes.
A failed run does not roll back installed packages. Keep `.lgtv-key.json` and CLI
keys private and do not use `bash -x`. Native Windows is not supported by this
Bash script; WSL installation is unvalidated. The Windows cytv console wizard
is distributed separately.

### Termux / Android

Supply a working **Zig 0.14.1** executable before running `install.sh`:

```sh
export ZIG=/absolute/path/to/zig
"$ZIG" version  # must print 0.14.1
./install.sh 192.168.1.50
```

A matching `zig` on PATH is also accepted. Android has no compatible
`ziglang==0.14.1` Python distribution; an explicit compiler skips that dependency.
Without one, setup stops before pairing or changing the TV. The compiler must
run in your actual Termux/container environment; CPU architecture alone does not
prove Android compatibility. Node.js, Python and CLI requirements still apply.
End-to-end Termux and C5/webOS 26 compatibility remain unverified.

## Root GUI after supervisor setup

If Software updates shows `Denied methods call status`, close and reopen
**Home Root** once. If it persists, save diagnostics and check status; keep
supervisor and recovery state. See [update preparation](UPDATES.md#one-time-computer-preparation).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="install-clean-your-tv--no-root-and-root"></a>
