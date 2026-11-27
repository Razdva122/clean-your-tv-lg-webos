# Homebrew Installer development and promotion

[Installer status and requirements](README.md) ·
[Physical acceptance record](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md)

## Reproducible candidate preparation

The offline Homebrew build requires `ziglang==0.14.1` for the ARM cleanup
lock and Home Helper. It stages the pure Python files and license of
`websockets==15.0.1` from the build environment.

Keep `build_payload(...)`, `build_installer(...)` and the existing
`homebrew/build.py` CLI as the build API. Build Root, Root Updater and supervisor
from the candidate source; use `cytv.python_runtime.prime_cache` to authenticate
the original runtime before `build_payload` normalizes it. `runtime-provenance.json`
records its original immutable URL, SHA256, size and normalized hash. Runtime
licenses are bundled with that archive, and Noto fonts carry OFL files. Project
source is [MIT licensed](../LICENSE); see [third-party notices](../THIRD_PARTY_NOTICES.md)
and the pinned [runtime source contract](../cytv/python_runtime.py).

For fresh setup the bootstrap runs the shared Root capability classifier in a
private snapshot. The supported local Root backend is system-profile. A
supported desktop-only Root backend leads to a desktop handoff. A typed
Root incompatibility invokes the No-root preflight. The pinned offline
payload includes both Home resolutions, Home Helper and the Ambient
companion. First pairing requires webOS approval and uses one bounded
connection to the TV's own address on port 3001.

The private No-root setup receipt binds the accepted package selection and
original operation. The installer keeps the credentials within the normal
Helper configuration and observer flow. Before reporting completion it
checks package and configuration readback and verifies the System Updater
setup. Home routing, standby and cold boot require device evidence.
[Edition selection](../docs/superpowers/specs/2026-11-26-homebrew-edition-selection.md)

The same application ID is used for the Homebrew package and the small
edition-bound tile built by `build_tile(output, version, edition)`. The latter
contains no Homebrew bridge or offline installer payload. Its `cytvTileEdition`
metadata identifies the target of a plain application-manager launch. The full
package stores this routing preference after the coordinator verifies a
single-tile installation. A pending setup request goes to its original
status flow first. An explicit launch with `cytvRecovery: true` opens the
independent recovery interface.

## Installation and recovery in the single-tile candidate

The public host builds still select the existing generation. Use the
[single-tile build commands](../android/DEVELOPMENT.md) for this candidate.

| Starting installation | Owner flow |
| --- | --- |
| Compatible rooted TV with Homebrew | Install the full Clean Your TV IPK, open the tile and confirm setup. Desktop and Android can open an already-installed full tile on the TV. The tile checks Homebrew access and Root compatibility. |
| Fresh Developer Mode TV | Desktop or Android pairs the TV and installs the daily tile, hidden Home and Helper. Subsequent launches open Home directly. |
| Existing supported Root or No-root | Keeping the installation is the default. Switching via the clean-install option removes the old settings. Root requires the full tile on the TV first. The host verifies removal before asking to continue setup. Mixed editions, incomplete operations and experimental Root setups require their existing recovery route. |
| Developer Mode TV already using the tile | Run the matching desktop or Android installer to repair the tile or update a compatible screensaver. The installer keeps Home and Helper in place. A full Home upgrade that preserves preferences needs an app-mediated export and verified restore on the host path. |
| No-root installed over an existing root SSH connection | Fresh single-tile setup prepares on-device updates after verifying the installed Home and Helper. An interrupted preparation is bound to its original host and TV receipts. |

The first installation starts a new rollback history. To return to an older
multi-tile release, remove the product and install that release separately.
On a TV with the verified update service, a later signed update records the
prior generation-two package set and profile. The independent recovery screen
can restore that set after a failed Home launch. With an unavailable service,
continue recovery from the matching host installer. Device acceptance must
check app visibility, physical Home routing, standby, stored media and reboot
on the exact candidate.

On-device product updates capture the Home profile while the original app can
still read its browser storage. The profile includes the supported local
preferences and the app's own theme and personal wallpaper stores. The update
service accepts up to 3 MiB of serialized browser data within the existing
4 MiB request limit. An incomplete or oversized backup stops the update before
package replacement. Home restores and reads back the snapshot before reporting
a successful start. The host Developer Mode repair path keeps the Home package
installed because that path has no verified browser-profile transfer.

