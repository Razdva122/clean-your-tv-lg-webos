# Installer recovery design

Approved scope: the maintainer approved the seven-part recovery proposal in the current Codex chat on 2026-11-06 and requested complete, understandable recovery rather than a small patch. This document records that scope; implementation does not authorize a TV connection or a release.

## Goal

An interrupted operation opens an understandable recovery review that separates installed packages, configuration, Home activation, vendor-operation outcome and device acceptance. Every offered mutation must be justified by original-operation evidence and revalidated immediately before effects. The supported outcome is continued setup, completed setup with LG Home, verified cancellation/removal, or an explicit evidence blocker with a useful private diagnostic.

## Architecture

Retain Store, Root Ownership, component journals, existing continuation/cancellation proofs and transport. Introduce a common recovery assessment with fixed reason/action codes, separate observation from explicit reconciliation, and use the same assessment across CLI, desktop, Android and exported diagnostics. Do not introduce a database, dependency or a second product coordinator.

Authentication uses semantic credential types independent of localization. Current Root activation recovery is extended with a directly selectable Home-off completion; complete signed runtime delivery remains a separate compatible action. PR #357 owns the health-startup race and is not duplicated here.

New Root receipts explicitly identify the recovery protocol. New No-root receipts retain per-package request/terminal evidence. A detached, bounded Developer Mode observer must persist the original subscribed response on the TV across host disconnection; it must not require the Root-only global monitor. Unknown submission never authorizes replay. A reboot before terminal persistence remains unknown unless an authoritative vendor contract provides a result.

