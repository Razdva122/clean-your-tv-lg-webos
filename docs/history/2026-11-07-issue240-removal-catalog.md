# Root removal catalog fallback and bounded failure detail

This source follow-up for #240 targets the unfrozen candidate after v1.10.0.
It does not establish the original installation cause or recovery on a reporter's
TV. No TV was contacted, no private diagnostic was republished, and no new owner
action is requested by this record.

## Change and boundaries

Root removal previously depended on the Developer Mode application-catalog
method. A negative bus reply could stop control restoration with only a generic
RuntimeError. The remover now tries the ordinary application catalog once after
a recognized refusal or timeout. Root's existing service already uses that
ordinary catalog; no service, credential, permission or endpoint provisioning is
added. A malformed protocol or inventory remains a blocker, as do two failed
catalog reads. Only the two exact catalogs and the existing activity-list method
receive the bounded 2 MiB reply budget; other calls retain 64 KiB.

The final Node cleanup uses the same fallback and still verifies fixed package
paths, registrations, activities, routing and restart proof before completion.
The Python cleanup retains its existing confined sweep for unregistered SDK
residue: an empty package directory is not evidence that a package is registered
and must not cause another removal request. No inventory exception can bypass
control restoration, original-worker fencing, terminal handling or final absence.

The first cleanup failure remains immutable. A separate last_failure records the
latest failed attempt and cleanup stage. Bounded bus failures add only a fixed
call identifier/reason and an optional signed 32-bit code. Both producer and host
exporter filter these fields; raw exception text, error strings, payloads,
inventories and route values are excluded. Older discarded errors cannot be
reconstructed. The field is diagnostic evidence, never recovery authority.

## Verification

Regression-first failures were observed for catalog fallback, catalogs above
64 KiB, precise negative-bus detail, first/latest failure separation and finalizer
fallback. A later malformed-envelope regression demonstrated that a valid
fallback could otherwise conceal a broken primary protocol; this now blocks.

Local macOS checks used the project's existing Python environment and Node
v23.11.0. Tests model TV replies/files and do not establish retail firmware
compatibility:

- Root cleanup: 55 tests passed, including fallback across restart, orphan SDK residue,
  both catalogs denied, malformed replies and unchanged routing safeguards.
- Root finalizer: 36 tests passed, one platform skip; the fallback cannot hide a
  surviving owned path and malformed/two-denied catalogs retain the runtime.
- Root driver: 51 tests passed, including legacy status caller identity and
  retained first-failure behavior.
- Bounded Luna reader: six tests passed, including actual child-process replies,
  timeout/reaping, large catalog acceptance and unchanged limits on other calls.
- Host diagnostic context: 32 tests passed, including the final exported JSON,
  malicious fields and distinct current failure details.
- Current Root Updater package built successfully. Generated Root/Updater/System
  package and infrastructure compatibility passed on Node v23.11.0, including
  fixed path inventories, signatures, TLS and Python-binding tamper checks. Exact
  Node 0.12/8 execution was not selected locally; no legacy runtime claim is made.
  Host/Android suites and selected CI are tracked in the PR.
- Prettier verification and git diff checks passed before review.

Independent review caught two initial problems: interpreting filesystem residue
as a registered application, and introducing an installer-only import into a
persistent worker. Both were removed; a cleanup/restart regression now leaves
an unregistered package residue through the actual fixture sweep and asserts no
redundant package-removal submission. Final source review found no blockers.

## Packaging, documentation and remaining acceptance

Rebuild Root Updater/installer support and all embedding desktop/Android installers
through the normal candidate process. No release/component version or build pin
is selected here; the candidate coordinator owns freeze and final acceptance.
The shared Luna/LS2 reader also ships in updater infrastructure, so future versions
and exact inventory/package/feed/rollback checks must include those changed bytes.
Published Helper bytes are unchanged.

The developer diagnostic reference and recovery matrix describe the new behavior.
Existing user removal/retry controls, text and translated setup steps do not
change; no owner should clear app data, replace saved connection identity, edit
journals or repeat installation to populate a report. Save/share remains explicit.

Physical model, firmware/webOS, remote and installer-device acceptance for these
bytes are unknown/untested. Home routing, ordinary controls, audio, standby, cold
boot, OTA, rollback and owner recovery are untested. Local modeled success is
not a completed installation/removal report or a universal compatibility claim.
The original #240 issue remains open until its actual remaining work is resolved.

## Candidate integration

PR #379 merged into release/next as 2f3724a6 at the maintainer's explicit request
without waiting for CI. Selected Tests run 42359748100 was pending at handoff;
this is not passing combined-candidate evidence. The broader local
installer/setup/Android command was interrupted before completion and is not
claimed as a pass. The targeted module/package checks above remain the actual
local evidence. Candidate #374 retains its version/build/physical acceptance
gates; this source integration is not public delivery or owner recovery.
