# Shared Contracts Implementation Plan

> Execute in this isolated workspace, with focused ownership for parallel tasks and independent review before integration.

**Goal:** Consolidate existing storage, lifecycle and recovery decisions and make unexpected contract values visible in the standard diagnostic report.

**Architecture:** Reuse state-permissions.js as the canonical ES5 storage implementation, extend existing pure policy modules, and keep protocol-specific admission unchanged. Add bounded typed diagnostic events; generated package copies come from the canonical host source.

**Tech stack:** ES5 / TV Node 0.10.15+, Python 3.9+, existing native C harnesses.

**Spec:** `docs/superpowers/specs/2026-11-10-shared-contracts-design.md`.

## Global constraints

- PROGRAM/ROOT_PROGRAM, old capsules/receipts and explicit safety latches remain unchanged.
- No new permission, endpoint, version selection, frozen-candidate input or TV action.
- Source and all embedded support copies use the same canonical JS resources.
- Advice/diagnostic exports never authorize effects; async execution revalidates live state.
- Runtime power processing strings remain valid; Home Off is not Helper Stop.
- Events: <=32 / <=16KiB per report, <=512 bytes each; no arbitrary values or raw logs.
- Reuse base 850c952b green CI; npm dependencies/venv are already prepared.

## Task 1: typed diagnostics and trusted resource delivery

Files: create native/app/contract-events.js, cytv/contract_events.py and cytv/tv_sources.py;
modify scripts/build-cytv.py, scripts/build.sh, android/stage.py and helper packaging;
test new event vectors plus existing diagnostics/Android/build-asset fixtures.

Interfaces:

```js
module.exports.create = function (emit, context) {
  // Returns {record(event), snapshot()}; no throws through the caller.
};
```

```python
def safe_events(values): ...  # bounded, revalidated list

def record(event): ...       # current operation recorder; no admission effect

def trusted_source(name): ...  # fixed resource names only

def node_adapter(name, invocation): ...  # trusted static invocation, not user text
```

Additional interface details for implementation:

- JS exports `describe(value)`, `normalize(event)`, `safeEvents(envelope)` and
  `create(emit, context) -> {record(event), snapshot()}`. Python exports the
  equivalent `describe`, `normalize`, `safe_events`, a bounded `Recorder`, and
  `record(event)` for current operation context. Snapshot is
  `{schema:1, events:[...], dropped:integer, suppressed:integer}`.
- Event fields: schema, component, operation, phase, field, expected, actual,
  decision, count; optional bounded first/last timestamps. Identifiers are code
  identifiers (component/operation/phase/expected <=32, field <=64), never payload
  keys. Decisions: refuse, wait, retry, retain, ignore, complete.
- `describe` reports exact built-in type/length only. `actual` accepts only typed
  metadata keys (type, length, uid, gid, mode, size, limit, code, errno,
  os_code, reported_code, category); unknown/raw nested fields never survive.
  Category/type values are fixed safe classifications, not arbitrary strings.
- First event is retained; remaining unique events use a bounded recent window.
  Repeat counts aggregate without unbounded maps. Emitter exceptions cannot
  escape; malformed input never breaks standard report generation.
- Trusted JS names are state-permissions and contract-events. Canonical sources
  are native/app/<name>.js. Stage generated copies under cytv/tv for frozen and
  Android; source mode may read the checked canonical repository source. A
  frozen/bundled missing resource must not fall back to installed TV code.
- Task 1 validates raw ES5 for contract-events only. state-permissions becomes
  standalone ES5 in Task 2; do not duplicate or silently rewrite that module now.
- Packaging changes include app/service copies of contract-events alongside the
  existing state-permissions copy. Keep source/runtime fixture closures aligned.

- [x] Add literal vectors for invalid type/enum/mode/size and hostile nested values; prove raw markers are absent.
- [x] Verify events remain bounded under repeats/flood and failed emitters preserve original outcomes.
- [x] Implement exact-builtin summaries, identifier validation, bounded recorder and trusted resource loader.
- [x] Include allowlisted canonical resources in frozen CLI/desktop and Android; fail clearly when packaged source is missing.
- [x] Run event parity tests on configured legacy runtimes and resource/build/Android fixtures.

## Task 2: canonical storage operations