Legacy receipts remain immutable evidence. Recognized legacy Root cancellation uses reviewed existing proofs; unsupported layouts, changed files, foreign routing, uncertain package removal and missing trust are explicit refusals. No-root historical outcome loss (#201/#307) cannot be repaired by inventing a transaction ID, using inventory as terminal evidence, deleting pending or replaying install/remove. Document the missing vendor contract and expose a precise support state.

## Invariants

- Preserve original profile, host pin, candidate identity, first failure and receipts. No secrets or raw logs in public diagnostics.
- Observation never resubmits a package, enables Home, changes routing or clears uncertainty. Trusted support-code staging, where needed, is separately explained.
- Mutations require a default-No explicit choice and fresh proof under existing locks. Status polling does not authorize a mutation.
- Existing legacy readers and supported runtime floors remain compatible: host Python 3.9+, Helper/No-root TV Node 0.10.15+, Root Node 8+ and existing Python selection rules.
- Preserve emergency stop, triple Home, key-up delivery, independent guardian, watchdog, rollback and foreign registrations. Never automatically clear emergency state.
- Keep physical Home, audio, standby, cold boot, OTA and rollback observations separate from package or source-test success.

## Verification and delivery

Reproduce the Android untranslated-secret failure before fixing it. Exercise each recovery action through real orchestration and temporary filesystem journals, inject interruption at reservation/submission/terminal/readback boundaries, assert exact mutation counts, retain uncertain/corrupt evidence, and cover concurrent changes between review and confirmation. Exercise common desktop/Android UI in a browser. Run affected installer/setup/Android and TV runtime checks with pinned dependencies; full frozen-candidate and physical acceptance remain release gates.

User-facing flow changes update all existing localized guides and installer catalogs. Candidate-only behavior stays separate from published instructions. Preparation targets release/next without version bumps, release pin changes or automatic issue closure. Record unresolved legacy/vendor and hardware acceptance limits with the implementation.

## Subsequent candidate authorization

On 2026-11-06 the maintainer explicitly requested merge into release/next and a new versioned release-candidate build after all implementation work completes. The final stage therefore includes coordinated integration, inventory/version/documentation preparation and one full candidate dispatch under RELEASE-FLOW.md. It does not authorize main publication, device changes or inferred hardware acceptance. Implementation tasks continue without changing release inputs until that final stage.


## Explicit clean-removal requirement — 2026-11-06

The maintainer explicitly requires removal to leave a clean TV whether setup succeeded, failed or was interrupted. This expands the earlier recovery-only scope. Implement full removal before final UI/localization and candidate integration. Removal is its own desired-absence operation; reconstructing or completing the old installation is not a prerequisite. Preserve the old receipt and first failure as historical audit, without relabeling an unknown installation successful.

Clean means no product application, functioning service, startup/control capture, owned EIM/routing override, private credential/configuration or executable/large staging remains. Restore the verified preinstallation Home baseline (normally LG Home); preserve unrelated applications, Developer Mode, Homebrew, rooting, third-party routes and genuine preexisting-owner backups. A compact private non-executable removal fence/audit receipt may remain to prevent late setup resurrection. Do not retain complete live product trees or raw credential/code archives and call that clean. Explicit removal authorizes deletion of changed product-owned preferences/data; installation-continuation hash equality is not a universal prerequisite for deleting our own namespace. Shared/foreign registrations still require exact ownership restoration proof.

Use existing Store and edition coordinators with a durable clean-removal intent linked to all original/nested operations. Stages are requested, original-writers-fenced, controls-restored, package-removal, private-cleanup and verified-clean. The same intent survives reconnect/retry; a pending install must not merely disable Remove. A disconnected or unavailable TV keeps the removal requested with exact unfinished state, never a false success. Observation remains read-only. Once prior CYTV writers are fenced and a new accepted platform removal reaches its own authoritative terminal/readback, the previous installation outcome may remain unknown without blocking the new goal.

### Root cleanup

Transition under original Ownership/component locks and retain terminal tombstones honored by existing workers. Fence even operations interrupted before first lease/request checkpoint. Use current verified support code and data-only original snapshots; never execute retained code to establish trust or bypass an active lease with a fresh UUID. Restore only owned routing/registrations and finish required rollback before deleting their backups. Extend normal full-project removal to failed deployment/provisioning/updater/bootstrap states. Do not require finishing product installation or activating Home. Remove all owned product packages, startup and service registrations, then retire disposable live/private/staged material with fixed ownership-confined inventories. Retain only genuine owner backups and minimal receipts, separately from executable product archives. Repeated removal revalidates the clean state; uncertain new vendor removal is not replayed.

### No-root cleanup

Extend the existing observer into the sole TV-side effect executor. Package spawn, configuration publication and EIM/launch must pass a revocable lifecycle gate; the host cannot retain a transferable permission to send an effect after cleanup. Reuse pinned Zig 0.14.1 for a small standalone static ARM gate if needed; this adds no third-party dependency and does not change the published Helper package. Securely open one never-recreated lock inode and hold its kernel lock through fence validation, claims and each effect's relevant local completion boundary. Persist revocation while holding the same gate. Local process exit/lock release does not establish vendor drain. Preserve existing emergency/watchdog behavior and existing normal controls.

A new explicit remove is distinct from replaying the unknown install. Preserve actual request/app/package identity and original subscriptions. Model accepted, definitely-unsubmitted-busy, absent-without-drain, terminal-removed and unknown separately. Only established pre-admission refusal allows a bounded new attempt; arbitrary error24/negative replies are not assumed busy. Missing SAM registration may make dev/remove fail before exclusion. A narrowly built inert cleanup carrier is a candidate repair path: exact owned app/package IDs and union of known owned service identities, no control functionality/startup/private credentials, fresh bound dev/install terminal and readback, then subscribed remove and complete registration/data readback. A service-free carrier is insufficient when it discards old service identity inventory. No guessed high versions, force flags, permissions elevation, vendor-daemon kill or blind carrier loops. Unsupported retail/API cases keep precise removal progress; source/OSE models cannot be reported as universal retail acceptance.

New protocol operations must fence delayed workers and copied-host configuration before claiming clean. Existing v1/legacy actors cannot retroactively honor a new marker: admit only an actually established original executor drain/compatible guard and new destructive platform barrier. Unrelated future external installers are outside the guarantee; known already-started CYTV work is not. Never use empty inventory, no-SAM refusal, PID timeout or current desired state as a substitute for the required barrier.

### Verification and scope

Test successful and partial Root/No-root setup, failures before/after every submission, delayed old launchers/configuration, two hosts, source mismatch, missing SAM with retained services/data, carrier failures/unknown terminals, partial updater/provisioning, changed owned preferences, foreign route/backup preservation, interrupted private cleanup and repeated already-clean removal. Include new issue #359: original package exception/unknown followed by denied package-status, without inferring absent packages or pre-submission state. Preserve original/current failure separation and add bounded phase/category diagnostics at source boundaries. CLI, actual Qt and Android browser must expose one understandable removal journey and truthful final result across all 13 locales.

No TV connection, public installation report or main publication is authorized. The already authorized release/next integration and new versioned full RC happen after this expanded implementation, independent review and affected checks. Physical retail removal, controls, audio, standby/cold boot and rollback remain separate acceptance gates.
