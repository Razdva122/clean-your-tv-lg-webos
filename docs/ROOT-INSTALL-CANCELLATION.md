# Internal recovery: cancel a never-activated Root install

This is a narrow maintainer recovery operation, not normal setup, an install
continuation, a repair command or a release acceptance claim. It is currently
limited to a failed product install at `root-deploy`, an independently saved
genuine SDK install terminal, no migration and no Root Updater/System state.
The cancellation baseline shipped in v1.5.0 and admits two exact Root journals.
The isolated inspection entry and optional candidate lookup below are
**unreleased source changes**; use their exact reviewed checkout, not an older
installer or a patched retained worker:

- `install-observed`: provisioning never started (the failure reported in #101).
- `provision-finalize-starting`: a saved finalize failure at `stock-home` or
  `status`, before activity registration, readiness or activation (#133/#143).
  This path needs the original provisioning snapshot and pending manifest.

Admission is conditional on the actual saved evidence, not the issue number,
model or `home_changed: false`. No reporting TV has been recovered or certified
by these source changes. Missing System Profile remains unsupported for Root
installation; cancellation does not add a Settings-only Home adapter.

Use separately reviewed source in an isolated checkout. Do not patch a retained
worker, private runtime, bundle manifest, original request/submission, host
pending record, ownership receipt, or SDK container permissions. Never submit
another install to resolve this operation.

## Admission and code identity

Build the maintained Root Updater **code bundle** without installing it:

```sh
npm ci
mkdir -p build
python3 root-edition/build_updater.py --output build/root-recovery-code
python3 scripts/root-install-recovery.py digest --code-bundle build/root-recovery-code
```

The digest pins the complete worker bundle and the separately maintained
`root-edition/cancel_install.py` and `root-edition/cancel_provision.py`. These
recovery modules intentionally remain outside historical worker inventories.
Both the host and the device check the pin. Keep that same reviewed code and pin
through an admitted cancellation; do not upgrade an in-progress cancellation.
The host uses exactly one saved Root profile whose pending operation matches
the explicit operation UUID, with saved automatic SSH authentication.

Before connecting, follow the [read-only admission handoff](development/ROOT-READONLY-ADMISSION.md)
to identify the original UUID locally and agree on the bounded inspection with
the owner. Run `inspect`, supplying that UUID and reviewed code digest. The
optional `--candidate ORIGINAL_CANDIDATE_SHA256` pins a candidate already known
to the maintainer; without it, inspection reads the candidate from that operation's
original device request and still authenticates it against the submission and
complete snapshot:

```sh
python3 scripts/root-install-recovery.py inspect \
  --code-bundle build/root-recovery-code \
  --operation ORIGINAL_UUID \
  --code-sha256 REVIEWED_RECOVERY_CODE_SHA256
```

This uploads trusted code to a new private temporary directory and checks the
original immutable snapshot, private support/runtime and interpreter binding,
request, submission, candidate, saved SDK terminal and exact product lease.
Before any private Python starts, trusted host-side Node checks the retained
interpreter binding as data. The tool calls only a fixed system interpreter or
the pinned private interpreter, with `-I -B`; its staged `python_binding.py`
checks the full binding/runtime inventory. Retained Python helpers, launchers,
user site modules, current-directory modules and `PYTHONPATH` are not executed.
Missing or changed binding evidence refuses inspection; it does not provision a
new interpreter or run the normal installer's smoke/write checks.
Every installed Root byte must match the original package. It rejects unknown
private entries (including dangling links), other product
components, project routing, non-LG Home routes, installer activity and live
original workers or private recovery processes. Do not kill a process or reboot
the TV just to bypass this refusal; review how to obtain a quiescent state.
The result includes the original candidate, code pin and proof digest; `admissible` does not mean
that installation or cancellation completed. No product record, package or
host pending receipt changes during inspection. The temporary code directory is
removed after a successful invocation; preserve it on a failed/unknown invocation
until any process is confirmed stopped, then remove only that staging directory.

Cancellation authenticates the known historical Root runtime layout containing
`runtime/audio_recovery.py` as well as the current inline-audio layout. It checks
the original complete inventory, static receipt and candidate digest, including
that historical module's bytes. It never imports that module or relaxes the
current bundle requirements used for installation/resume.

Admission does not establish human input acceptance. Confirm LG Home controls
immediately before a reviewed device mutation. Keep private backups and raw
hardware diagnostics outside the repository and public GitHub records.

For a finalize failure, inspection additionally verifies the complete private
service against the original package, its exact runner and pending runtime
manifest, and the four fixed LS2 registration paths. Snapshot contents, hashes
and ownership must match the maintained provisioning plan and current files.
Readiness, stock-Home initialization, activity registration, startup hooks,
profile trials, persistent intent and other unknown state are refused. An
ActivityManager list must confirm no recovery activity. Settings must be readable
with LG Home or an absent Home override; these settings and unrelated entries
are pinned through cancellation. System Profile is not queried on this narrow
never-activated path. This proves absence of our routing effects, not firmware
routing support or physical remote acceptance. Normal install/resume gates remain
strict and separate from snapshot authentication.

## Explicit cancellation and unknown outcomes

After reviewing the concrete proof and authorizing removal, invoke the same
command with action `remove`, `--proof-sha256 REVIEWED_PROOF_SHA256` and
`--confirm-lg-home` after the device owner confirms LG Home and normal remote
controls still work. An issue's earlier confirmation does not replace this fresh
check. No remove connection is attempted without the explicit flag.
It repeats admission under the **same original product lease** and provision
lock. A single atomic deploy write preserves the complete original proof and
sets `cancellation-admitted`, which unchanged historical resume code refuses.
A crash before the separate cancellation receipt can recover from this exact
embedded proof. The original request, submission, snapshot, code and SDK install
terminal remain unchanged.

For admitted finalize failures, the cancellation restores only the four fixed,
exactly recorded LS2 registrations, including their original mode/UID/GID, then
scans registrations before submitting removal. It never calls the failing
recovery service or writes Home settings. The original provisioning snapshot,
pending manifest, failure record and private code remain unchanged. A partial
restoration accepts only original or expected installed bytes and can finish
without resubmitting a package operation; drift blocks further work.

The separate cancellation receipt saves `remove-submitting` before one subscribed
SDK remove. A lost terminal is unknown and **cannot be replayed**, including when
the package is absent. A saved actual removal terminal allows readback and
remaining bookkeeping without another remove. No installation, activation,
emergency-latch reset, retained-code execution or shared SDK permission/ownership
change occurs. Metadata restoration is confined to the four owned LS2 files.

After removal, package/registration absence and the admitted Home checks must pass.
The original lease becomes terminal at `cancelled-and-removed` only after actual
removal/readback. A cancellation receipt without the terminal lease reports
`cancellation-terminal-pending`; it cannot retire host pending. The failed install
never becomes an install-success record. An old resume after terminalization is
read-only; concurrent changes to original evidence before that point cause
recovery to fail closed rather than silently accepting revised proof.

## Host reconciliation and archival

Run action `reconcile` with the same UUID, candidate, reviewed code and proof.
It obtains the host session lock and performs fresh device inspection. Only
`cancelled-and-removed` with a terminal original lease permits preserving the full
original host pending record and device disposition in a private recovery-history
file, then retiring the active pending file. Neither package absence nor a
locally invented completion can do this.

Keep the removed Root state in place until that disposition has been verified.
Then reuse the existing strict `Installer.prepare_root_reinstall(already_removed=True)`
archive path, without calling install. It records/reconciles the archive identity
and preserves the old Root evidence by rename. Cancellation terminalization
**must precede archival**, so an old resume cannot see a fresh Root tree under a
nonterminal original lease. If archive fails, retain its host receipt and use the
existing status reconciliation; do not delete it or reset the lease.

A later fresh install requires a new UUID, reviewed fixed artifacts and separate
normal setup authorization. Successful cancellation alone proves no runtime
compatibility, standby behavior or cold-boot recovery. Windows path work and
release acceptance remain separate.

## Verification

Focused tests exercise exact pinned services DATA, original evidence drift,
pre-registration finalize failures with unavailable System Profile, exact LS2
restoration, activation/activity rejection, interrupted rollback, active
installer/worker rejection, old resume exclusion,
one real remove, lost terminals, and crashes before the separate receipt, after
terminal removal, after final deploy readback and before lease terminalization.
Host tests prove that unknown/wrong dispositions preserve pending and verified
cancellation preserves its history. Run the repository test suite before
integration. Real hardware admission can verify source/package identity without
authorizing or proving actual cancellation.
