# cytv standalone installer

[Documentation](README.md) · [Graphical installation](INSTALL.md) · [Help and feedback](FEEDBACK.md)

This is an advanced reference. Use the graphical installer for the normal setup path.
No-root and Root are equal options for different TV setups. Choose No-root for LG Developer Mode or Root for existing root SSH access. Compatibility and test coverage remain specific to each edition.

For double-click setup without a terminal, use the [desktop application](DESKTOP_INSTALL.md).

`cytv` is one terminal wizard for **No-root Edition** and **Root**. Native
builds embed the TV packages, the computer Python runtime and SSH/control libraries.
The optional TV ARMv7 Python archive is downloaded separately on demand. End users
do not need Git, Node.js, Python, Bash, Zig or a separate SSH client.

This is a new installer, not an expansion of the hardware compatibility claim.
Hardware evidence remains scoped to the documented models. Source/automated checks cannot replace real TV acceptance.

## Visible TV checks (unreleased)

Console, desktop and Android installers show the existing prerequisites one by
one: SSH sign-in, edition-specific runtimes, webOS tools/directories, routing
conflicts and Helper readiness where applicable, followed by control pairing and
inventory during installation. Each row has a text status as well as a visual
marker. Results remain visible after failure; subsequent steps stay **Not checked**.
An interrupted probe is **Could not verify**, not evidence of a missing runtime.

Python and Node.js checks concern the **TV**, not the computer running cytv.
Root setup can prepare private Python only when its other prerequisites pass;
`doctor` does not prepare a runtime or request control pairing. A failed runtime
check does not justify deleting profiles, resetting pairing or re-rooting. Save
the diagnostic report and identify the failed requirement first. These rows reuse
the existing probes; they do not add TV changes or establish hardware acceptance.

## Run

Download the console executable matching your computer from the
[latest release](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest).
Development artifacts are also available from the **cytv standalone builds** workflow. Supported build targets are Windows x64, Linux x64, macOS ARM64 and macOS
x64. Linux builds use Ubuntu 22.04; macOS builds use macOS 15. Older desktop OS
compatibility is not established.

For a graphical window, Linux uses `cytv-linux-x64.deb`; the standalone
`cytv-linux-x64` is this CLI. Windows provides
`cytv-windows-x64-desktop.zip`, extracted with **Extract All** and launched via
`cytv-desktop/cytv-desktop.exe` with its `_internal` folder intact.
See [desktop setup](DESKTOP_INSTALL.md).

Windows CLI: download `cytv-windows-x64.exe` and open it, or run it from PowerShell.
If you rename it to `cytv.exe`, use that name in the command examples. The console stays open after
the wizard when launched without arguments. macOS/Linux: open a terminal in the
download directory, restore executable permission if your ZIP extractor removed
it, then run:

```sh
chmod +x cytv
./cytv
```

The macOS build is ad-hoc signed by the freezer, not Developer ID signed or
notarized. Windows publisher signing is not configured. Downloaded executables
may require the operating system's normal approval for an unidentified developer.
Do not disable system-wide security settings.

## Root updates included

The Root installer includes Root Updater. In the same installation it installs
Root Home, prepares its exact package as the rollback baseline, registers the
independent updater and boot recovery worker, and verifies the service before
enabling Root Home. No separate updater command is needed. Subsequent compatible
edition release sets install from Settings → Software updates after the separate
System Updater bootstrap described below.

If updater setup or verification fails, activation stops with LG Home selected
and the operation receipt retained. Run `cytv status` and inspect the retained
setup state before retrying; an interrupted setup is not automatically replayed.
Existing updater installations are not overwritten by reinstall: their recovery
runtime is pinned. Use TV updates, or reviewed recovery if the updater is broken.
Infrastructure migrations can still require a computer. This combined flow needs
real-TV acceptance; automated tests do not establish hardware compatibility.

## Installation wizard

If a previous No-root removal is unfinished, installation offers to finish it
before continuing. This is a separate, default-No confirmation, including with
`--yes`. It restores LG Home and resumes the existing verified package-removal
flow; it does not delete the operation journal to bypass recovery. Declining
keeps recovery data. Non-interactive installation stops with instructions to
use the interactive installer or `cytv uninstall` for the same saved TV/profile.
If recovery fails, attach the new diagnostic report for the `uninstall` phase.

