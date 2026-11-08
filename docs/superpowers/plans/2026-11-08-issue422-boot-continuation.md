# Root boot continuation implementation plan

**Goal:** Preserve the owned Root Home route through normal startup without delaying the UI, while retaining independent emergency recovery.

**Architecture:** Adopt only an exact owned retained profile from confirmed enabled intent, with no surviving predecessor protection processes. Rotate the routing transaction using a durable recovery record, keep the original baseline/file identity, and arm a fresh bounded guardian and recovery-only input supervisor before the normal boot gate. Release persistent health only after the existing normal marker/failsafe gate; any uncertainty restores the original baseline. Live predecessor/snapshot cases retain conservative recovery rather than losing queued or partial emergency gestures.

**Constraints:** No UI wait, automatic emergency reset, watchdog extension, foreground launch, successful-install acceptance claim, or release metadata change. Use existing Python/JS dependencies and focused tests. This is an independent follow-up fix branch; final signed artifact and physical acceptance are separate gates.

- [x] Reproduce the route gap with an executable boot regression; run it against the old dispatcher and observe failure. Cover retained ownership, original baseline and stale predecessor refusal.
- [x] Extend the existing boot_gate runtime entry with a narrowly scoped continuation journal and lifecycle event. Test interrupted record/intent/journal/binding writes and recovery. Keep recovery-only input supervision bounded with the existing two-second watchdog and original sixty-second deadline.
- [x] Route eligible normal boots through continuation; preserve legacy/mismatch/failsafe/off recovery. Test gate failure, observer failure, explicit off, duplicate dispatch and stale callbacks.
- [x] Run Root runtime and affected host checks, independent review, document the new private record and limitations, and prepare an implementation PR targeting release/next. Do not claim TV acceptance from host simulation.

Validation: full Root suite 1,154 tests (three platform skips); focused safety suites142; installer/setup/System integration319 (one platform skip); formatting, Python compilation and diff checks pass. Independent safety review completed. Physical signed-package/device acceptance remains pending.
