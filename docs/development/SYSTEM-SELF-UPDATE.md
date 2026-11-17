# System Updater self-update

This feature establishes a new provisioning baseline for Root and No-root on
rooted TVs. It does not repair older retained supervisors, switch edition on root
detection, or implement on-TV Developer Mode installation. Product release
numbering remains the release coordinator's choice.

## Stable entry and replaceable engine

The registered service calls the provisioned bootstrap. Before interpreting a
product protocol, it verifies the separate signed `system-bootstrap-v1.json`
catalog at `releases/latest/download/system-bootstrap-v1.json`. Every capable
future release must retain that asset name, all four edition/graphics descriptors
and the referenced immutable engine archive.

The catalog authenticates exact Root, Root HD, No-root and No-root HD product sets
without requiring the first bootstrap reader to interpret their future protocol.
The selected engine interprets the product set. Python and Node requirements are
checked before staging. The engine is staged in an inactive private slot and
verified against its signed archive and complete inventory before activation.

Engine and product work share the existing device operation owner. Recovery
retains the selected catalog, edition, graphics variant and profile snapshot;
retry does not silently select a different release. A previous confirmed engine
remains available during trial activation. Own-package migration uses a separate
journal and generation receipt while preserving the original provisioning trust.

The existing installer observation rule remains mandatory: an unknown submission
is never permission to submit again. A matching version or idle installer is not
terminal evidence. Do not clear ownership or modify inventories to bypass this.

Recovery offers **Reinstall System Updater** when the signed catalog supplies
the installed engine version. A newer engine is installed through **Update all**.

No-root keeps Home, Helper and Home Updater. Its signed Home package contains the
authenticated screensaver Companion recipe, using the existing fixed component
set. Root retains its recipe in Root Home. Both HD/FHD packages carry the recipe.
Explicit and emergency-stop intent remains authoritative.

## Build and publication

The bootstrap and engine have independent versions. `engine_version` is recorded
in the complete installer bundle. The reproducible engine archive contains its
inventory and System IPK; setup-only host code is excluded.

Signing preparation reads the immutable source commit and requires artifacts for
engine-capable sources. It reconstructs the engine independently from the Root
installer archive and No-root installer ZIP, then compares both with the proposed
public archive. Version regression and changed bytes under the same engine
version stop publication. The builder's explicit historical-fixture exemption is
not the normal release path.

The bootstrap signature binds all four independently checked product manifests.
Final publication verifies the catalog against BUILD-INFO, product feeds and
archive bytes. Retain the catalog even on releases without updater changes:
unchanged older clients still need their route to the current product. Existing
Home/Root/Helper version and rollback compatibility gates remain mandatory.

## Signing-key rotation

`system-updater/bootstrap-public.pem` is the stable trust root. Initially it equals
the product release public key. Keep this separate file unchanged when changing
`updater-service/release-public.pem`, including in every new engine.

Catalog envelopes optionally carry `keyChain`: up to eight ordered delegations,
each containing `publicKey` (SPKI PEM) and `signature`. Sign the exact UTF-8 bytes
`CYTV bootstrap key v1\n` followed by that PEM with RSA-SHA256 using the preceding
trusted key. The final delegated key signs the catalog payload. The first reader
already understands this format. Missing, reordered and substituted links fail.

The protected workflow accepts secret `BOOTSTRAP_SIGNING_PRIVATE_KEY` and public
JSON variable `BOOTSTRAP_SIGNING_KEY_CHAIN`. Without a separate secret it uses the
product signing secret, which must still verify against the bootstrap root.
A product-key change without valid bootstrap signing configuration fails closed.
Private keys never belong in Git or on the TV. Retain an offline root and a
bounded delegation route; this does not recover from compromise of all trust.

## Sign a pinned candidate catalog

After the complete candidate succeeds and the release plan pins its run and
attempt, dispatch the protected signing workflow on `release/next`:

```sh
gh workflow run publish-release.yml --ref release/next \
  -f publish=false -f system_candidate_qa=true \
  -f tag=vX.Y.Z -f candidate_build_run=RUN_ID
```

The Actions artifact `signed-system-candidate-RUN_ID-ATTEMPT` contains the
catalog, four edition/graphics manifests, exact packages, engine archive and
build provenance. It stays separate from the public release feed. Verify it
against the pinned bootstrap public key. The TV's ordinary online updater
still requests the published channel, so signing the artifact establishes
signature and package evidence. Live delivery also needs a supported way to
present the unpublished assets and a compatible starting engine.

## Verification scope

Keep the [original acceptance case IDs](../superpowers/plans/2026-11-16-updater-self-update.md#9-release-acceptance-and-future-publication-gate).
SU-11/SU-12 concern genuinely unrooted TVs and are outside the maintainer's selected
implementation scope. Host tests cover signatures, build provenance, slots,
journals, recovery and edition contracts. They do not establish real LS2 recovery,
physical power-loss behavior, Home routing, remote input, audio or firmware support.

Before release, preserve the selected first-baseline bytes and provenance as
upgrade fixtures. Test new artifacts with that unchanged client, skipped releases
and a newer product protocol. Run affected Root and No-root/root device cases on
selected final artifacts using the canonical release ledger. The existing
Root-only preliminary signer cannot provide No-root/full self-update acceptance;
do not broaden its authority implicitly.
