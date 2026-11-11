# Shared state, lifecycle, recovery and diagnostics contracts

## Scope

The maintainer requested a systemic improvement based on a retrospective of 60
issues, then explicitly required useful logging of unexpected values. This v1
improves the existing No-root shared-state boundary, Helper lifecycle decisions
and host recovery advice. It preserves protocol-specific execution authority.
It is not a replacement Root backend or a generic recovery framework.

Base: 850c952b, the fully verified draft #488. Development is isolated on
`codex/shared-state-contracts`. No frozen 1.16.0 scope, selected artifact,
component version or TV changes are authorized by this design.

## Evidence and problem

The full issue register contained 144 issues and 927 comments when collected.
The targeted retrospective deeply examined 60 distinct issues and their directly
related implementation evidence. It is not a representative failure-rate sample.

- #140, #437 and #487 expose an incomplete ownership handoff between installer
  and native runtime. Shared group access does not grant chmod authority.
- #378/#390 and #409 show why a safe storage invariant cannot be expressed as
  one universally writable directory.
- #155, #104 and #487 show that shutdown, watchdog recovery and explicit Stop
  need different transitions. Home preference Off is not Helper Stop.
- #111 and #165 show that historical version/completed evidence is not current
  pending work. #201/#240/#418 distinguish restoration from activation capability.
- #59 shows that unavailable observation is not proof of absent functionality.
- #489 demonstrates inconsistent package/verifier size contracts, but its frozen
  release correction remains owned by the current release coordinator.

The current tree already has useful boundaries: state-permissions.js,
runtime-policy.js, power-policy.js and recovery_state.assess(). Extend those
rather than introducing parallel decision engines.

## Alternatives

1. Keep narrow fixes and document their assumptions. Cheap, but leaves divergent
   writers/validators and duplicate lifecycle/action interpretation.
2. Consolidate executable contracts in the existing modules and add bounded
   diagnostic evidence at their boundaries. Selected: it preserves paths and
   authority while making future changes testable across consumers.
3. Introduce a storage broker, new state directory and generic recovery adapters.
   Deferred: it requires new authority, migration and device acceptance without
   being necessary for these verified failures.

## Non-negotiable invariants

- PROGRAM and ROOT_PROGRAM in no_root_observer.py remain byte-identical to base.
- Existing capsule bytes, operation IDs, receipts and historical executable
  identities remain valid. Advice and diagnostic events never grant effects.
- Do not clear blocked/watchdog or interpret Home Off as explicit Helper Start.
- Preserve triple Home, key-up delivery, cleanup-before-watchdog-restart,
  five-retries-per-ten-minutes and existing deadlines.
- Do not read or execute a retained TV JS module as installer support.
- Do not admit arbitrary foreign configuration owners, paths or modes.
- No package install is replayed to recover a configuration failure.
- No new endpoint, service grant, automatic supervisor migration or device test.
- Logging is bounded, best effort and non-authoritative; failure to log cannot
  replace the original failure or prevent release of input resources.

## 1. Shared storage contract

Canonical executable source remains `native/app/state-permissions.js`. Preserve
its callable export for existing runtime consumers and expose these concrete
operations as function properties:

- inspectConfiguration(directory, options): read-only validation;
- prepareConfiguration(directory, options): authenticated installer preparation;
- requestStop(directory, options): preserve/create stop latch, then write Stop;
- atomicRecord(directory, kind, bytes, options): fixed named runtime/service
  output classes only, never an arbitrary destination/path policy engine.

The existing runtime entry prepares controller-owned control state and pairing
privacy. It stops chmod attempts on read-only installer-owned apps.json.

| File class | Ownership and mutation contract |
| --- | --- |
| ssap-key.json | Secret 0640. Runtime may adopt the inode only for necessary privacy repair while preserving bytes/group. Installer may reclaim a foreign key only when exact bytes match the original capsule SHA256 and all existing metadata/idle guards pass. |
| apps.json | Installer configuration, 0644. Runtime reads without chmod/re-own. Validate together with key before first mutation; foreign ownership still refuses. |
| control.json | Existing shared-group command channel, 0660 for controller initialization. Each writer uses its own staged inode. Stop preserves existing safety evidence. |
| blocked/watchdog | Safety evidence; ordinary preparation never deletes, replaces or truncates existing bytes. Explicit existing resume remains the only clearing authority. |
| controller.lock/relay.lock | Inode-stable native locks. Never pass through atomicRecord, rename or ownership repair. |
| PID/logs/preferences/channel responses | Runtime output with explicit named writer and mode. Exclusive staging and checked rename; data is not configuration or recovery authority. |
| startup-state.json | Service-owned state in the service namespace; no inference about app-directory visibility. |

Shared internal primitives pin a no-follow directory descriptor, validate its
identity/security attributes, read a checked single-link bounded inode, stage
exclusively, set the checked shared GID and verify before rename. Stage cleanup
runs on failure. The module uses ES5 syntax and Node 0.10-compatible APIs even
before compilation because the installer streams the same trusted source.

`cytv/tv_sources.py` loads only explicitly allowlisted host resources. Source
checkout uses the canonical repository file; frozen/Android packaging stages
that same file under cytv/tv. Missing packaged resources fail before mutation.
Its CommonJS wrapper embeds the canonical module and contract-events dependency;
it never resolves installed TV paths. STATE_CHECK and helper_stop.PROGRAM become
thin adapters retaining their existing success markers and command interface.