Desktop behavior in 1.3.0 (absent from earlier v1.2.0 installers): successful
status, doctor or restore checks with an unfinished No-root removal offer
**Recover and reinstall** for the same saved connection. This uses the existing
interactive install/removal flow and preserves its separate default-No recovery
confirmation. Desktop report delivery uses a dedicated report event rather than
recognizing a filename in translated log text. Failure reports retain the failed
action, phase, traceback locations and allowlisted error metadata; the window
offers **Save diagnostic report…** without another doctor run. CLI and Android
still receive the existing report path through their normal output adapters.
No new TV endpoint, permission, persistent recovery state or automatic retry is
introduced. Issue #65's original device failure remains under investigation.

Developer Mode key failures include a safe `connection` object in diagnostic
JSON: `protocol: developer-key` and an allowlisted `reason_code`:
`key-server-unavailable`, `response-redirect`, `response-size`, `response-format`
or `key-unlock`. Reports never contain the response, private key, passphrase or
remote exception text. `key-unlock` does not prove an incorrect passphrase: a
damaged or unsupported key can fail in the same parser. Enter the current
six-character Developer Mode passphrase exactly, including letter case; if the
failure persists, compare key retrieval with LG's official CLI. Do not attach
private keys or passphrases to an issue.

After connecting, cytv reads the installed TV versions and shows current → bundled version for Home and Home Helper (No-root), or Root and Root Updater. Review and confirm before installation. First installs, reinstalls and downgrades are labeled separately; `--yes` skips confirmation but still prints the versions.

The wizard separates steps with headings, whitespace and numbered options.
On an interactive terminal each major step starts a fresh screen; scrollback is
retained. Questions begin with `>`. Bold uses the terminal's own foreground color,
so it works on light and dark themes. Redirected output and `TERM=dumb` remain
plain text; `NO_COLOR` disables emphasis. Paragraphs wrap to the terminal width.

The opening screen searches for LG webOS TVs on the local network for a few seconds.
Choose a TV by number (Enter selects the first), `r` searches again, and `0` opens
manual entry. The list includes the TV's name/model when available and its address.
The search uses LG's SSDP service on active local IPv4 interfaces, including when
a VPN changes the default multicast route. Discovery never pairs, installs or
changes the TV; SSH identity verification still happens later.

Keep the TV on and connect both devices to the same home network. Allow Local
Network access for cytv or the terminal if the OS asks. Some VPNs, firewalls, guest
Wi-Fi and router isolation still block discovery. If nothing is found, the wizard
offers retry or manual entry immediately. `--no-discovery` skips the search;
`--host`, saved profile reuse and `--non-interactive` do not broadcast.

