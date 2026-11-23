# Embedded LG Home adapter

W17M, reported in [#410](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410), motivates an adapter for TVs whose LG Home panel lives inside the Qt compositor rather than `/usr/bin/com.webos.app.home`. Selection follows observed capabilities, not a model, firmware or SDK allowlist. This implementation and offline evidence do not establish physical TV compatibility or a fix for the reporter's installation.

## Shared backend and admission

The adapter reuses the [C1 compositor backend](C1-NATIVE-GATE.md): the `c1-native-gate` backend name, `compositor-keyfilter-v1` routing, LS2 broker, independent native guardian, controller lease, stop latch and emergency-input reader remain shared. Descriptor schema4 uses the same six marker fields and generic identity observations as schema3. The recorded target fingerprint identifies the compositor binary. Historical schema1 mount recovery and schema2/3 native-Home paths retain their own recovery contracts.

Admission requires an explicitly absent System Profile service, ARM32 userland and compositor, the protected `surface-manager-starfish` executable with `LSM_MAIN_QML` and `qrc:///main.qml` capabilities, an inspectable Upstart compositor job and bounded start/stop/status operations. Runtime checks also require trusted ownership, stable target identity, no conflicting Home integration or covering mounts, and an independent input channel advertising Home and Back. Model, firmware and SDK values are observations with validated syntax; they do not choose compatibility.

The QML wrapper loads LG's own `qrc:///main.qml`. It discovers a unique `handleSystemKeys` policy by its exposed function name and checks the exposed readiness, access and modal-alert state before intercepting Home. It preserves the other policies and delegates to LG when routing is unavailable. No fixed policy count or array position is assumed. A tagged, authenticated compositor lease proves that the wrapper attached; a process environment value alone is insufficient. The read-only `c1AdapterStatus` method exposes that proof only to hub-authenticated `com.webos.lunasend-*` callers through a separate LS2 permission group. It grants no administrative methods.

## Launch transaction and recovery

The external wrapper and controller script are included in the recovery manifest's hashes. Existing bundles without these assets retain their historical inventory; an embedded selection requires both assets. No LG QML, executable, Upstart job or vendor LS2 role is modified.

An explicit Enable starts a detached supervisor before changing the compositor. A root-owned journal records the boot identity, job hash and transition phase; a transition lock serializes attachment and restoration. The supervisor stops the compositor job and starts one instance with `LSM_MAIN_QML` pointing at the external wrapper. It verifies the new process identity and environment, then waits for actual broker attachment before reporting success. Parent death or cancellation during attachment triggers stock restoration. A failed or interrupted transition retains recovery evidence instead of retrying activation in a loop.

After attachment, controller or broker death revokes/expires the shared lease. The resident policy then passes the next short Home sequence to LG's original handler, which opens its panel. This fallback does not restart the compositor and does not depend on a surviving CYTV controller. The native guardian and independent emergency reader retain their shared stop behavior. Lease expiry and an already-held key remain timing boundaries to test; the claim is not instantaneous fallback at the instruction that delivers SIGKILL.

Explicit Off, restoration and removal return the compositor to `LSM_MAIN_QML=qrc:///main.qml`. They verify the running executable and stock environment and retire the supervisor before deleting adapter resources. An uncertain restart, changed job or failed readback retains the journal and files. Recovery can start stock after an interrupted stop left the job waiting.

The owned startup recovery path reconciles interrupted work to stock. A cold boot starts with the factory entry file because the wrapper environment belongs to the previous Upstart instance. It requires explicit **Change Home** to activate CYTV again. Schema4 does not inherit schema3 automatic rearm or lifecycle return: closing content does not automatically reopen CYTV. Normal Root OTA remains disabled for this backend.

## Offline evidence and remaining device checks

The stock ARM Upstart/initctl utilities have been exercised offline with a D-Bus session: a per-launch entry-file environment reaches its instance, and a later ordinary start leaves it unset. This establishes the launch mechanism without persisting an override in LG's job configuration. It does not reproduce the complete TV startup sequence.

Focused fixtures cover capability admission, authenticated attachment, shared lease loss, emergency stop, launch cancellation, interrupted restoration, asset integrity, stock readback and removal. See the [dated evidence](../history/2026-11-20-embedded-home-adapter.md) for the exact firmware/QEMU inputs and observed results.

Physical Magic Remote routing, visual panel presentation, audio, HDMI, standby, AC cold boot, service activation permissions and recovery on an actual target TV remain hardware acceptance gaps. A successful offline run or package installation is not evidence for those cases. Do not replace an existing schema1/2/3 marker or helper to migrate an installed backend; recover and remove it through its existing path first.

Embedded Beta removal verifies the restored registration snapshot and an exact hub missing-service reply for the lease alias after a scan. This proves activation retirement without requiring a newer permission-query API; uncertain responses preserve recovery state. Historical backend removal keeps its original contract.
