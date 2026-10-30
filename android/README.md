# Install Clean Your TV from Android

> Unpublished 1.5.0 candidate: Android 0.5.0 / versionCode 15. See the [release scope and pending acceptance](../docs/RELEASE-1.5.0.md). Published stable is 1.4.1 (Android 0.4.1 / versionCode 14); historical acceptance below retains its original scope.

Use your phone to install either **No-root** (Developer Mode) or **Root**
(existing root SSH) on an LG webOS TV. No PC, Termux, phone Python installation
or cloud service is needed. The APK includes the offline interface and TV packages;
optional TV Python is a separate verified download.

Release **1.4.0** includes **Android 0.4.0 / versionCode 13**.
[Download the signed APK](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest) ·
[Full installation guide](../docs/INSTALL.md) · [Recovery](#recovery-and-private-data) ·
[Report a problem](../docs/FEEDBACK.md)

Requires a **64-bit ARM phone, Android 7.0+ and WebView/Chrome 108+**.
Android 15 / API 35 ARM64 with WebView 124 was verified in an emulator.
Physical phone-to-TV installation/recovery and the minimum Android/WebView
configuration remain unverified. See [acceptance and limits](STABLE-READINESS.md).
Update over your existing APK without uninstalling or clearing data; the
application ID and signing certificate are retained.

The interface supports twelve languages and follows the phone language on first
launch, with English fallback. Tap the top-right language control to choose and
save another language. Root and No-root are equal options for different TV access.

<a id="release-140"></a>
Current versions and evidence are in the [1.4.0 release notes](../docs/RELEASE-1.4.0.md)
and [Android acceptance](STABLE-READINESS.md).

**Unreleased:** a [visible TV checklist](../docs/CLI.md#visible-tv-checks-unreleased) shows individual prerequisite results and keeps them on the error screen. Unrun checks remain unverified; `doctor` does not prepare Python or request control pairing.

## Install and connect

1. Copy the signed APK to a **64-bit ARM phone running Android 7.0 or later with Android System WebView/Chrome 108+**. Allow the browser/file manager to install this APK when Android requests it.
2. Keep the phone and LG webOS TV on the same local network. Turn the TV on; disconnect VPNs or guest-network isolation if the connection fails.
3. Enter the TV IPv4 address and check the connection first. Then choose **No-root** for Developer Mode, or **Root** for a TV with existing root SSH access. Exactly one responding access mode is highlighted; with both or neither, choose manually. Default SSH ports are 9922 and 22 respectively; Root ports are editable.
4. No-root: follow the four preparation steps in CYTV: install Developer Mode, sign in with an LG Developer account, enable **Dev Mode Status** and reopen the app after reboot, then enable **Key Server**. Enter the six-character **Passphrase** from the TV, preserving letter case; this is separate from the LG account password. The steps and code prompt include offline LG reference screenshots; use the code on your own TV. See the [full setup guide](../docs/INSTALL.md#set-up-developer-mode-no-root). Root: use the existing SSH password or select a private key with Android's file picker. Encrypted keys prompt for their passphrase.
5. Review the SSH fingerprint before trusting the TV. Review the actual installed/package versions before confirming installation. Accept the remote-control pairing prompt on the TV if shown.
6. Keep the TV on. The foreground service continues while the Activity is in the background; keep Android's CYTV notification available. Do not force-stop the app or change networks during installation.
7. Check Home, arrows/OK, Back, volume and standby/wake on the TV. Root requires existing compatible root, Python 3.9+, Node.js 8+, Homebrew services
   and supported ARM32 remote input on the TV. Eligible missing Python can be supplied
   as a pinned private ARMv7 runtime downloaded on the phone and transferred via SSH;
   a compatible TV loader/libc is still required. Working system Python skips this download.
   See [runtime limits](../docs/OPTIONAL-PYTHON.md). CYTV does not root or flash the TV.

Older 32-bit phones and x86 devices are not included in this APK. The UI includes install, status and restore; it does not expose uninstall or automatic discovery. The full TV app inventory is imported automatically. Compatible whole-edition TV updates require separate computer-assisted System
Updater bootstrap with root/Homebrew services. Unrooted TVs use the installer.
The APK does not expose that bootstrap action; see [updates](../root-edition/UPDATES.md).

## Recovery and private data

Open **Status and recovery** from the start screen. After an interruption,
check status before reinstalling. The app retains operation receipts and does
not automatically repeat installation after process death. Keep the same TV,
edition and SSH port; pending or unknown outcomes need inspection.

Android exposes install, status and restore. For removal, use desktop/CLI with
the retained connection and evidence. An interrupted No-root removal needs its
verified continuation and separate confirmation; an unknown removal outcome stays
blocked. Status and restore do not download Python. Keep runtime slots needed
for recovery.

Three short Home presses within two seconds request the existing TV emergency exit. Older No-root Helper versions through 0.6.13 instead use holding Home for two seconds. Root cold-power behavior and model compatibility retain the limitations documented by the TV project.

Profiles, imported keys and pairing data live in the app-private directory. Android backup is disabled. Passwords are requested on demand and are not written to the UI log or preferences. Imported keys persist for later use; uninstalling Android CYTV removes them and the local recovery receipts. Raw logs remain local and can contain TV addresses; no automatic sharing/export is implemented. The Android package needs Internet/network access for local TV sockets, foreground-service/notification permissions and a bounded wake lock. Cleartext is enabled for the TV's Developer Mode Key Server; the WebView itself blocks all network navigation and serves only bundled files.

## Build and verification

See [Android development](DEVELOPMENT.md) for prerequisites, signing, test commands
and the limits of emulator/browser evidence.

<a id="build"></a>
See [build instructions](DEVELOPMENT.md#build).
<a id="checks-and-screenshots"></a>
See [checks and screenshots](DEVELOPMENT.md#checks-and-screenshots).
<a id="maintenance-connection-continuity-in-130-issue-12"></a>
See [connection continuity](DEVELOPMENT.md#maintenance-connection-continuity-in-130-issue-12).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="cytv-for-android--040-versioncode-13"></a>
