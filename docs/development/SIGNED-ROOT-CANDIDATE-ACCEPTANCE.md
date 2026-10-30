# Private signed Root candidate acceptance

This is maintainer-only acceptance tooling for an unpublished candidate, not a
public update channel or a workaround for an unsupported TV. It requires explicit
owner authorization for update and retained rollback with the owner present.

The original v1.3.0 System Updater reads only GitHub's public `latest` feed.
An unpublished candidate cannot be discovered there. Never overwrite a published
feed, patch a pinned supervisor/key, fabricate a transaction or bypass a signature
to make a candidate appear. The acceptance controller substitutes only offer
selection during admission; the original production verifier and worker remain
responsible for trust, installation, health and rollback.

## Host and signing gates

For normal early Root feedback, use the direct package route documented in
[TV development](TV-DEVELOPMENT.md). It builds only the three coherent Root
packages, verifies run/source/artifact provenance in the protected signer and
downloads a production-key-verified unpublished artifact. No temporary GitHub
release or desktop executable is needed. The device admission, owner-presence,
rollback and evidence requirements below still apply. Preliminary results never
replace the complete frozen release build or final acceptance.

The desktop-artifact route remains available when `cytv.yml` already produced a
feedback build:

1. Record its exact run, attempt, branch, source SHA and unpublished version. The
   macOS ARM64 package job must have succeeded and no job may be known failed or
   cancelled. Keep the branch at this source until signing and recheck finish.
2. Dispatch the protected Root-only signer:

   ```sh
   gh workflow run publish-release.yml --ref release/next \
     -f tag=vX.Y.Z -f publish=false -f preliminary_root_qa=true \
     -f candidate_build_run=RUN_ID -f candidate_source_sha=EXACT_SOURCE_SHA \
     -f candidate_branch=SOURCE_BRANCH
   ```

   Leave `direct_tv_qa` false for this route. The trusted tools inspect the
   digest-bound macOS artifact and its embedded payload without executing
   candidate source. The private key stays in the protected Actions environment.
3. Download `signed-root-candidate-RUN_ID-ATTEMPT` from the signing run. Verify
   the production signature with `system-updater/policy.js`, source-bound notes,
   provenance, manifest versions and all three package hashes before admission.
   Bind the exact envelope bytes' SHA-256 to the request and retain both run IDs.

Neither preliminary route uses `assemble-release.py` or creates a temporary
GitHub release. The assembler requires a complete full candidate and final merge
provenance; never weaken it or fabricate those facts for feedback builds. Root
QA does not establish desktop, Android, No-root or final release acceptance.

## Device admission

Read the connected model/firmware and current versions. Retain original supervisor
code/infrastructure hashes, current/prior state and local rollback cache hashes.
A synthetic local release `v0.0.0` is normal: its component versions and captured
bytes are the actual computer-provisioned rollback baseline. Do not replace it
with a reconstructed public-release descriptor or clear an aborted journal.

Use the already trusted SSH profile and verified pinned Python binding. Run
`scripts/root-candidate-acceptance.py` through an isolated `-I -B` interpreter with
its request on stdin; do not stage executable code into the installed supervisor.
The controller reads the infrastructure receipt, captures every authenticated
source and uses a private import namespace, rather than loading adjacent bytecode
or ambient modules. It verifies the production envelope through the original
installed Node verifier. Original package inspection must accept **every** candidate
and prior cache before the controller can mutate anything.

The exact JSON request fields are `action` (`preflight` or `install`), `release`
(`vX.Y.Z`), `envelopeSha256` (raw envelope JSON SHA-256), `envelope` (base64 of
those exact JSON bytes), and `packages` (component name to base64 package bytes).
Only `install` additionally accepts `profile`, the actual UI-captured profile.
Root edition is fixed; request data cannot select paths, commands, keys or modules.
Unknown/duplicate fields and non-finite JSON values are rejected. Output contains
only phase, release, component names/versions/digests; do not log the input request.

Start with `action=preflight`. It must report versions/hashes only and write no
cache, journal, lease or legacy-lockdown state. A failed preflight is a stop, not
permission to repair state manually. Existing cache conflicts must be rejected.

For `action=install`, supply the complete profile captured from the **running UI**
using `RootProfile.capture({system:true})`, including embedded icons, actual
configuration, order/language/layout. Store it privately; do not manufacture an
empty profile or copy a historical capture. Compare its digest after installation
and rollback; do not expose app inventories or private profile data publicly.

The controller rechecks all gates under the original product lease, publishes
absent signed packages through the original exclusive atomic cache writer, then
calls original `Manager.install`. The original Manager alone writes the new
transaction. Release the lease before starting the unchanged original worker.
Draft URLs are not anonymously readable: this run uses exact signed cache bytes,
and therefore does not establish anonymous public-download acceptance.

## Observe and roll back

Observe the original System service status. Do not synthesize healthy receipts:
the real launcher must restore the saved profile, render its actual tiles and
send its ordinary health signal. Require completed component installer terminals,
verified package/infrastructure hashes and normal Home resumption. Unknown package
outcomes require supported recovery; do not retry an install or force rollback.

After successful update, obtain owner confirmation of Home, arrows/OK/Back,
volume/audio and emergency behavior. Explicit/emergency off must stay off. Keep
standby, normal restart and true AC-off results separate; update acceptance alone
does not accept all lifecycle paths or firmware blocking.

Invoke retained rollback through the **ordinary installed System Updater service**.
Observe its unchanged worker, real launcher/profile health and completed rollback
terminals. Compare original versions, exact baseline/code/profile hashes and
owner-confirmed controls. Preserve journals, original caches and rollback evidence.

## Evidence and final release boundary

Record the candidate build and signing run IDs, source commits, artifact/envelope/
component hashes, model/firmware, actual tested paths, failures and untested paths.
This accepts separately authorized offer admission, signed package handling,
original worker update and rollback. It does **not** accept normal public feed
selection, anonymous draft download, fresh computer provision or all TV models.

For another user's device, show the exact redacted report and destination and
obtain the owner's consent under AGENTS.md. Authorized maintainer QA on a
maintainer/project-owned test device may record concise technical results within
the approved release scope. Neither case authorizes publishing private logs.

Preserve the signed evidence privately. Never overwrite a published version.
Record acceptance honestly, complete and pin all required platform builds at the
frozen source, verify intended TV component bytes still match the accepted bytes,
and complete Release policy before main integration.
Production publication and shipping notices remain the normal protected workflow.
