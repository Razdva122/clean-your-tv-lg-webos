# Install cytv without a terminal

<a id="installer-update-check-unreleased"></a>

## Installer update check

Before a new installation, the computer installer checks GitHub's latest stable
release and compares its installer version from `BUILD-INFO.json` with the running
installer. If newer, choose **Open GitHub and download the latest version** to open
the release page and stop this installation, or **No, install this version** to
explicitly continue with the embedded packages. It never replaces itself or
silently switches packages. The terminal also prints the download link.

Network, rate-limit, TLS or invalid-metadata errors show an unavailable-check
notice and allow installation to continue. Requests use HTTPS with a three-second
timeout per request; no TV data or credentials are sent. Pending operations and
maintenance/recovery commands skip this check. Non-interactive installation stops
when a newer installer is found unless `--use-bundled-version` is explicitly given;
`--yes` alone does not authorize using an older installer.

> **Release 1.9.0:** see [versions, tested scope and recovery limits](RELEASE-1.9.0.md). C1 Beta is fresh-install only, selected automatically in the common installer; normal OTA is unavailable and physical C1 acceptance is pending. Historical results below retain their original artifact scope.

> Release 1.7.1 rebuilds cytv 0.8.1 to correct macOS bundled-package validation. Use the published release link below for available downloads. [Patch scope and checks](RELEASE-1.7.1.md).

> See [1.6.0 versions, installer changes and limits](RELEASE-1.6.0.md) and the [dated acceptance scope](history/2026-11-02-release-1.6.0-final-acceptance.md). Obtain available packages from [GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases).

Download the desktop package from the
[published release](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest).
The wizard includes its runtime and TV packages. No developer tools are needed.
Root setup may download a separate verified TV Python runtime when eligible.

Prepare the TV using [the installation guide](INSTALL.md), then follow your
computer's steps below. For Android, use the [Android guide](../android/README.md).