Both normal Helper packaging paths continue copying the same canonical source
into app/service sandboxes. Frozen CLI/desktop and Android explicitly stage the
trusted JS resources; no manually maintained source-string copy is introduced.

## 2. Helper lifecycle contract

Extend runtime-policy.js with pure classifyExit(snapshot). Inputs preserve OS
code/signal separately from reported reason, tracked-worker identity, READY,
watchdog-kill proof, current monotonic time, worker-bound power deadline, current
stop/latches and remaining retry budget. Output:

    {action, block, cleanup, terminalUI, code, signal, reportedReason, diagnostics}

Actions are terminal, retry-watchdog and wait-power. Explicit Stop/reported27 or
an existing emergency latch wins. Exit32 requires all current #488 evidence.
Unknown combinations keep the existing terminal fallback and emit diagnostics.
Exit25 retains its current no-initial-block behavior and existing cleanup rules.
workerClosed executes the decision; finish consumes it instead of independently
reinterpreting the same facts. Async restart still rechecks current stop/latches.

power-policy.js owns observe(payload, now), returning command/deadline,
settledActive/resumed/cancelWakeWait/cancelPresentation and diagnostics. Preserve
existing next() compatibility. Recognized processing includes firmware strings
such as Request Power Off, Screen On and Prepare Power On as well as the existing
boolean/absent forms; do not invent a Boolean-only grammar. This first extraction
preserves the existing interpretation rather than broadening power exceptions.

C remains the authority for actual release/ungrab errno and close outcomes.
Node remains the authority for tracked child/stop/lifecycle. Consolidate T/R
handling in a small C helper shared by startup_pump and the running loop, keeping
startup Q29 distinct from running Stop0. Do not move evdev proof into Node or
introduce a C JSON parser/generator framework.

## 3. Recovery advice contract

Extend recovery_state.py, retaining assess(profile,pending,observation)'s public
state/reason/actions shape and protocol-specific Installer proof readers.

- One setup-action projection determines continue-setup and finish-home-off;
  recovery.py must consume it rather than re-derive eligibility from raw flags.
- Missing/failed observation remains unverified, not absent or terminal failure.
- Saved verified-clean is historical evidence until current backend verification.
  The UI continues saying Verifying removal; saved state alone cannot show success.
- Restoration capability never implies activation capability. Do not add a new
  Home-off completion path to unsupported Root backends.
- Every mutating backend still re-reads original receipt and live proof after
  user confirmation. Do not rewrite old capsules or Root historical programs.

Use existing field/reason/action vocabulary where possible. No new generic
adapter layer or durable receipt format is required.

## 4. Contract diagnostics

Canonical ES5 helper: native/app/contract-events.js. Host counterpart:
cytv/contract_events.py. Shared scenario vectors test the same wire semantics;
no third-party logging service or new telemetry endpoint.

Each violation records schema=1, component, operation, phase, field, expected
rule ID, safe observed description, decision, diagnostic correlation and bounded
repeat count. Components/field/rule IDs are developer-defined identifiers, not
payload keys. Preserve original OS/reported exit values for lifecycle analysis.

Observed values are explicit metadata: types, lengths, numeric modes/UID/GID,
size/limit, known enum categories and numeric status/errno. Do not recursively
serialize arbitrary objects, file bytes, exception messages, paths or credentials.
Unknown strings keep type/length and a bounded categorical description rather
than being silently discarded as a generic unknown or exported verbatim.

Limits: at most 32 projected events / 16 KiB per report, at most 512 bytes per
event; repeated identical violations aggregate. Keep the first failure and the
latest bounded context. Reporter failures are swallowed independently of the
original control/recovery result. Runtime events use existing controller logs
with bounded rotation; ordinary report collection reads only the fixed bounded
safe-event projection through trusted SSH support, never exports raw logs.

The trusted Node adapter emits a small fixed JSON error envelope and nonzero
exit status. transport.run revalidates only this envelope and attaches safe
contract context to TVCommandError; root-driver parsing remains unchanged.
operation_context stores bounded host events and create_report/failure_summary
include them in standard Save diagnostic report and retained first-failure history.
A diagnostic projection is never fed back as operation admission.

Instrument storage validation/repair, relay exit/power interpretation, recovery
action/observation classification and malformed contract error envelopes.
Expected missing optional fields are not violations. Older Helper/retained
programs without new events remain supported and telemetry availability is
explicit; absence of events does not mean an operation passed.

## Rollout and verification

1. Characterize existing contract decisions before extracting them.
2. Add diagnostic schema/resources and boundary tests, including hostile values,
   flooding and failed log writes, before wiring production collectors.
3. Consolidate storage and wire exact-source packaging; keep immutable observers.
4. Extract lifecycle decisions and centralize recovery action advice.
5. Exercise complete writer/reader cycles and standard-report export.
6. Review the combined batch and run affected host/PR gates once. Reuse unchanged
   #488 evidence; rerun only changed tests/dependencies before combined CI.
7. Keep the implementation outside frozen release scope. A future coordinator
   versions/rebuilds affected Helper/installer/Android components and selects
   exact-artifact acceptance. No TV compatibility or delivery claim from host tests.

Required scenarios include A-installer/B-runtime UID cycles, reboot modes,
foreign apps before any key mutation, shared/unshared groups, all link/type/mode
and substitution refusals, stable locks/latch bytes, before-READY Stop, same-boot
wake/Home Off, watchdog limits, old/unknown capsules, historical completion,
changed receipt after confirmation, unsupported activation with supported
restoration, and first-error diagnostic retention without private values.
