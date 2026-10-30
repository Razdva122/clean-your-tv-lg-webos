# Manual installation of No-root and Root without cytv

[Documentation](README.md) · [Graphical installation](INSTALL.md) · [Help and feedback](FEEDBACK.md)

This is an advanced reference. Use the graphical installer for the normal setup path.
No-root and Root are equal options for different TV setups. Choose No-root for LG Developer Mode or Root for existing root SSH access. Compatibility and test coverage remain specific to each edition.

This guide uses commands from the source repository: the webOS CLI for No-root
and Python/OpenSSH for Root. You do not need to run `cytv` or `install.sh`.
Run every command **on your computer** unless stated otherwise.
The addresses and names below are examples; replace them with your own.

Hardware checks remain scoped to their actual devices and artifacts. Read
[requirements and known limits](COMPATIBILITY.md) and [current release evidence](history/README.md)
before using manual commands. Do not treat an old validation record as acceptance
of your TV or a new source checkout.

## 1. Choose a path and prepare the tools

| Requirement | No-root | Root |
| --- | --- | --- |
| TV access | LG Developer Mode, Key Server, SSH `prisoner:9922` | Existing root, a trusted SSH host key, authentication without an interactive password |
| On the TV | Active Developer Mode session; TV Node.js 0.10.25+ for the source/test Helper (published installers: 0.12.2+); local control access | Python 3.9+ (manual commands assume `/usr/bin/python3`), Node.js 8+, `/usr/bin/luna-send`, Homebrew services, `/media/developer/apps`, a compatible ARM32 Magic Remote input interface |
| Ready-made artifacts | A personalized Home IPK and, optionally, a Helper IPK | The **entire** Root bundle: IPK, `setup.py`, support files, `runtime/`, manifests and checksums |
| Build from source | Git, Python 3.9+ with pip/venv, Node.js 20.19+ with npm, webOS CLI 3.2.6; Zig 0.14.1 for Helper | Git, Python 3.9+, Node.js 20.19+ and npm for compatible web assets; no webOS CLI/Zig |
| Additional tools for the full test suite | Bash, Node.js, Python 3, a C compiler named `cc` | The same tools; the build and SSH installer themselves do not require Bash |
| After installation | The computer can be off; Developer Mode must remain active; Helper depends on local networking | The computer can be off; root access and recovery services must remain available |

The Root installer **does not obtain root**, flash firmware or enable Developer
Mode. Use No-root if your TV is not rooted. Do not install Developer Mode over
an existing root setup to follow the No-root commands. Obtaining root and
establishing support for a particular firmware are outside this guide.

### macOS, Linux and Windows

- **macOS/Linux:** enter the `bash` blocks below in Bash or a compatible terminal.
  `.venv` requires pip and the venv module; some Linux distributions package
  venv separately. The project commands do not require `sudo`.
- **Windows, No-root:** `scripts/build.sh` and `scripts/configure-tv.sh` are Bash
  scripts that use Unix utilities. Run the complete procedure in WSL with
  Linux versions of Python/Node/CLI/Zig installed inside WSL. PowerShell alone
  cannot execute these scripts. The project has not validated WSL/Windows
  installation on a real TV. Check that WSL can reach the TV's IP and keep
  Windows and Linux CLI profiles and keys separate.
- **Windows, Root:** you can run `build.py` and `setup.py` with native Python 3.9+
  from PowerShell. `ssh.exe` and `scp.exe` must be on PATH, and `scp` must support
  **`-O`**: the driver uses the legacy SCP protocol. The TV also needs a working
  root SCP server. Native Windows installation still needs separate device
  validation. Replace `python3` with `py -3` in Python commands if that is how
  you invoke Python. Create directories with `New-Item -ItemType Directory`.
  Quote file paths in PowerShell. Root does not require activating `.venv`.
  The full `bash scripts/test.sh` requires Bash and a C compiler.

Downloading the sources and tools initially requires Internet access.
Installation requires the computer to reach the TV on a trusted local network;
a guest Wi-Fi network with device isolation will not work. Keep SSH/SSAP keys,
CLI profiles, private reports, app inventories and personalized IPKs private.

### Source checkout

```bash
git clone https://github.com/Razdva122/clean-your-tv-lg-webos.git
cd clean-your-tv-lg-webos
```