Files: native/app/state-permissions.js; cytv/no_root_observer.py; cytv/helper_stop.py;
cytv/operations.py stop writer; builders/service module staging; relevant permission/observer tests.

Interfaces added to existing callable export:

```js
prepare.inspectConfiguration(directory, options);
prepare.prepareConfiguration(directory, options);
prepare.requestStop(directory, options);
prepare.atomicRecord(directory, kind, bytes, options);
```

- [x] Add failing role-cycle tests: installer A, runtime B, normalized modes, A continuation; no package replay and unchanged latch bytes.
- [x] Add foreign apps refusal before key mutation, group/type/link/size/substitution cases and explicit read-only checks.
- [x] Extract checked directory/inode/staging primitives from existing code; use named file classes rather than arbitrary paths.
- [x] Keep runtime call signature; make apps.json runtime read-only; preserve current key adoption and exact-hash installer reclamation.
- [x] Replace only STATE_CHECK/helper_stop outer adapters with trusted source calls. Compare immutable PROGRAM/ROOT_PROGRAM bytes to base.
- [x] Wire existing Stop fallback through the shared writer; preserve actual process-quiescence checks.
- [x] Run affected permission, continuation, Stop and exact-source packaging tests.

## Task 3: lifecycle decision extraction

Files: native/app/runtime-policy.js, power-policy.js, native.js, native/prototype/relay.c;
existing watchdog/power/startup C+Node tests.

```js
policy.classifyExit(snapshot); // terminal | retry-watchdog | wait-power + effects
power.observe(payload, now);  // normalized current power facts + diagnostics
```

- [x] Characterize OS/reported mismatch, signal/Stop/latches, budget, source25 and confirmed32 with literal expected outcomes.
- [x] Add valid firmware processing-string cases and malformed/unknown values; no Boolean-only assumption.
- [x] Move classification into existing policies; workerClosed/finish execute one decision, while restart rechecks current latches.
- [x] Consolidate C T/R update helper without changing Q/D/E or pre-grab failure semantics.
- [x] Emit safe diagnostics for unexpected combinations, retaining original OS and relay values.
- [x] Run source/compiled Helper, power, watchdog, key-up/startup/IR and legacy runtime checks affected by this extraction.

## Task 4: one recovery action projection

Files: cytv/recovery_state.py, recovery.py, recovery_ui.py; state/journey/UI tests.

```python
def setup_actions(profile, pending, observation): ...
```

- [x] Add cases where raw setup flags disagree with a blocked/foreign assessment; no action may bypass the assessment.
- [x] Add saved terminal removal versus currently verified completion cases; no success from saved journal alone.
- [x] Reuse a pure action projection for assess and recovery choices; preserve existing public return shape and action names.
- [x] Keep all Installer proof readers and confirmation-time revalidation unchanged.
- [x] Add fixed unexpected-observation diagnostics and test CLI/desktop/Android action consistency.
- [x] Run recovery state, journey, UI and affected installer integration tests.

## Task 5: standard-report end-to-end context

Files: cytv/transport.py, diagnostics.py, diagnostic_context.py, errors.py,
operations.py bounded runtime projection; native log/collector integration.

- [x] Add a transport fixture with a fixed contract-error envelope; reject malformed/oversized/private additions.
- [x] Retain error_type/exit_status and attach only safe contract events.
- [x] Include bounded events in operation context, first_failure and standard report; later status failure cannot replace the first cause.
- [x] Read only safe bounded runtime events using trusted support; record legacy/unavailable telemetry explicitly.
- [x] Verify repeated logs, failed writes, unavailable telemetry, unknown field types and private-data marker exclusion.
- [x] Run report/context/transport plus desktop and Android export cases.

## Task 6: combined verification and review

- [x] Inspect every changed-source dependency and record missing evidence in one ledger.
- [x] Verify the immutable observer hashes and source/frozen/Android resource identity.
- [x] Run affected test groups and exact legacy runtimes after the whole correction batch; no unchanged full RC or TV install.
- [x] Independent code/security review of storage handoff, lifecycle races, recovery authority and diagnostic privacy/bounds.
- [x] Update developer contract references and relevant practical guides only if user steps change.
- [x] Commit and create separate reviewable PRs/stack as appropriate; preserve #488 and frozen release scope. Follow selected CI and accurately reconcile linked issue status.
