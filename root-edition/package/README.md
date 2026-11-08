# Build a Root source bundle

Build on the host with Python 3; the output directory must not exist:

```sh
python3 root-edition/build.py --version "$(python3 -c 'import json; print(json.load(open("release-versions.json"))["root"])')" --output /absolute/path/to/new-candidate
```

The bundle contains an isolated `com.cleanyourtv.root.preview` IPK, its public-source file hashes, the recovery runtime, and host/device drivers. `bundle.json` covers every distributed support/runtime file. `SHA256SUMS` covers the IPK. No TV connection occurs during build. A source build requires its own exact-artifact validation; see
[1.4.0 evidence](../../docs/RELEASE-1.4.0-ACCEPTANCE.md).

These are **unreleased source-candidate** instructions, distinct from published
tagged bundles. For a later supervised TV session, build the matching Root Updater
bundle, retain both whole directories, and use an explicit preconfigured OpenSSH
alias with its host key already trusted:

```sh
python3 root-edition/build_updater.py --output /absolute/path/to/new-updater
export CYTV_OPERATION=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
python3 /path/to/candidate/setup.py install --ssh television --bundle /path/to/candidate --updater-bundle /absolute/path/to/new-updater --operation "$CYTV_OPERATION"
python3 /path/to/candidate/setup.py status --ssh television --bundle /path/to/candidate --updater-bundle /absolute/path/to/new-updater --operation "$CYTV_OPERATION"
# Repeat the original UUID status until state=complete AND current=true before enabling.
python3 /path/to/candidate/setup.py enable --ssh television
python3 /path/to/candidate/setup.py restore --ssh television
export CYTV_REMOVE_OPERATION=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
python3 /path/to/candidate/setup.py uninstall --ssh television --bundle /path/to/candidate --updater-bundle /absolute/path/to/new-updater --operation "$CYTV_REMOVE_OPERATION"
```

The install command returns a detached pending receipt. Repeat only status with
the original UUID; pending/recovery/conflict stops subsequent steps. Do not retry
installation automatically or infer completion from shell exit.

`--identity /path/to/key` is optional. The scripts require strict host-key checking and batch authentication. Device operations require root, suitable Python 3.9+, TV Node.js 8+, Homebrew services,
the webOS Luna tool, the developer-app directory and supported ARM32 remote input.
Manual drivers do not provision Python; cytv can supply the optional pinned ARMv7
runtime on eligible TVs. Retain its verified binding for recovery/removal. The manual bundle install request does not select this app as Home; normal
cytv setup follows provisioning with verified activation and launch. Manual persistent activation is available
through `setup.py enable` or **Change Home** in Home settings after the checks
pass. For normal setup, use [manual installation](../../docs/MANUAL_INSTALL.md),
including shared product status/removal and explicit continuation, or [cytv](../../docs/INSTALL.md).

The generic bundle inventory is empty; normal shared setup discovers apps locally on the TV before installation. Explicitly add `--migrate-packaged-home` to **install** to import a validated Home Updater profile or `apps.js`, `config.js`, and referenced packaged icons from the fixed installed `com.gathin.tvhome` app. The source is read-only and never modified. Browser/localStorage-only preferences are excluded. Resulting candidate file hashes are retained in `personalization.json`; migration never adds personal data to the offline distribution.

The driver records stages in `/var/lib/clean-your-tv-root/deploy.json` before installation submission. Installation proceeds only after an independent matching terminal backend event and installed-file hash verification. Existing candidate files or state block installation. A timeout, disconnect, or uncertain result requires inspection; do not blindly retry. Remote staging remains available after failure.

Uninstall first requires successful Home recovery, rolls back this candidate's LS2 provisioning, refreshes registration, and requests removal. It requires a terminal removal reply and absence of all candidate app/service/package directories. After matching terminal removal, a fixed empty package metadata directory may be removed with `rmdir`; nonempty or indirect leftovers still stop cleanup. State and recovery evidence remain on disk; the driver never deletes retained state automatically. The production app and legacy helper are never written by these drivers.

Recovery implementation: service code and its fixed runner are copied by verified
hash into root-owned private state. The firmware's immutable Node bootstrap runs
that service; the Homebrew runner and system launcher are not patched. Registration
of the one recovery activity uses the root installer with a fixed bus sender and
checks the complete stored definition and creator before reuse or cancellation.

Normal source `install` requires both bundles and installs Root Home + Root
Updater. `setup_updater.py --apply` submits the same shared product request; do not
run both entry points for a fresh install. `--component-only` is advanced recovery
only. Keep the generated 32-hex operation ID above privately for status and
`--resume`, which validates the original private snapshot and lease. Unknown submissions remain blocked. See [manual continuation](../../docs/MANUAL_INSTALL.md#candidate-shared-product-continuation).

Homebrew's separate CYTV Installer is Root-only and unpublished; it embeds pinned
offline Python for supported ARMv7/armv8l 32-bit userspace. Runtime preparation is
explicit and followed by inspection/review. Homebrew updates/removes Installer
only; complete-product removal and signed product updates retain existing
coordinator/updater ownership. Package-owned 50/51/52 startup links and live
package-disappearance guards are implemented but direct deletion, standby,
cold boot and all other [physical gates](../../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md)
remain untested. Recovery evidence and referenced runtimes survive removal.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="offline-candidate-bundle"></a>
