# Signing and publishing update feeds

The release branch policy, late version selection, required release PR checks
and post-publication issue/PR notifications are described in
[Release integration flow](RELEASE-FLOW.md).

The normal release trigger is a finalized `release/next` PR merged into `main`.
Choose the version at candidate freeze, not when creating the preparation branch. Set
`release` and the changed component versions in `release-versions.json`, update
the matching application/service manifests and add `docs/RELEASE-X.Y.Z.md`.
Publication itself needs no manual tag, draft creation or Publish click.

After freezing a newer release version, matching plan and release notes, dispatch
**cytv standalone builds** on `release/next` with `full_candidate=true`. This
runs complete validation and all four desktop builds plus Android. Ordinary
pushes do not start or cancel candidate builds. Ordinary PRs run affected checks
without producing platform installers. For device feedback before acceptance,
`test_build=true` produces preliminary installer artifacts; the faster direct
Root route is documented in [TV development](development/TV-DEVELOPMENT.md).
Neither preliminary route publishes,
sign feeds or satisfy the final release gate; see [candidate preparation](RELEASE-FLOW.md#freeze-and-validate-the-candidate).
After merging the
candidate into `main`, **Automatic release**:

1. Finds the successful trusted build pinned by the merge's second parent (or
   the exact second-parent build when unpinned), verifies equivalent build inputs,
   requires all five platform jobs to succeed, verifies that the candidate and
   merge have identical Git trees, and checks that the release is unpublished.
2. Verifies the complete candidate test record, including Linux/macOS, browser
   and ARM checks, without repeating the full suite after merge.
3. Downloads only that build's artifacts, checks payload versions and hashes in
   all installer files, and creates the public No-root ZIP and Root TAR
   bundles, release notes, `BUILD-INFO.json` and checksums.
4. Creates/resumes a draft targeting the exact `main` merge commit and uploads the
   prepared assets. A draft/tag for another commit stops the workflow.
5. Calls the protected signing workflow directly: it creates both feeds and
   rollback assets, signs them, uploads them, verifies every referenced package,
   publishes as latest and verifies again.
6. Uses the checksummed `RELEASE-INVENTORY.json`, bound to the exact source
   commit, to notify all included PRs and related issues without duplicate bot
   comments. **Retry release notifications** retries this step independently.

Already published versions are skipped. Failed tests, builds, packaging or
signing never advance a new release to latest. Retrying the failed workflow can
resume a draft for the same commit. Publication rechecks the draft immediately
before upload. A newer published version blocks older release attempts.

For pipeline maintenance, **Automatic release** also accepts a successful candidate
build run ID (or finds it automatically) and `validate_only=true`, running from
the corresponding `main` merge. Historical successful `main` builds are also
accepted when their SHA matches exactly. Packaging tools and the tested release
source are checked out separately. This assembles/verifies the
complete release asset set without creating a draft, signing or publishing.
Platform installers are reused; `BUILD-INFO.json` records both the merge's
`source_commit` and the candidate's `build_source_commit`. Android provenance
continues to require its original candidate SHA and signer.
The signing workflow's separate `publish=false` mode validates production
signatures without changing release assets. These modes are for testing the
pipeline; normal releases need neither manual invocation.

For an already prepared draft or an explicit repair of a current release,
`node scripts/publish-release.cjs vX.Y.Z` remains the signing entry point.
It queues signing and publication; waiting for the workflow result is required.
An installer-only release preserves the existing older signed Home rollback.
A new Home release uses the nearest previous stable release's actual Home IPK.

The GitHub **release-signing** environment holds `UPDATE_SIGNING_PRIVATE_KEY` as
an encrypted environment secret. Stable publication uses `main`; the separate
Root-only QA job uses trusted `release/next` tools and cannot publish. The secret
is passed only to trusted signing/preparation steps and is never written into an
artifact or a log. Keep the offline key backup. Re-provisioning requires an
explicit operator action; changing the signing identity also requires updating
and deploying the clients' pinned public key.

The workflow has a `publish=false` input for an end-to-end generation/signing
check that leaves release assets and publication state untouched. Its artifact
contains only public feeds, IPKs and metadata. Existing published releases can
be repaired through the same workflow; older-than-latest tags are rejected.

For a read-only check of existing public/draft feeds:

```sh
node scripts/publish-release.cjs vX.Y.Z --check-only
```

Do not publish directly with `gh release edit` or the web Publish button: these
bypass preparation. GitHub does not emit draft-created/edited workflow events,
so the version change in `main` is the normal release entry point. The read-only **Release
update feed** workflow still detects invalid feeds after public release edits.
The signing workflow verifies inline after publishing because changes made by
`GITHUB_TOKEN` do not trigger another release workflow.

A wrong/missing key, absent bundle, version regression, incompatible rollback,
changed package without a component-version bump, or mismatched provenance
stops the workflow. A Helper version change needs a compatible, tested rollback
baseline; the automation stops rather than publish an unusable No-root offer.
An operator-tested runtime transition can be approved in
`native/helper-rollback-compatibility.json` by pinning the exact new Helper
archive (`candidate_archive_sha256`), previous Helper package, published Home
rollback and a nonempty acceptance record. The new archive hash includes every
uncompressed archive byte and metadata field; gzip headers are excluded for
portability between build hosts. A changed payload, installation control or
rollback baseline stops publication. Acceptance must state its actual hardware
scope and any missing device/artifact details. This is a specific reviewed
transition, not permission for arbitrary Helper changes.

For 1.1.0 the maintainer explicitly authorized stable publication with incomplete
physical Helper/rollback validation. Its exact-archive approval records that
exception and automated evidence; it does not claim an operator-tested Helper
transition. See [the bounded acceptance record](RELEASE-1.1.0-ACCEPTANCE.md).
Hash, provenance, signature and protected-branch checks still apply unchanged.

A permission-only Helper transition can alternatively be approved in
`native/helper-rollback-compatibility.json`: it pins both Helper versions, the
previous Helper package, the exact previous Home rollback and the reviewed
permission-module hash. Preparation requires unchanged input executables and
all other runtime/protocol files; only version metadata and PNG assets may
also differ. Unapproved transitions still stop publication. Existing clients
with the older Helper must use the full installer before Home-only updates.
The previous stable release must have current build metadata and public bundles.
Version selection, release notes and TV acceptance remain development work;
all release build, packaging, signing and publication commands run in CI.
