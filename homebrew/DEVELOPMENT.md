# Homebrew Installer development and promotion

[Installer status and requirements](README.md) ·
[Physical acceptance record](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md)

## Reproducible candidate preparation

Keep `build_payload(...)`, `build_installer(...)` and the existing
`homebrew/build.py` CLI as the build API. Build Root, Root Updater and supervisor
from the candidate source; use `cytv.python_runtime.prime_cache` to authenticate
the original runtime before `build_payload` normalizes it. `runtime-provenance.json`
records its original immutable URL, SHA256, size and normalized hash. Runtime
licenses are bundled with that archive, and Noto fonts carry OFL files. Project
source is [MIT licensed](../LICENSE); see [third-party notices](../THIRD_PARTY_NOTICES.md)
and the pinned [runtime source contract](../cytv/python_runtime.py).

The offline inventory includes the fixed Python edition reader and the desktop
Root capability modules it imports. For fresh setup the bootstrap executes
that reader in its private, inventory-checked snapshot. The supported local
installation uses the system-profile Root backend. A supported desktop-only
Root backend leads to a desktop handoff. Positive evidence that Root cannot
control Home leads to computer or Android setup to establish No-root eligibility
and pair Home Helper. The TV candidate has no first-pair or installation path
for No-root. [Edition selection](../docs/superpowers/specs/2026-11-26-homebrew-edition-selection.md)

The same application ID is used for the Homebrew package and the small
edition-bound tile built by `build_tile(output, version, edition)`. The latter
contains no Homebrew bridge or offline installer payload. Its `cytvTileEdition`
metadata identifies the target of a plain application-manager launch. The full
package stores this routing preference after the coordinator verifies a
single-tile Root installation. A pending setup request goes to its original
status flow first. An explicit launch with `cytvRecovery: true` opens the
independent recovery interface.

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