One setup confirmation covers the verified fresh Root installation, preparation
of complete updates and a single activation attempt. Existing editions require
the dedicated transition flow. When Python preparation is required, the UI checks
the original payload digest, fresh installation state and candidate digest
before submission. The product worker verifies the installed generation,
releases its installation mutex and uses the guarded runtime to request
activation. Status reports package completion, launch acknowledgement and
current routing separately. Restore or removal revokes the setup approval.
Verify this path, interruption and recovery on the selected physical artifact
before recording acceptance. [Private files and operations](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#review-inventory-persistent-files-permissions-and-endpoints)

`cytv.yml` has an optional `homebrew_candidate` manual input. Its `homebrew` job
also runs with normal candidate installer builds; it uses no signing secret and
uploads only a `homebrew-candidate` CI artifact. Its failure is optional unless
acceptance selects the current frozen project release; selected promotion requires
both the successful workflow and a successful Homebrew job. Stale approval records
for unrelated release tags keep the build optional. It defaults to installer **0.0.0**,
which is a development version and cannot be promoted. Candidate URL strings in
its manifest reserve an intended immutable release path; no reachability is
claimed. CI build success is not hardware acceptance.

Generate metadata only after the final IPK exists:

```sh
python3 scripts/homebrew-manifest.py --ipk /absolute/path/installer.ipk \
  --ipk-url https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/vX.Y.Z/io.github.razdva122.cytvinstaller_A.B.C_all.ipk \
  --icon-url https://raw.githubusercontent.com/Razdva122/clean-your-tv-lg-webos/COMMIT/assets/icons/installer-256.png \
  --output /absolute/path/homebrew-manifest.json
```

Replace the example version/commit tokens at candidate freeze; they are not
valid release inputs. The generator derives id, title, type, installer version,
installed bytes, IPK size and SHA256 from the actual package. It requires
`rootRequired: true`, HTTPS project release URLs, and validates the outer offline
inventory, inner component inventories/versions, runtime binding, provenance and
runtime inventory without executing any package or bundle code. The dedicated
Installer IPK reader allows up to 64 MiB per runtime archive, matching Root IPK
or baseline cache member. Its other members retain a 16 MiB limit.

## Acceptance and existing release gate

There is deliberately **no `homebrew/release.json`** in this candidate. Without it,
assembly ignores Homebrew CI artifacts and includes no installer, catalog
manifest or feed in the public asset list. Do not create that file until real
human and TV acceptance has been recorded. At freeze record the installer version
independently from product versions and bind the exact accepted bytes:

```json
{
  "schema": 1,
  "release": "vX.Y.Z",
  "version": "A.B.C",
  "ipk_sha256": "EXACT_ACCEPTED_IPK_SHA256",
  "manifest_sha256": "EXACT_ACCEPTED_MANIFEST_BYTES_SHA256",
  "ipk_url": "IMMUTABLE_PROJECT_RELEASE_IPK_URL",
  "icon_url": "IMMUTABLE_PUBLIC_ICON_URL",
  "source_url": "PUBLIC_PROJECT_SOURCE_URL",
  "hardware_acceptance": "Named record: model, webOS, firmware, hashes and all Task 8 results",
  "human_review": "Named human reviewer, meaningful review/test record and AI disclosure"
}
```

This is documentation, not acceptance evidence. Keep generated manifest formatting
unchanged after acceptance: its exact bytes are pinned. Freeze URLs too; the CI
job reuses them from the acceptance record. Accepting exact artifact hashes avoids
a circular source-commit requirement when adding acceptance changes the Git SHA.
The accepted artifacts still must come from the existing successful trusted
candidate build and exact merge-tree gate; a successful `homebrew` job becomes
required when the acceptance `release` matches the current project release. The
record selects only that frozen release; later unrelated releases ignore it for
fresh promotion and use verified carry-forward. A new installer needs its own
version, originating release and exact acceptance record. No independent publisher or signing bypass exists.

`assemble-release.py` verifies accepted bytes before copying them; existing
SHA256SUMS generation includes both manifest and IPK. `prepare-release.py` verifies
accepted Homebrew artifacts again before existing signed-feed preparation.
Signing and publication also require the approval in BUILD-INFO to equal
`homebrew/release.json` at its verified source commit; mutable release metadata
cannot independently grant acceptance. Keep the originating acceptance record
unchanged while carrying that installer across unrelated releases. On a
later unrelated release, it carries the previously verified acceptance record,
manifest and IPK forward unchanged if no new installer is selected. Embedded
product versions remain those of the accepted installer, not the newer project
release. Orphan/unaccepted assets are never adopted. Installer regression or a
changed approval/artifact without an installer version increase fails.

The catalog's one intended stable endpoint is
`https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/homebrew-manifest.json`.
Carry-forward keeps that file present across unrelated releases while preserving
the original immutable `ipkUrl`. `publish-release.cjs` checks checksum membership,
exact accepted metadata, data-only inventories and package bytes again, and
fetches the original release IPK to verify that URL still serves the accepted
bytes. It rejects unaccepted/orphan public installer assets. This happens in the
existing protected publication/check-only path; normal signing, checksum, source
and product-feed gates stay authoritative. Publication is followed by the existing
check-only verification; missing assets or verification failures block success.

## Catalog review

`catalog/io.github.razdva122.cytvinstaller.yml` targets upstream apps-repo `PackageInfo.json`
(category `utility`, pool `main`). Generated metadata targets
`api/PackageManifest.json`. Its planned URLs and screenshot omissions must be
resolved before submission. Schema success cannot establish URL availability.
Validate against current upstream validators at submission time, using bounded
network checks and without executing downloaded application code. The
[catalog preflight](catalog/SUBMISSION.md#catalog-preflight) records the upstream revision and results.

Required remaining evidence: public HTTPS URLs, representative TV screenshots,
package staging/storage measurement, clean HBC setup, both cytv/TV handoffs,
upgrade/rollback, System Updater setup, automatic import when compatible Home
settings exist, setup without a migration source, direct installer and component
removal, triple-Home, standby and separate cold boot. Record exact artifacts
and human review. AI assistance was used for implementation and this
draft; disclose it in the eventual submission. Do not submit the catalog draft
or publish Homebrew assets before those gates pass.


Unreleased cold-boot correction: rooted SDK DATA may have ordinary `0777` modes.
The corrected private readers require independent original package hashes; they
do not repair shared permissions or execute shared source. Missing/conflicting
current, transaction or own-package proof keeps automatic Home rearm inhibited,
while independent private LG Home restoration remains available. Deliver the
changed helper closure through checked fresh setup/rebootstrap, preserving
existing recovery archives and unknown-operation records. Updating Installer
alone does not replace retained private product code. Fresh setup can authorize
the separate activation attempt together with installation. Maintenance also
offers explicit activation and Restore. See the
[candidate authority and acceptance record](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#cold-boot-data-authority-correction).
