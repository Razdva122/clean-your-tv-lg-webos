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