In 1.6.0, a [visible TV checklist](CLI.md#visible-tv-checks-unreleased) shows individual prerequisite results and keeps them on the error screen. Unrun checks remain unverified; `doctor` does not prepare Python or request control pairing.

## macOS

1. Download `cytv-macos-arm64.zip` for an Apple Silicon Mac (M1 or later), or
   `cytv-macos-x64.zip` for an Intel Mac.
2. Double-click the ZIP to extract `cytv.app`.
3. Drag `cytv.app` into **Applications**, then double-click it.
4. Allow **Local Network** access if macOS asks. Click **Set up my TV**.

### If macOS says “cytv was not opened”

Our current Mac builds are not Apple-notarized. macOS may say that Apple cannot
verify whether cytv contains malware. If you downloaded the app from this
project's GitHub release and want to open it:

1. Click **Done** to dismiss the warning; keep the app in **Applications**.
2. Open **Apple menu → System Settings → Privacy & Security**.
3. Scroll to **Security**, find the blocked cytv message and click **Open Anyway**.
4. Confirm with your Mac password or Touch ID if requested, then click **Open**.

After this approval, launch cytv normally by double-clicking it. If the button is
missing, try opening cytv once more, then return to these settings. A managed
work Mac may require your administrator's help.

These steps apply to the unverified-developer/notarization warning. If macOS
reports actual malware or a damaged app, stop and report the exact message.
Do not disable Gatekeeper or remove quarantine with terminal commands.
See [Apple's first-launch guidance](https://support.apple.com/en-mo/102445).

### If setup reports missing or invalid embedded graphics packages

Affected macOS bundles can reject their normal package-folder alias even when the
IPKs and manifest hashes are valid. Release 1.7.1 (cytv 0.8.1) corrects that validation; both rebuilt macOS bundles
passed their package-selection checks. If this message persists with the complete
published installer, save its diagnostic report for investigation. This error occurs
before package installation. Keep its diagnostic report; do not edit the app bundle,
substitute IPKs or bypass checks. This fix does not require a TV firmware update.

### If the app opens but cannot connect to the TV

**Published v1.12.1:** Connection failures distinguish denied network
access, refused SSH ports and timeouts when the operating system provides that
cause. The failure screen shows guidance and **Check connection again** as the
primary action. This runs Doctor, not installation. **Change connection** checks
an edited address, edition and port without starting setup. On macOS, **Open
System Settings** opens Settings; follow the displayed Privacy & Security →
Local Network path. macOS may list an older duplicate app name. The app cannot
infer the permission switch state from an unreachable/timeout error. Connection
editing/recheck shortcuts are withheld while an operation needs recovery;
follow the existing recovery flow. Saving diagnostics and reporting an issue
remain optional secondary actions.


1. Turn on the TV and connect it and your Mac to the same home network.
2. Open **System Settings → Privacy & Security → Local Network** and enable **cytv**
   if it is listed. Allow access when the app asks.
3. After changing permission, fully quit cytv and reopen it. Use **Check TV status**
   before retrying an interrupted installation.
4. If the connection still fails, save the diagnostic report and open an issue
   with the error, macOS version and TV model. Do not delete recovery files.

Desktop dependencies require macOS 13 or newer; native CI builds run on macOS 15.
Older-system acceptance has not been established.

## Windows x64

Download [cytv-windows-x64-desktop.zip](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip):

1. Download the ZIP, right-click it in File Explorer and choose **Extract All**.
2. Open the extracted `cytv-desktop` folder and double-click `cytv-desktop.exe`.
3. Click **Set up my TV**. No terminal or separate Python installation is needed.

Keep the whole folder together, including `_internal`; do not run the executable
inside the ZIP or copy the executable out by itself. The app opens its own window
without a console. `cytv-windows-x64.exe` is the separate console wizard.
Windows publisher signing is not configured.

## Ubuntu, Debian and Linux Mint

Use an **x64** computer with Ubuntu 22.04 or newer, Debian 12 or newer, or Linux
Mint 21 or newer. ARM Linux packages are not included.

1. Download `cytv-linux-x64.deb`.
2. Double-click the file. In your graphical package installer, click **Install**
   and enter your computer's administrator password if requested.
3. Open **Clean Your TV** from the applications menu.
4. Click **Set up my TV**.

The `.deb` contains the graphical app. The standalone `cytv-linux-x64` executable
is the separate CLI and opens a terminal wizard.

The package installer may download desktop libraries, so keep the computer online.
If double-clicking opens an archive viewer, use **Open With** and select your
software/package installer. Minimal Linux installations without a graphical
package installer need one supplied by their distribution; the `.deb` itself
cannot provide that first installation UI.

After installation, cytv runs as your normal user. It does not ask for your Linux
administrator password when connecting to the TV. Uninstall cytv using your
software manager; this does not uninstall TV apps or delete saved recovery data.

## Language selection

The installer chooses the computer’s language automatically.
Use the language selector to save another language, or choose **Auto** to follow
system settings. On the TV, use **Settings → Language**; this is a separate preference.
See the [localized installation, use and recovery guides](LANGUAGES.md).

## In the wizard

- Turn on the TV and connect it to the same home network as your computer.
- Select a discovered TV, or use the address field and **Help finding my TV**.
- Choose **No-root** for LG Developer Mode, or **Root** for an already rooted TV.
  Connection detection sets the current choice to match the detected connection; you can select either edition. Root privileges are verified after sign-in.
- Review the TV and edition, then click **Continue**. No-root requests control
  pairing on the TV; Root reads the catalog through its authenticated SSH connection.
- Root checks Python 3.9+, TV Node.js 8+, root/Homebrew services and input support.
  Eligible ARMv7 TVs without suitable Python can receive a separate pinned runtime
  over SSH; this does not certify older-TV compatibility. Root activates Home
  control and opens Clean Your TV Home immediately. There is
  no trial countdown or Keep confirmation.

Passwords are masked. SSH identity changes still block the connection. While TV
changes are in progress, the window waits for the step to finish instead of
terminating the installer halfway through an operation.

On failure, read the explanation, click **Save diagnostic report…**, then
**Open an issue**. Include your steps, expected/actual results, TV model and firmware.
Review the JSON report before attaching it. Do not attach your profile folder or keys.

When an earlier installation was interrupted, **Set up my TV** checks its state
before proceeding. If Root and Root Updater are already installed and verified,
choose **Finish Root setup** to activate Home without reinstalling the packages.
If the earlier attempt stopped before updater setup, the wizard verifies recovery
and offers reinstallation in the same flow. Unverified states remain blocked;
save the diagnostic report instead of deleting recovery files.

The start page also offers status, diagnostics, return to LG Home and uninstall.
Existing console commands remain available in the separately distributed CLI.

<a id="guided-no-root-recovery-and-reinstallation-in-130"></a>

### Review interrupted setup or removal

If a No-root installation or removal remains unfinished after **Check TV status**, connection
diagnostics or **Return to LG Home**, click **Review recovery options**. The wizard
keeps the same TV, edition and SSH port, even when several connections are saved.
It asks before inspection and before each supported change, with No selected by
default. Recovery never starts a new installation automatically. **Set up my TV**
also enters recovery when it finds a retained operation. Returning to LG Home
alone does not complete removal. Unknown package/setup outcomes keep their data.

In published v1.11.0 and later, **Uninstall Clean Your TV** uses a simple removal flow:
confirm once, stop/remove known present project items, fully restart the TV when
asked, then choose **Try again** for the final sweep. Disconnect and reconnect
power; standby and Quick Start are not enough. CYTV never restarts the TV
itself. Missing items are skipped, including after a partial setup. Connection
loss needs a connection check and Try again on the same saved TV, without another
recovery wizard. An actual access denial asks for Root; an actual busy operation
asks you to wait and try again. Completion needs both removed and verified-clean
proof. Eligible Root setup may still finish separately with LG Home/Home control
off. Physical checks remain separate. See the
[removal flow](RECOVERY.md#next-candidate-original-operation-recovery-and-full-removal).

For unfinished removal, **Try again** is the primary action and repeats the same
approved goal. **Save diagnostic report…** remains available. For other failed
steps, saving the report is the primary action. Save that attempt's report with
the normal file dialog and attach it to your issue; no
terminal or later `doctor` run is needed. Cancelling the file dialog or choosing
an unwritable destination keeps the original report available. If report creation
failed, the window says so; include the visible error instead. Unknown outcomes
still stop the process, with no automatic retry or deletion of recovery evidence.

## Remove the project from a rooted TV

Choose **Uninstall Clean Your TV** with the saved **Root** connection. The wizard
restores LG Home and removes Root, Root Updater, its service and boot hook, plus
any installed No-root Home, Helper and Home Updater packages. It also removes
owned updater bus permissions and the System Updater supervisor when present.
Other TV applications stay installed.

This also works if an older cytv already removed Root but left Root Updater behind.
The wizard checks that the updater is idle before stopping it and verifies that
project apps, service registrations and startup hooks are gone. If a removal was
interrupted, run the same action again; an ambiguous package removal is never
submitted twice automatically.

Root recovery records, archived updater state and referenced managed Python
runtime slots remain for diagnostics and recovery.
The published v1.11.0 cleanup additionally removes
owned private setup/runtime data when its cleanup proof permits; minimal removal
records and ownership backups may remain. A blocked cleanup is reported explicitly.
They have no active service or startup registration. The Mac application and its
local reports remain installed on your computer.

## Clear WAM caches on a rooted TV

Choose **Maintenance → Clear WAM caches (root required)**. Review the estimated
size, available space and slower-next-launch warning before confirming; the
default is No. This requests only native WAM `cache` and `codecache` cleanup.
It does not clear Session Storage or other app data, reboot or resume setup.
See [WAM cleanup and manual Session Storage risks](WAM-CLEANUP.md).

<a id="unreleased-optional-wam-cache-cleanup"></a>
<a id="interrupted-no-root-installation-in-the-unpublished-140-candidate"></a>

These actions are included in published 1.4.0. Unfinished installation recovery
can reset Home preferences when apps are removed; review the removal confirmation.

## Build and validation

Developer commands and offline screenshots: [desktop build reference](development/DESKTOP-BUILD.md).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="offline-interface-previews"></a>

## Storage estimates in candidate builds

CYTV desktop installation reports **required / available / shortfall** in MiB before
submitting packages, separately for each target filesystem. Requirements sharing
a filesystem are added together. The conservative budget uses unpacked IPK file
sizes rounded to 4 KiB, staging/recovery copies and a 16 MiB reserve per filesystem.
It retains existing files rather than subtracting space that might later be freed.
This is an estimate: firmware installer scratch usage and existing device-specific
backups can still require more. If capacity cannot be read, package submission
stops with the required estimate and explicitly unknown available/shortfall values.

Personal wallpapers show separate estimates for computer temporary storage, TV
video cache and TV app storage. CYTV keeps these figures visible after transfer;
**Received** still means that you must preview and Apply on the TV. Browser quota
information is available only in Home, so CYTV marks that capacity unknown; Home
checks it before saving. A prepared video cache includes a 1 MiB reserve. App
storage estimates allow temporary copies plus a 1 MiB reserve. A positive estimate
is not a reservation: concurrent writes may still exhaust space. On old firmware
without a quota API the required size is shown, with available/shortfall unknown;
normal storage errors remain failures and preserve the current wallpaper.

Downloaded themes also have an independent **64 MiB / 8 themes** cache limit.
A space rejection shows the new theme requirement, remaining cache allowance and
shortfall; the count limit asks you to remove a downloaded theme. Removing apps
may free a different partition or leave the Home app quota unchanged. Free the
specified storage yourself; CYTV does not delete apps, themes or session data
for you. Pending installations still require the normal status/recovery check.

These changes require rebuilt candidate Home/services and desktop CYTV packages.
They do not change published downloads. Host/browser tests are not physical-TV
acceptance; model/firmware-specific storage and installer behavior remain untested.