Manual entry shows a short explanation of where to find the TV's IP address:
Settings → All Settings → General → Network, then Advanced Wi-Fi Settings or Wired
Connection (Ethernet). Older TVs may place Network under Connection. Read the
address without editing network settings. See [LG's network menu guide](https://www.lg.com/us/support/help-library/lg-tv-how-to-manually-change-the-dns-server-settings--20150576570174)
for model/version differences.

Type `r` at the address question to retry discovery (unless disabled), or `?` to
show help and the guide link. A blank/invalid address or menu choice can be corrected
in place; it does not generate a bug report.
`q` or Ctrl+C cancels a normal question. Password questions use Ctrl+C to cancel;
typing is hidden, with an explanation of which password/passphrase is needed.
Existing profiles appear in a selection menu during installation, including an
option to add another TV. Private key paths accept quoted/dragged files and explain
what to do if the file is not found. Final confirmation shows the TV and edition;
installation uses `[Y/n]` (Enter continues). Removal and restore still require an explicit yes.

1. Select a discovered TV (or enter its address manually). The wizard checks SSH
   banners on port 22 (or the supplied custom Root port) and Developer Mode port
   9922, without signing in or sending commands. Root SSH suggests **Root**; if it
   is not detected, the default is **No-root**. A closed port does **not** prove
   the TV is unrooted; SSH may be disabled or use another port. Choose manually
   when needed. Explicit `--edition` and saved profile reuse skip this check.
2. Read the requirements and accept the installation summary.
3. For a previously known TV, cytv verifies its remembered key automatically.
   It also reuses exact host/port records from `~/.ssh/known_hosts`, including
   hashed hostnames; an existing cytv pin takes precedence. On first connection,
   confirm **Connect and remember this TV?** only for your own TV on a trusted
   home network. Enter confirms (`[Y/n]`); `n` or `q` cancels. There is no required SHA256 copying; `?` shows the
   fingerprint for optional comparison with an independently trusted connection.
   This first-use approval establishes trust; it cannot independently certify an
   unknown TV. A changed saved key or a matching revoked trust record is blocked
   before sign-in, without a confirmation override.
4. **No-root:** enable Developer Mode and Key Server on the TV, enter its passphrase
   when requested, then accept the separate remote-control pairing request on TV.
   **Root:** after host-key verification, cytv first tries automatic sign-in:
   a saved/explicit identity, or passwordless login followed by up to three keys
   from the running SSH agent. Only if these attempts fail does the wizard offer
   a root password or private key file. A successful file choice is remembered
   for this TV; rejected keys are not saved. Encrypted keys still need their
   unlock passphrase. No passwords are guessed and no directories are scanned
   for keys. `--identity` explicitly selects a key and bypasses other methods.
   If an agent cannot sign, the wizard closes that session and offers a manual
   sign-in choice, then makes one fresh connection with automatic methods disabled.
   Connection loss/timeouts stop authentication; they do not trigger more key or
   password attempts. Host-key verification also applies to the new connection.
   The wizard never obtains root or installs Developer Mode onto a rooted setup.
   Root privileges and the required webOS environment are verified after login.
5. Fresh applications, icons and inputs are read from the TV; packages are
   personalized locally. No personal inventory is included in distributed builds.
   Keep the TV on with its Home screen visible. Some TVs keep SSH active in
   standby but reject the remote-control connection with `1008 / EWS`. The wizard
   then asks you to turn on the TV with its remote and press Enter to check again;
   `q` cancels. This retry covers only pairing/inventory, before package installation.
   Noninteractive mode stops with a clear error instead. No automatic wake command
   or retry of package changes is sent. Saved pairing tokens avoid repeated TV
   approval when still valid.
6. The wizard installs and verifies the edition. No-root requests Home Helper
   launch. Root installs recovery before changing system Home.
7. Root installation verifies recovery, stops the old No-root Home Helper,
   enables persistent Home control and opens Clean Your TV Home automatically.
   The installer verifies routing, the recovery guardian and persistent intent
   before reporting **Root is ready**. Turn **Change Home** off, use three short
   Home presses within two seconds, or `cytv restore` to revert.

The old Helper is disabled at startup and stopped through its existing control
command; its files and stop latch remain available. If it cannot stop automatically,
the interactive wizard asks you to press Home three times within two seconds and release all
buttons, then retries the stop step before continuing. Noninteractive runs stop
with instructions. Root activation never bypasses the Helper idle check.

If activation or opening Home cannot be confirmed, cytv keeps an activation receipt
and recovery data. Use `cytv status` to inspect the outcome or `cytv restore` to
return to LG Home. A verified active state resolves the receipt. If the launch acknowledgement was
lost, status reports the screen launch as unconfirmed and asks you to press Home.
An uncertain enable or launch is never automatically retried.
Manual installation with `deploy.py install` still installs recovery only; see
[manual installation](MANUAL_INSTALL.md) for the separate activation step.

If Root is already installed, the wizard checks its deployment and recovery before
reading a fresh inventory. A separate **Reinstall Root? [y/N]** question describes
the replacement; `--yes` never accepts it, and noninteractive installation stops.
Enter leaves the existing deployment unchanged without generating an issue report.
An incomplete deployment must be recovered first, rather than overwritten.

After explicit approval, cytv prepares and validates the replacement bundle locally,
restores LG Home, removes the previous Root through its existing recovery driver,
then verifies removal before archiving its recovery directory on the TV. Root
preferences may be reset; other TV apps stay installed. Recovery archives have names
like `/var/lib/clean-your-tv-root.archive-<random ID>` and are never deleted by this
flow. Retained state from a previously completed removal can be archived without
submitting removal again. If old Root processes remain, restart the TV using its
remote, wait for LG Home, then rerun cytv. The archive guard checks processes,
package/routing/registration absence and completed recovery; it never kills processes
or bypasses a conflict. Interrupted archive submission is reconciled by `cytv status`
using the recorded destination and state identity before installation can continue.
Reinstallation uses a fresh inventory; `--migrate-home` is refused for that flow
so an invalid migration source cannot be discovered only after removing old Root.

No-root replacement refuses an active or ambiguous helper. Press Home three times within two
seconds to stop it before installing again (older Helper: hold Home for two seconds). Installing Root keeps the
ordinary Home files but stops and disables its Helper before activation. `--migrate-home` explicitly imports an existing Home
profile/packaged inventory instead of reading a fresh SSAP inventory:

```sh
./cytv install --host 192.168.1.50 --edition root --identity ~/.ssh/tv_key --migrate-home
```

Before daily use check arrows/OK, short Home, in-app Back and exit confirmation,
volume/pointer, standby/wake and cold boot. Both editions use three short Home presses within two seconds for emergency exit.

<a id="candidate-shared-root-operations"></a>

## Shared Root operations

Root installation and complete removal in the published installer use the shared
on-TV coordinator. The separate CYTV Installer client for Homebrew remains
[unreleased](../homebrew/README.md); its source uses the same coordinator. The normal cytv platform/edition choices,
SSH trust and No-root flow remain. A current verified product can be inspected,
restored and removed across either client without reinstalling or resetting its
profile. Older or uncertain infrastructure is not silently migrated.

Run `cytv status` first after interruption, then use restore/diagnostics as needed.
The offered **Finish Root setup** action verifies completed package/recovery
setup and then performs explicit activation; it does **not** restart an incomplete
worker. The on-TV UI's Continue action is limited to proven final readback. For
other recognized interrupted stages, the source setup CLI provides
[`--operation` plus `--resume`](MANUAL_INSTALL.md#candidate-shared-product-continuation)
using the original stored snapshot and lease. No generic clear-lock, reset or
blind retry is supported. Keep journals and private recovery material.

Homebrew upgrades the separate Installer, not the installed product. System
Updater preparation remains an explicit optional action; complete signed product
updates keep their existing updater. Installer-only deletion leaves the product
installed; use complete-product removal to restore LG routing and clean owned
packages/private startup wrappers while retaining recovery evidence and referenced runtime
slots. See [candidate requirements](INSTALL.md#candidate-on-tv-root-installation).

## Maintenance

```sh
./cytv status
./cytv doctor
./cytv restore
./cytv uninstall
./cytv enable-system-updates --edition root
```

Saved profiles keep subsequent commands short. Multiple profiles show a numbered
selection; `--host`, `--edition`, `--port` and `--identity` select explicitly.
Options work before or after the command. `restore` restores LG Home behavior
without removing applications. `uninstall` restores before requesting removal and
checks application, service and package absence. Root preserves its recovery
evidence, including after removal; retained TV state blocks reinstallation by
design. See [Root rollout](../root-edition/ROLLOUT.md).

`--yes` accepts the install/restore/removal summary only; it never accepts SSH trust. `--non-interactive` rejects local input prompts and requires
previously established host trust and usable credentials (saved/explicit key,
SSH agent or TV passwordless login). It never opens the fallback credential menu.
An encrypted key still needs interactive unlocking. Interactive
TV pairing may still be required for installation; use the wizard for first setup.
`--check-payload` verifies embedded assets without connecting to a TV.

## Enable whole-edition updates (1.1.0)

For Root with an existing trusted root SSH connection, use
`cytv enable-system-updates --edition root`. For the No-root edition on a rooted
TV, use the manual supervisor bootstrap with `--edition no-root` and a root SSH
alias in the linked guide; a cytv No-root profile connects as `prisoner`.
This explicit computer-assisted action provisions the independent System Updater
supervisor and captures the installed rollback baseline. It needs root, Homebrew
services, TV Node.js 8+ and suitable Python 3.9+; eligible missing Python can be
provisioned during setup. An unrooted TV continues using computer updates.
It refuses conflicting legacy transactions, unknown outcomes and existing
supervisor state. An app-only legacy OTA does not install this infrastructure.
See [Root system updates](../root-edition/UPDATES.md) and [No-root updates](UPDATES.md).

To prepare only the pinned runtime download without contacting a TV, run:

```sh
cytv --prepare-python-runtime --data-dir /path/to/private-cache
```

Use the same private data directory for setup. This optional ARMv7 runtime needs
a compatible TV loader/libc and additional staging space; it does not replace
Node.js, root services or input compatibility. [Runtime details](OPTIONAL-PYTHON.md).
Status, doctor, restore and uninstall never download a new interpreter.

<a id="candidate-root-system-updater-replacement"></a>

## Root System Updater replacement

Root installers since 1.5.0 contain System Updater 1.1.2. The explicit
replacement command accepts an installed 1.1.0 or 1.1.1 after verifying its
retained code, owner package, registration and finished recovery state.
With the existing trusted Root connection:

```sh
cytv replace-system-updater --edition root
```

This explicitly replaces only the supervisor, after checking that installation,
rollback and Home resumption are finished. Root packages, launcher storage and
preferences are preserved; the old supervisor state is archived. Normal trusted
connection options apply; confirmation defaults to No (`--yes` accepts this
summary). A matching interrupted replacement resumes with the same bundle;
foreign pending operations and uncertain package outcomes remain blocked. Any
existing legacy Root Updater transaction/backup also blocks replacement, including
a completed one; keep that evidence for review, never delete it to force progress.
See [replacement and recovery](RECOVERY.md#replace-the-root-system-updater-candidate).

## Interrupted operations

A private local receipt is synchronized before installation/removal, and
recovery attempts have separate receipts. A failed command never means a package
was not installed. **Do not delete journals or rerun installation blindly.**

Run `cytv status` first. A No-root installation can be reconciled when expected
installed asset/config hashes and versions match; this verifies files, not active
input handling. Root reconciliation requires the terminal deployment stage and
verified recovery integrity. Verified package absence can reconcile removal.

An incomplete install may be explicitly removed only after the TV installer reports
idle. An uncertain removal is not submitted again. `restore` remains available
and records its result while retaining incomplete-install evidence. If readback is
incomplete, access is denied, or recovery reports a conflict, retain the evidence
and follow the edition's [recovery instructions](RECOVERY.md).

Optional early input restoration is tracked separately. A rejected registration
uses the guarded fallback. Rejection alone does not establish that an older
registration is absent: an EIM input-list readback establishes absence when
available. An unknown EIM result still requires confirmed cleanup before uninstall.

<a id="candidate-root-system-rollback-readiness"></a>

## Root System rollback readiness

With a matching published installer, after a verified Root System rollback reaches a
launcher-readiness timeout with all package installers completed, use the same
saved/trusted Root connection:

```sh
cytv recover-system-rollback --edition root
```

Normal connection options such as `--host`, `--port`, `--identity`, `--data-dir`
and `--non-interactive` remain available. This is a Root-only maintenance command,
not an installation retry. It verifies retained evidence, requires the restored
launcher's genuine authenticated readiness within a fresh 120-second window, and
keeps a durable audit. Unknown installer results or changed/conflicting state stop
recovery. Packages, pinned supervisor code/keys and an explicit Home-off choice
are preserved. Ordinary retries resume the same unexpired attempt without
extending its deadline. After diagnosis, `--new-recovery-attempt` explicitly opens
a new audited attempt only after the old 120-second deadline expires, with no
accepted health receipt and no unknown installer outcome. It archives the entire
old audit under its UUID and hash before creating a fresh UUID/window; it never
automatically chains attempts. Completed recovery is idempotent and does not roll
over. The normal confirmation defaults to No; state checks still apply. See
[the recovery procedure and limits](RECOVERY.md#root-system-rollback-readiness-candidate).

## Report a problem

Every failed connection/install/recovery step prints the error, an
[issue link](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new) and a
private `reports/diagnostic-<id>.json` file to attach. It contains the cytv version,
desktop OS/architecture, edition, action, failed phase, pending action/stage and
stack **file/function/line locations**. It excludes exception text, source lines,
locals, addresses, identity paths, credentials, app lists, environment and raw TV
logs. No report is submitted automatically.

Since 1.2.0 (#51): a definite Luna rejection adds a `luna` object with a fixed
operation category (`package-install`, `package-remove`, `package-status` or
`luna-call`), signed 32-bit numeric `error_code`, `details_error_code` and
`status_value` fields, a boolean `return_value`, and an allowlisted package
`state`. Missing/invalid numbers and results are `null`; unrecognized states are
`unknown`. Decimal numeric strings are normalized to numbers. Raw TV error text,
URIs, package IDs, paths and reply bodies are never exported. The existing
phase (for example `install-helper`) identifies which step failed. This improves
diagnosis without retrying a failed operation or claiming that issue #51's
installation failure is fixed.

Root diagnostics report individual requirement results as `pass`, `fail` or
`unknown` in `tv.root_requirements`. SSH command failures can include a safe
numeric `ssh_command.exit_status`; neither credentials nor raw remote output are
included. A Python failure does not establish that the other Root requirements
passed. Report the actual failed checks, TV model and firmware.

SSAP connection reports can also include a numeric WebSocket close code and an
allowlisted reason such as `tv-not-ready`. Raw close reasons remain excluded.
Pairing and inventory failures explicitly state that installation has not started.

An empty or OS-blocked discovery search is handled by retry/manual entry without
generating an issue report. Unexpected discovery failures use the usual report path.

You can also generate a report explicitly:

```sh
./cytv doctor --report
```

Review the report before posting. Add the TV model and firmware, the steps you
followed, the expected result and actual behavior. The **cytv installer problem**
issue form asks for these details. If reporting from a terminal, remove addresses
and key paths from the command you paste. Keep the full private state and TV
journals locally for recovery; attach only the diagnostic report.

## Private data

Default local profile locations:

| Desktop | Directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\CleanYourTV` |
| macOS | `~/Library/Application Support/CleanYourTV` |
| Linux | `$XDG_DATA_HOME/cleanyourtv`, default `~/.local/share/cleanyourtv` |

Profiles are isolated by TV address, SSH port and edition. Keys and pairing tokens
are saved as private files; POSIX files use mode 0600 and directories 0700. On
Windows the default location inherits the user's profile ACL. If using `--data-dir`,
choose a directory accessible only to your account. Do not publish profile folders,
pairing keys or device inventories. No credential is placed in a subprocess command
argument. Error output never includes an unfiltered remote exception/traceback.

The SSH transport pins host keys. The SSAP and icon connections use the TV's local
self-signed HTTPS endpoint, as the existing installer does; use a trusted LAN.
Icon retrieval is limited to the selected TV host, has size/time limits, refuses
redirects and falls back to an embedded icon on failure.

## Build from source

Developers need Git, Python 3.11+ and the build requirements. Zig is used locally
to compile the existing ARM32 helper. Node.js 20.19+ and npm build the compatible
TV web assets; run `npm ci` before the commands below. See [TV web build](TV-WEB-BUILD.md).

```sh
python -m venv .venv-cytv
# macOS/Linux:
.venv-cytv/bin/python -m pip install -r cytv/build-requirements.txt
.venv-cytv/bin/python scripts/build-cytv.py
# Windows:
.venv-cytv\Scripts\python -m pip install -r cytv\build-requirements.txt
.venv-cytv\Scripts\python scripts\build-cytv.py
```

Output is `dist/cytv` or `dist/cytv.exe`. Build each target natively; PyInstaller
does not turn a macOS executable into a Windows/Linux executable. The workflow
does this in four separate jobs. Use a fresh virtual environment: build requirements
select binary `cryptography` wheels with their own static OpenSSL rather than a
source build that can conflict with Python's bundled `libssl` on Intel macOS.
An already installed source build is not replaced by pip's binary-only option;
recreate the environment if the runtime check fails.

Both console and GUI builders run `--check-payload` and the internal offline
`--check-runtime` probe on the frozen executable before packaging succeeds. The
runtime probe loads Python TLS and SSH dependencies, signs/verifies RSA and
Ed25519 data, encrypts/decrypts AES-GCM data and derives a bcrypt key. Dependency
load errors fail the build with their original exception; these checks do not
connect to a TV, read connection profiles or publish a release. GUI startup smoke
remains a separate check. A focused Intel macOS PR workflow freezes both actual
entrypoints without a TV payload and runs the same probe before integration.
This fix for issue #93 shipped in 1.4.0; the original device result remains unconfirmed.

For source development, `python scripts/build-cytv.py --payload-only` prepares the
embedded assets, then `python -m cytv` runs the same wizard. Public payload sources
are limited to tracked application/service files and the existing Root builder's
explicit source inventory; ignored developer state is excluded. Checksums detect
payload corruption, not publisher identity. Updating `cytv` currently means
downloading a newer executable; this CLI has no automatic update channel.

References: [LG CLI protocol and commands](https://webostv.developer.lge.com/develop/tools/cli-dev-guide),
[LG Connect SDK webOS discovery target](https://github.com/ConnectSDK/Connect-SDK-Android-Core/blob/master/src/com/connectsdk/service/WebOSTVService.java),
[PyInstaller standalone operation](https://pyinstaller.org/en/stable/operating-mode.html).

For older No-root Helper releases (through 0.6.13), use the previous emergency gesture: hold Home for about two seconds. The updated Helper uses three short Home presses within two seconds.

## Release version checks

The production builder reads `release-versions.json` and rejects mismatched Home,
Helper, Root or cytv versions, including packaged service metadata. Build from the
release commit with `python scripts/build-cytv.py`; no separate local source tree
is required. The wizard has no trial or Keep step.

## Home button diagnostics

The console executable can collect the existing opt-in Home Helper recording
using its own saved No-root TV connection:

    ./cytv home-diagnostics --edition no-root

Use the platform-specific console executable name on Windows. With multiple
saved No-root connections, select the affected TV. With no saved connection,
follow normal address, trust and Developer Mode prompts; do not copy private
Android profile/key files to a computer. The Helper must already be running.
Press Home once when prompted, leave the remote untouched for the recording,
then attach the generated JSON after reviewing it. Recording does not restart
Helper or change the saved Home choice; standby and cold boot remain separate
acceptance checks.

Home settings diagnostics (published in 1.4.0): a failed status read is shown
as unknown, with Change Home hidden until a valid response. This avoids showing
an unconfirmed off switch. It does not repair a firmware denial or unavailable
request-file transport, prove that Helper stopped, or automatically start it.

<a id="unreleased-optional-wam-cache-cleanup"></a>

## Optional WAM cache cleanup

`cytv clean-wam-cache --edition root` estimates Cache/Code Cache usage and available
`/var/lib` space, offers manual guidance and requires default-No confirmation.
It requests only `cache` and `codecache` through the TV's native WAM API; it does
not delete files itself. Session Storage and other app state are excluded.
`--yes` does not authorize cleanup; noninteractive mode and pending local operations
are refused. Cache rebuilding may slow the next app launch. No reboot, automatic
retry or setup resume occurs. See [scope, manual maintenance and evidence](WAM-CLEANUP.md).
Published installers do not include this action yet.

## Candidate: redirected Windows output and POSIX payloads (#107)

The next candidate preserves the stream's selected encoding and writes unsupported
console characters as backslash escapes (for example, `\u041f`) instead of failing
with `UnicodeEncodeError`. UTF-8 output keeps the original localized text. This
applies to help, errors and normal CLI output; it does not change TV settings or
saved JSON data. A UTF-8 terminal/log remains preferable for readable localized text.
These source changes are not a claim about already published installers.

Windows source checkouts use LF for text through `.gitattributes`; binary assets
remain unchanged. `--check-payload` verifies file hashes and rejects CR characters
in loose or IPK-contained `.sh` scripts. It rejects a defective build rather than
rewriting a signed or published package. Rebuild installers from a fresh checkout;
do not edit installed recovery scripts or retained transaction files.

The separate Root routing/recovery incompatibility on BX/webOS 5 remains unresolved.
See the [investigation record](development/ISSUE-107-WINDOWS.md).
