# Forward Home cancellation investigation — 2026-11-02

Scope: the unresolved forward-update portion of #202 after published v1.6.0.
This investigation contacted no TV and changed no product/runtime behavior.
The active retained rollback accepted for #222 is a separate scenario; #206's
published-version Settings check remains outstanding under its existing request.

## Historical path

The published v1.5.2 source is commit
`142ca6a2eb5528a8d34f36fdd02d1a16c016e1fb` (Root/infrastructure 0.6.1,
Root Updater 0.3.3, System 1.1.2). Reading the original functions establishes:

1. `system-updater/device.py:Device.suspend` verifies Root integrity, reserves
   the transaction, calls `runtime('suspend-update', id)`, then launches LG Home.
   `Device.runtime` allows only status/suspend/finish/abort, not explicit Restore
   or boot. The original System caller does not directly cancel Home resume.
2. Old `update_guard.suspend` captures active intent and invokes `_restore`.
   `intent_runtime.restore` calls `Coordinator.exit`; that method disables intent
   and recovers the bound route. It does not call `update_guard.cancel`.
3. The old CLI's two automatic boot fallbacks call `main('restore')`. That
   explicit path calls `cancel` before intent recovery. PR #205 already separated
   these paths in new runtime bytes. A previously loaded old caller is unchanged.
4. `persistent_recovery.bound_exit` calls `cancel` for bound `escape`, but ordinary
   fault recovery does not. Neither source inspection nor the cancellation
   receipt identifies which of these external entries ran during the failed QA.

Original complete-source SHA-256 values, for reproducible comparison:

| Source | SHA-256 |
| --- | --- |
| `system-updater/device.py` | `afdbb391c16ce3b6657c4edc735df5a30335301a550b5ec8a160b31b1b895a75` |
| `root-edition/runtime/update_guard.py` | `1b0b86b31a23f4071415bde2030945fb66d354ea5818fdf877d84debda5c82a3` |
| `root-edition/runtime/intent_runtime.py` | `d91fa2771e63d2ae3a680cf7caf42c765a66ac9a64e2edb0110c5b8b95925d24` |
| `root-edition/runtime/persistent_recovery.py` | `16535c39ff9ac18bf637779202c764dbdd5c16bb6faa47e0f278c33f55be9a03` |

## Recovered evidence and its limit

The original maintainer QA chat was inspected after searching local project,
worktree and temporary artifacts. The named private QA directories no longer
exist. Its saved monitor source and emitted summary confirm the already recorded
result: active before/desired true/attempted false, cancelled, cancellation older
than the new CLI file, installed CLI matching the new source. The monitor saved
file metadata and state; it did not record the cancelling process or callback.
No caller trace was recovered. Raw chat output and private diagnostics are not
included in this record.

The existing frozen CLI fixture reproduces a possible delayed automatic callback.
The additional characterization test executes that same historical callable as
both `boot` and explicit `restore`, against equal synthetic pending transactions.
Both leave the ticket unchanged, the same disabled intent and byte-identical
cancellation receipts. Current `finish` correctly returns cancelled without
activation for either entry. Device routing IO is synthetic; this is an evidence
boundary test, not a replay of the unidentified TV callback.

The missing input is the authenticated callback/process entry and its ordering
relative to reservation, suspension, Root app/Updater terminals and infrastructure
replacement on the original active-forward transition. A receipt alone cannot
supply it. A new guard must not infer automatic cancellation from timing, erase an
old receipt or reinterpret it as permission to enable Home: the identical receipt
can represent owner Off. Existing emergency, fault, transaction, boot, version,
health and attempted-once gates remain authoritative.

## Next boundary and verification

A separately authorized bounded exact-package forward session remains necessary
if no original caller trace is recovered. Capture fixed operation classes and
transaction-relative ordering; retain raw evidence privately. Do not replace the
retained System supervisor, keys, permissions or receipts, or change startup
policy to manufacture a pass. No new physical session is authorized by this
investigation. The original report remains unresolved; this PR is not a fix.

Fresh host checks: 34 update/Home-resume tests and seven immutable-supervisor
rollback-anchor tests pass. The latter run with pinned `fonttools==4.60.1` from
`scripts/build-requirements.txt`; an initial run without that dependency failed
before fixture setup. These tests cover update, rollback, explicit cancellation,
emergency binding, failed recovery and interrupted staging, but establish no
new hardware acceptance. No full candidate build, signing or release was run.