If you already have the repository, change to its root directory. Use your
chosen verified source revision and retain its identifier (`git rev-parse HEAD`)
with the packages. Older instructions may list different versions; the new
Home IPK's name follows `launcher/appinfo.json`.

## 2. No-root: prepare the TV

1. Install the official **Developer Mode** app, sign in to your LG Developer
   account, enable Developer Mode and complete the restart requested by the TV.
2. Open Developer Mode, check the remaining session time and enable
   **Key Server**. Note the local IP and keep the passphrase screen open until
   you have retrieved the key.
3. The computer and TV must be able to reach each other. Developer Mode SSH
   uses port **9922**. Control pairing for the app inventory and Helper uses
   a separate SSAP connection at `wss://TV:3001`, approved on the TV screen.

For account and session setup, see [LG's official guide](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app).
Monitor the official timer: Developer Mode expiry can lead to removal of
sideloaded apps. Built-in Beta renewal is off by default, and actual renewal
has not yet been validated. [Beta details](DEVELOPER-MODE-BETA.md).

## 3. No-root: tools and two separate pairings

From the repository root, in Bash on macOS/Linux/WSL:

```bash
python3 -m venv .venv
npm ci --ignore-scripts --no-audit --no-fund
. .venv/bin/activate
python3 -m pip install -r requirements.txt 'ziglang==0.14.1'
export ZIG="$(python3 -c 'from pathlib import Path; import ziglang; print(Path(ziglang.__file__).parent / "zig")')"
npm install --prefix build/tools --no-audit --no-fund '@webos-tools/cli@3.2.6'
export PATH="$PWD/build/tools/node_modules/.bin:$PATH"
node --version
python3 --version
"$ZIG" version
```

Node.js 20.19+ and Zig **0.14.1** are required. For Termux/Android, supply a working Zig 0.14.1 executable instead of installing
the `ziglang` Python distribution; see [Termux setup](INSTALL.md#termux--android).
For Home alone, without Helper,
you can omit `ziglang` and the `ZIG` variable. In a new terminal, reactivate
`.venv`, add the local CLI to PATH and set `ZIG` again.
You can also install the webOS CLI separately using [LG's documentation](https://webostv.developer.lge.com/develop/tools/cli-dev-guide),
but the pinned local version makes these commands more reproducible.

### Developer Mode SSH

Start interactive setup:

```bash
ares-setup-device
```

Add a profile named **`lgtv`** with your TV's IP, port **9922**, username
**prisoner**, and no SSH password. If that profile name already points to
another TV, choose another name and replace `lgtv` in every subsequent command.
Then run:

```bash
ares-novacom -d lgtv --getkey
ares-device --system-info -d lgtv
```

Enter the passphrase **shown in Developer Mode** when the CLI prompts.
This retrieves the Developer Mode key; it is not a root password.
The CLI stores the profile and key in its user configuration. Do not include
`ares-setup-device --listfull` output in shared logs: saved profiles may contain
passphrases.

### SSAP: app inventory and the Helper key

```bash
export TV_HOST=192.168.1.50
python3 sync-apps.py "$TV_HOST" --list
python3 sync-apps.py "$TV_HOST"
```

Replace the IP. Approve the pairing request **on the TV**. The script creates
`.lgtv-key.json`, `launcher/apps.js` and `launcher/icons/`. Check the number of
synced apps and any warnings: an app is skipped if its icon cannot be downloaded.
`--list` only prints the inventory; the build needs the second invocation,
without `--list`.

Set `dockApps`, `hiddenApps` and `columns` in `launcher/config.js`, using app IDs
from the list above. Hiding a tile does not uninstall an app. Keep a private
copy of config, apps and icons before making further changes; do not put it in
a public release. Do not run project scripts with `bash -x`: the Helper
configuration transfer command contains the pairing key encoded in Base64.

## 4. No-root: build, install and enable

### Home with Helper

```bash
bash scripts/build.sh
```

Optional full checks before building:

```bash
python3 -m pip install -r cytv/requirements.txt
bash scripts/test.sh
```

These dependencies support the shared installer's tests; `cytv` itself is not
run. The tests also require `cc`. The build produces `dist/SHA256SUMS`,
`dist/com.local.nativehome_0.6.19_arm.ipk` and the Home IPK. The 1.1.0
source uses Home **1.4.0**, Helper **0.6.19** and Root **0.2.0**, as recorded
in [`release-versions.json`](../release-versions.json). For another source revision,
check the Home manifest and use the matching generated package filenames:

```bash
python3 -c 'import json; print(json.load(open("launcher/appinfo.json"))["version"])'
```

Keep known-working packages outside `dist/` before your next build.
To verify `dist/SHA256SUMS`, run `sha256sum -c SHA256SUMS` from `dist/` on
Linux/WSL, or `shasum -a 256 -c SHA256SUMS` on macOS. Checksums establish
integrity; trust in the source is a separate requirement. The list may include
older IPKs left in `dist/`.

Install Helper, then the **exact** new Home IPK, adjusting the version if needed:

```bash
ares-install -d lgtv dist/com.local.nativehome_0.6.19_arm.ipk
ares-install -d lgtv dist/com.gathin.tvhome_1.4.0_all.ipk
TV_HOST="$TV_HOST" DEVICE=lgtv bash scripts/configure-tv.sh
ares-launch -d lgtv com.local.nativehome
```

`configure-tv.sh` uses the saved SSAP key and app inventory. It transfers Helper
settings, verifies each file's SHA-256 and permissions, atomically replaces
each file, and requests EIM input registration for early Home restoration.
The TV needs `mktemp`, `base64`, `sha256sum` and `stat -c`. Each file is verified
separately; the two files are not one transaction. If EIM registration does not
return `returnValue: true`, the script prints a warning: startup relies on the
fallback path, which can briefly show LG Home.

Launching Helper explicitly enables Home interception and opens Home.
For emergency access, assign Home to an available numbered Quick Access key
through the TV menu; on supported remotes, hold **0** to open that menu.

### Home alone, without Home interception or Helper configuration

After syncing your apps:

```bash
mkdir -p dist
python3 scripts/tv_web_build.py --input launcher --output build/home-app
ares-package build/home-app renewal-service -o dist
ares-install -d lgtv dist/com.gathin.tvhome_1.4.0_all.ipk
ares-launch -d lgtv com.gathin.tvhome
```

This does not require Zig or Helper. Open Home from LG Apps or Quick Access;
the Home button retains its system behavior. Without Helper, there is no
Helper interception, app-exit monitoring or automatic return as described above.
`ares-package` alone does not generate the project's `SHA256SUMS` file.

### No-root checks and recovery

Test arrows and held arrows, OK, Back and Cancel inside apps, volume, pointer
and wheel. A short Home press should open Home while Helper is active.
Test standby/wake and cold boot separately.

- **Press Home three times within two seconds** to stop Helper and return to LG Home.
  The stop flag persists and prevents automatic startup; this does not reset
  your settings.
- To resume, open **Home Helper**. Command: `ares-launch -d lgtv com.local.nativehome`.
- Opening Home alone does not clear the emergency stop. Holding Back does
  not stop Helper either. If a fault recurs, leave Helper stopped.

Check packages and the startup service; these commands do not test physical buttons:

```bash
ares-install -d lgtv --list
ares-novacom -d lgtv --run "luna-send-pub -n 1 luna://com.local.nativehome.service/status '{}'"
```

Inspect `returnValue`, `blocked` and `state` in the service reply. The query
requires Helper/service to be installed; an installed package alone does not
prove that interception is working. See [recovery](RECOVERY.md) and
[compatibility](COMPATIBILITY.md).

## 5. Root: prepare trusted access

You need **existing working root SSH access**. Configure a separate OpenSSH
alias on your computer in `~/.ssh/config` (Windows:
`%USERPROFILE%\.ssh\config`). Example:

```sshconfig
Host my-tv
    HostName 192.168.1.50
    User root
    Port 22
    IdentityFile ~/.ssh/tv_root_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking yes
```

Replace the path with your **existing** key for trusted root access; the file
name above is only an example. Its public key must be authorized on the TV.
Do not copy the private key to the TV. Verify the host-key fingerprint through
existing trusted access or a trusted backup record, then store it in
`known_hosts`. Fetching a fingerprint over the network alone does not establish
the server's identity. Investigate changed keys rather than bypassing the check
with `StrictHostKeyChecking=no`.

`setup.py` always uses `StrictHostKeyChecking=yes`, `BatchMode=yes` and
`ConnectTimeout=10`; it cannot prompt for a password. Load a passphrase-protected
key into your SSH agent beforehand. Check access to the required tools:

```bash
ssh -V
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes my-tv 'id -u; /usr/bin/python3 --version; test -x /usr/bin/luna-send && echo LUNA_OK'
python3 root-edition/doctor.py --ssh my-tv --output doctor-report.json
```

The TV requires Python 3.9+ (including required modules), Node.js 8+,
`luna-send`, Homebrew services and supported ARM32 remote input. The manual
commands below assume a suitable `/usr/bin/python3`. For eligible ARMv7 TVs
without one, use cytv's verified on-demand [Python provisioning](OPTIONAL-PYTHON.md)
and its retained interpreter bindings; do not create a system Python symlink.
Manual drivers do not automatically download Python. Status, recovery and removal
must use the installation's verified interpreter, including after an interruption.

The session must use UID 0. UID 0 and a doctor report alone **do not prove**
input compatibility, root persistence after reboot or working recovery.
Doctor reads state without obtaining root or changing settings. It refuses
to overwrite an existing report; use a new filename for another check.
For a nonstandard SSH port, explicitly add `--port 2222` to doctor: it passes
port 22 by default even if the alias specifies another port. `setup.py` uses
the port configured in the alias.

The **setup.py `--ssh` option accepts only one alias name**, such as `my-tv`,
without `root@`, `:port`, spaces or SSH arguments. An optional identity key can
be specified with `--identity /absolute/path/to/key`; add this flag to every
setup invocation that needs it. Doctor has no `--identity` flag; use
`IdentityFile` or your SSH agent.

## 6. Root: build or obtain a complete bundle

From the source root; this operation does not connect to the TV:

```bash
mkdir -p build
npm ci --ignore-scripts --no-audit --no-fund
python3 root-edition/build.py --output build/root-candidate --version 0.4.0
```

The parent directory must exist, and `build/root-candidate` must be **new**, with
no symlinks along its path. Choose a different name for the next build.
The 1.3.0 source bundle contains `com.cleanyourtv.root.preview_0.4.0_all.ipk`, `setup.py`,
`deploy.py`, `runtime/`, `bundle.json`, `release.json`, `SHA256SUMS` and the
other required Python support files. Retain the entire directory. Installing
the IPK alone through `ares-install` or another manager does not provision recovery.

If you obtain a ready-made bundle, extract it completely to a trusted local
directory and use its `setup.py`. Verify the IPK using `SHA256SUMS` from the
bundle directory, as in the No-root section. Installation additionally checks
**every** file against `bundle.json`. Do not edit the bundle or mix files from
different release candidates. The `hardware_validated: false` and
`public_release_ready: false` fields reflect preview maturity.

With a development environment available, you can run the full
`bash scripts/test.sh`; it requires Bash, Node.js, `cc`, and
`python3 -m pip install -r cytv/requirements.txt` for the shared installer's tests.
For the Root Python checks alone, run
`python3 -m unittest discover -s root-edition/tests`.
Offline tests do not validate buttons or boot behavior on your TV.

### Candidate source versus published bundles

The following shared-product commands are included in **1.3.0**. Homebrew Installer publication is separately gated.
Use the complete matching bundles from this revision. Published tagged bundles
retain their matching drivers and procedure; these new flags do not retrofit
old retained infrastructure. No Homebrew catalog or new public assets are
available from these commands. Historical Root 0.2.0 C3 acceptance above remains
limited to those original artifacts.

### Where Root gets its app inventory

A source build contains an empty generic inventory. Normal shared-product setup
uses the fixed on-TV app discovery module to personalize it locally before
installation. cytv can instead supply its existing host-personalized inventory.

For a **fresh installation**, `--migrate-packaged-home` explicitly imports a
validated Home Updater profile or installed ordinary Home's packaged
`apps.js`, `config.js` and icons. It does not migrate browser/localStorage or
unknown retained infrastructure. The source is read-only; installed preference
hashes are retained in `/var/lib/clean-your-tv-root/personalization.json`.
Invalid/missing migration data stops before product mutation. Do not edit an IPK
or bypass bundle checks to personalize it.

## 7. Root: first installation, checks and persistent activation

Only for a first compatible installation without unknown/retained state, build
Root Updater as well as Root. Use fresh output directories and record an explicit
32-character hexadecimal operation identifier so later status can find the request:

```bash
python3 root-edition/build_updater.py --output build/root-updater
export CYTV_OPERATION=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
python3 build/root-candidate/setup.py install --ssh my-tv --bundle build/root-candidate --updater-bundle build/root-updater --operation "$CYTV_OPERATION"
python3 build/root-candidate/setup.py status --ssh my-tv --bundle build/root-candidate --updater-bundle build/root-updater --operation "$CYTV_OPERATION"
```

The install command returns a pending receipt from a detached worker. Repeat the
same shared `status` command until **`state: complete` and `current: true`** before
System Updater preparation or activation below. While `pending`, wait and inspect;
`recovery_required`, `conflict` or `current: false` stops the sequence for diagnosis.
Do not rerun install automatically or replace the original operation UUID.

Retain the actual operation ID privately; do not generate another to retry an
uncertain request. Add `--migrate-packaged-home` only for the deliberate fresh
preference import above. Normal `install` requires **both** `--bundle` and
`--updater-bundle`, installs Root Home/recovery and Root Updater, and captures the
matching baseline. Package completion requires exact terminal evidence and
verified installed bytes. **Setup does not enable Home or clear emergency/off.**

An alternative source entry point reviews the same full-product request:

```bash
python3 root-edition/setup_updater.py --bundle build/root-updater --baseline build/root-candidate --ssh my-tv
```

Without `--apply` it prints the plan without TV mutation. With `--apply --operation "$CYTV_OPERATION"` it submits shared Root + Root
Updater setup; do **not** run both entry points to install twice. The
`--component-only` flag on either setup tool is explicitly advanced component
recovery, not normal setup, a reinstall shortcut or infrastructure migration.
System Updater preparation is a separate explicit optional action, described in
[Root updates](../root-edition/UPDATES.md).

### Candidate: shared product continuation

After interruption, inspect status first and preserve the original request,
lease, snapshots, logs and interpreter binding. Switching between cytv and the
TV installer requires no reset. cytv's Finish Root setup only verifies completed
setup and activates Home; it does not restart an incomplete worker. The TV UI
offers Continue only for proven final-readback installation/removal states.

For additional recognized stages, the **same source setup CLI** can explicitly
continue the original verified snapshot using its operation ID:

```bash
python3 build/root-candidate/setup.py install --ssh my-tv --bundle build/root-candidate --updater-bundle build/root-updater --operation "$CYTV_OPERATION" --resume
```

This reuses the original stored worker snapshot and lease, validates its binding,
and continues only recognized proofs. It does not authorize a new operation or
replay a package submission whose outcome is unknown. Removal continuation uses
`uninstall` with both bundles, its original removal operation ID and `--resume`.
Status/restore/diagnosis remain the next steps when proof is insufficient. Never
delete journals, clear locks or overwrite recovery files to force progress.

If the old No-root Helper is running, press Home three times within two seconds to stop
**that helper**, then release all buttons. Root refuses activation while Helper
is active or an ambiguous old PID marker exists. Do not manually delete its
`blocked` or PID files, or run two input handlers together.

After the original shared setup status confirms `state: complete` and `current: true`,
for persistent mode, open **Home Root → Home settings** and turn **Change Home** on, or run:

```bash
python3 build/root-candidate/setup.py enable --ssh my-tv
python3 build/root-candidate/setup.py status --ssh my-tv
```

**No trial, countdown or Keep button is required.** `enable` records persistent
startup intent after automatic input, guardian and effective-routing checks.
Failed activation restores LG Home. The diagnostic `trial`, `intent-trial` and
`confirm` commands in `--help` are not the normal activation path.

In `status`, inspect the actual Home destinations (`effective`), journal,
`guardian_active`, `recovery.integrity_verified` and saved `intent`. With Root
active, the destinations should point to `com.cleanyourtv.root.preview`, recovery
integrity should be verified and the guardian should be running.
`returnValue: true` alone does not replace these checks or testing the remote.
First test arrows/OK, short Home, Back/Cancel and a confirmed app exit, then
the emergency exit. Test standby and cold boot separately; a successful
software reboot does not establish those behaviors.

A confirmed normal shutdown retains the selected Root profile for startup.
Startup recovery reconciles the old transaction before reactivation with fresh
protections and normal-boot checks. Use webOS power controls; direct
`systemctl reboot` can be classified as an input fault and disable Home control.
A fault, failsafe or explicit exit disables persistent intent; the next
activation requires an explicit `enable`.

## 8. Root: exit, recover and return to No-root

- **Three short Home presses within two seconds**, releasing the button between
  presses, request emergency restoration to LG Home independently of the web UI.
- In **Home settings**, turn **Change Home** off to restore persistent LG routing.
  **Open LG Home** only visits LG Home once; it does not disable Root. Older
  builds may offer **Return to LG Home → Confirm return** or **Exit Root mode**.
- Holding Home **is not** the Root emergency gesture; it can trigger an LG
  system action such as magnification.

From your computer:

```bash
python3 build/root-candidate/setup.py restore --ssh my-tv
python3 build/root-candidate/setup.py status --ssh my-tv
```

After restoration, verify stock Home in the effective routes, no active
guardian and disabled Root intent. The tested baseline uses
`com.webos.app.home` as stock Home. If a conflict or error occurs, retain access
and journals, stop activation attempts and leave the override/state intact.

If the local bundle is unavailable but root SSH and the installed runtime
are intact, you can invoke the same recovery directly:

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes my-tv '/usr/bin/python3 /var/lib/clean-your-tv-root/runtime/cli.py restore'
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes my-tv '/usr/bin/python3 /var/lib/clean-your-tv-root/runtime/cli.py status'
```

Exiting does not remove root, uninstall apps or resume the old Helper.
Only after verified restoration, open Home Helper if you want No-root again.

## 9. Update, remove and reinstall

### No-root

Before updating, stop Helper with three short Home presses within two seconds and save the old IPKs and your
personal apps/config/icons. Update your chosen sources, repeat sync and build,
install Helper → Home, run `configure-tv.sh`, then explicitly launch Helper.
**Do not uninstall first**: removal can erase app data and tile ordering.
State preservation across every firmware/installer combination is not guaranteed,
so repeat Helper configuration. For rollback, use your saved verified packages
and their recovery instructions.

For complete removal, stop Helper first, then run:

```bash
ares-novacom -d lgtv --run "luna-send-pub -n 1 luna://com.webos.service.eim/deleteDevice '{\"appId\":\"com.gathin.tvhome\"}'"
ares-novacom -d lgtv --run "luna-send-pub -n 1 luna://com.local.nativehome.service/disable '{}'"
ares-install -d lgtv --remove com.local.nativehome
ares-install -d lgtv --remove com.gathin.tvhome
```

Verify `returnValue: true` for EIM removal and service disabling; resolve errors
before continuing. Remove Quick Access assignments through the TV menu.
For Home alone, without Helper or its configuration, you only need to remove
Home and your Quick Access assignment. See [No-root maintenance](MAINTENANCE.md).

### Root

Root supports compatible signed edition release sets through Settings after
[updater setup](../root-edition/UPDATES.md). The unreleased normal source setup
above includes Root Updater; published tagged bundles retain their own matching
separate procedure. System Updater is optional and requires explicit preparation
before whole-edition updates. Homebrew upgrades CYTV Installer only, not product
components. `setup.py` has no manual
`reinstall` command. Do not install a new IPK over a live runtime: the package,
recovery files, manifests and journals must match. Retain the original bundle
and private backups outside the TV.

For the unreleased shared-product flow, complete removal uses both verified
bundles and a new removal operation ID (distinct from the install ID):

```bash
export CYTV_REMOVE_OPERATION=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
python3 build/root-candidate/setup.py uninstall --ssh my-tv --bundle build/root-candidate --updater-bundle build/root-updater --operation "$CYTV_REMOVE_OPERATION"
python3 build/root-candidate/setup.py status --ssh my-tv --bundle build/root-candidate --updater-bundle build/root-updater --operation "$CYTV_REMOVE_OPERATION"
```

Removal also returns a detached pending receipt. Repeat only the shared status
command with the original removal UUID until `state: complete` and `current: true`.
Pending/recovery/conflict stops any subsequent setup; do not submit removal again
automatically or infer completion from package/process absence.

It restores LG Home, verifies ownership and removes the project product packages,
owned registrations and private startup wrappers. Recovery/archive evidence and referenced
Python slots remain independently retained. Deleting CYTV Installer itself from
LG/Homebrew removes only Installer; it does not perform complete-product removal.
Direct component deletion is also distinct and still needs physical acceptance.
The following older/component recovery details do not replace this full request.

If Root Updater is installed, retain its state and follow the
[Root update/recovery guide](../root-edition/UPDATES.md) before replacing its
pinned recovery runtime. The advanced Root Home component-only removal sequence is:

```bash
python3 build/root-candidate/setup.py restore --ssh my-tv
python3 build/root-candidate/setup.py status --ssh my-tv
python3 build/root-candidate/setup.py uninstall --ssh my-tv
```

Proceed to uninstall only after verified restoration. Uninstall first restores
Home, removes its own permissions/registrations/startup hook, waits for a terminal
removal event and verifies that its app, service and package directories are
absent. It does not remove or start ordinary Home/Helper.

**State at `/var/lib/clean-your-tv-root` is deliberately retained**, including
removal and recovery evidence. This blocks the next manual `install` even if
the package is already removed. Repeating the command, running `rm -rf` or
replacing the runtime does not resolve `Candidate or state already exists`.
After removal, some recovery registrations are already gone, so the old
`status` command may no longer report valid recovery; that is not a reason
to resubmit removal.

Since 1.2.0 (#55): a deployment interrupted at `payload-verified`,
`personalization-starting`, `personalization-complete` or
`provision-apply-starting` can use the normal `uninstall` command even when
provisioning never created its snapshot. The driver verifies the early journal
and absence of provisioning evidence, restores Home, skips only the inapplicable
LS2 rollback, then requires terminal package removal and directory absence. An
explicit `provisioning_not_started: true` receipt survives interrupted cleanup.
The current cytv reinstall flow can archive that verified retained state using
its normal process, routing and registration guards; recovery evidence is kept.
Missing snapshots in later or conflicting states still stop cleanup. This
behavior requires the new driver; do not overwrite an older retained runtime to
retrofit it. Existing incomplete installations need review of their own state.
The OLED Flex recovery-service startup failure in #55 remains unresolved; this
change does not establish device compatibility or justify another blind install.

Before preparing another installation, all of these conditions are required:
confirmed terminal removal, absence of all three candidate directories,
verified stock routes, disabled intent, no running guardian/input processes,
and an **off-TV** copy of state/journals and the old bundle. Archiving state
and freeing its active path require review of that specific state under the
[current rollout procedure](../root-edition/ROLLOUT.md). Manual `setup.py` has
no built-in command to prepare reinstallation safely. A universal directory
rename or deletion command would be unsafe here. This is separate from the
reinstallation path provided by `cytv`.

A timeout or SSH disconnect during install/uninstall can leave the outcome
unknown. Do not retry blindly. Retain remote staging at
`/tmp/clean-your-tv-root-*`, `/var/lib/clean-your-tv-root/deploy.json`, the routing
journal and the error output. You can read the deployment journal without
changing the TV:

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes my-tv 'cat /var/lib/clean-your-tv-root/deploy.json'
```

Use recovery if the runtime is already installed and indicates that recovery
is possible. Preserve conflict evidence for investigation. Do not remove
foreign profiles or whole system directories, and do not treat acceptance
of an install/removal request as proof of its final outcome.

## 10. Common reasons a step stops

| Symptom | Check |
| --- | --- |
| `ares-*` not found | The current terminal's PATH includes `build/tools/node_modules/.bin` |
| No-root cannot retrieve its SSH key | Developer Mode/Key Server, the correct IP and `prisoner:9922`, the passphrase shown on the TV |
| No SSAP pairing or apps | On-screen approval, access to `3001`, `.lgtv-key.json`, icon download errors |
| Helper did not resume | Open Helper itself or select Resume; opening Home does not clear the emergency stop |
| Root SSH prompts for a password or refuses access | Alias, known_hosts, IdentityFile/SSH agent, authorized root public key; BatchMode is required |
| Root install fails at `scp -O` | Local OpenSSH supports `-O` and SCP works on the TV; do not silently substitute another protocol |
| Root install/migration stopped | Retained deploy journal, profile source, pre-existing candidate/state; retrying is not a fix |
| Root enable refuses activation | Old Helper is stopped, all buttons are released, recovery integrity and input compatibility pass |
| TV works after setup but not after boot | Check the edition and stop/intent state; test standby, software reboot and cold boot separately; preserve the protections |

Further reading: [edition comparison](EDITIONS.md),
[Root installation and activation commands](../root-edition/ROLLOUT.md),
[Root hardware evidence and open limits](../root-edition/RELEASE-ACCEPTANCE.md).

For older No-root Helper releases (through 0.6.13), use the previous emergency gesture: hold Home for about two seconds. The updated Helper uses three short Home presses within two seconds.
