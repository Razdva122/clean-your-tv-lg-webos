# Shared storage, lifecycle and recovery contracts

This reference describes the implemented source contracts. Delivery requires a
rebuilt Helper and installer, including Android; host tests do not establish
physical TV acceptance. See the [dated verification ledger](../history/2026-11-10-shared-contracts.md)
and [diagnostic export reference](INSTALLER-DIAGNOSTICS.md#shared-contract-context).

## Storage and ownership handoff

`native/app/state-permissions.js` remains callable as
`prepare(directory, log, initializeControl)` for runtime preparation. Its named
operations share checked directory/inode reads and exclusive staged writes:

| API | Responsibility and boundary |
| --- | --- |
| `inspectConfiguration(directory, options)` | Read-only installer configuration validation. |
| `prepareConfiguration(directory, options)` | Validate key and apps before key repair; foreign-key replacement additionally requires `expectedHash` matching the original capsule's exact SHA256. Existing outer idle/process guards still apply. |
| `requestStop(directory, options)` | Validate destinations, preserve an existing blocked latch, create it if absent, then write Stop. It does not establish process quiescence. |
| `atomicRecord(directory, kind, bytes, options)` | Write one fixed named output class with checked staging and rename. It cannot target configuration, locks or emergency latches. |
| `readConfiguration(directory, kind)` | Read checked `key` or `apps` only; runtime apps reads never chmod or adopt the inode. |
| `appendLog(directory, line)` / `readLogEvents(directory)` | Bounded checked local logging / fixed safe-event projection; neither grants recovery authority. |

The pairing key's private mode is 0640. Runtime privacy repair can adopt its
inode while preserving exact bytes and shared group. Installer reclamation does
not trust a numeric runtime UID: it authenticates the original bytes as well as
metadata and the surrounding recovery guards. Foreign apps ownership remains a
refusal for installer preparation. Apps remain installer configuration; runtime
reads do not normalize legacy modes. Normal installation writes apps as 0644.

Fixed record kinds are `control`, `home-preference`, `startup-state`, `pid`,
`logger`, and `home`/`input`/`catalog` request and response pairs. Each has its own
fixed filename, role and mode. Control initialization and shared preference/
channel writes use 0660; Stop writes its command as 0644 and creates an absent
blocked latch as 0664. Existing latch bytes are preserved. `startup-state` lives
in the service namespace; visibility there says nothing about app-directory
visibility. Controller/relay locks retain their inodes and native ownership.

A synchronous session pins a no-follow directory descriptor, checks ancestors,
identity, ownership, group and accepted mode, and reads single-link bounded
regular files. Writers create an unpredictable exclusive staging inode, verify
its identity, group and mode, check the directory/destination before rename,
then clean staging on failure. Do not introduce asynchronous work inside a
session: it temporarily changes and restores the process working directory.
Existing narrowly accepted runtime directory modes and checked EPERM/EACCES
normalization warnings do not broaden installer or channel admission.

`cytv/tv_sources.py` allowlists only `state-permissions` and `contract-events`.
Source execution reads canonical repository resources; frozen desktop/CLI and
Android use staged `cytv/tv` bytes and refuse missing packaged resources. Static
host-owned adapter bodies resolve only bundled factories and necessary Node
builtins. Never supply user/remote text as an adapter invocation or execute an
installed TV module as host support. Both Helper packaging paths copy the same
compiled canonical modules into app/service sandboxes. Raw adapter resources
remain ES5 and executable on Node 0.10.15, 0.10.25 and 0.12.2.

## Lifecycle decisions

`runtime-policy.classifyExit(snapshot)` returns `terminal`, `retry-watchdog` or
`wait-power`, together with block, cleanup, terminal UI, process exit and safe
diagnostic facts. OS code/signal and the relay-reported reason remain separate.
`workerClosed` executes that decision; `finish` does not reinterpret it.

Explicit Stop, emergency reason 27 and existing safety latches prevent recovery.
Power exit 32 requires the tracked child, matching OS/reported values, no signal,
a current worker-bound power deadline and no watchdog latch. Watchdog retry
requires the existing exit/owned-kill proof, cleanup before replacement and the
five-attempts-per-ten-minutes budget. Restart callbacks re-read current Stop and
latch state. Source exit 25 retains its existing initial blocking/cleanup rules.
Unknown combinations retain the terminal fallback and bounded diagnostics.

`power-policy()` returns `observe(payload, monotonicNow)` plus the existing
`next(payload)` compatibility method. Observation provides the T/R command,
15-second power deadline, settled/resumed facts and wake/presentation cancellation.
Firmware processing strings such as `Request Power Off`, `Screen On` and
`Prepare Power On` remain valid; truthy processing delays settled Active.
Home preference Off is separate from explicit Helper Stop.

C owns actual release/ungrab/close results. Its shared T/R handler preserves the
startup Q29 versus running Stop0 distinction. Triple Home, key-up delivery,
watchdog cleanup and unrelated input remain native safety responsibilities.

## Recovery advice and admission

`recovery_state.assess(profile, pending, observation)` retains its public
state/reason/actions shape. `setup_actions(...)` projects setup choices only
after the full assessment applies ownership, operation, pending and proof
priorities. `recovery.py` consumes that projection for CLI, desktop and Android.

Product-backed installation needs matching complete/current product evidence
before setup-ready advice. A raw readiness boolean cannot override failed,
foreign or stale product proof; uninstall never gains setup choices from it.
Historical activation/updater observations keep their protocol-specific support.
Restoration capability does not imply activation capability; the C1 native gate
does not gain a Home-off completion action.

A saved verified-clean removal remains historical until current backend
verification. The interface says Verifying removal and cannot announce success
from the saved journal alone. Missing/failed observation remains unverified.
Every mutating backend still re-reads the original receipt and live proof after
confirmation. Neither safe summaries nor diagnostic events can authorize effects,
clear pending, rewrite capsules or replay package installation.

## Diagnostics and limits

The ES5 `contract-events` and Python `contract_events` modules normalize typed
metadata and retain a first-cause/recent-context window. Events contain fixed
schema/component/operation/phase/field/rule/decision identifiers, safe actual
metadata, bounded counts and optional numeric timestamps. Unknown strings expose
type/length and fixed categories; arbitrary objects are never serialized.

A standard report shares at most 32 events / 16 KiB of compact projection across
all known current and retained locations, at most 512 bytes per event. Copies
occupy one location. Same-operation recorder reconciliation preserves counts;
report allocation across operations preserves each original event's own count
and timestamps. The retained first failure keeps its original diagnostic ID.

The trusted adapter's fixed error envelope is validated before safe events attach
to `TVCommandError`; original error type/SSH exit status and Root driver parsing
remain separate. Report and history export revalidate fields and concrete producer
vocabularies. No credentials, paths, inventories, arbitrary exception text or raw
log lines are included. There is no external telemetry endpoint.

Existing authorized No-root status/read probes collect only checked fixed
`controller.log` / `controller.log.previous` safe projections, each file capped
at 128 KiB of UTF-8 bytes. Telemetry is `read`, `legacy` (no instrumented evidence)
or `unavailable`; none is proof that an operation passed. Logger failure is best
effort and cannot hold cleanup or replace the original failure. Unsafe/unwritable
storage cannot retain new telemetry; older logs cannot reconstruct missing causes.
Creating/saving the standard report is local and does not trigger a device probe.

## Remaining acceptance

No physical TV, firmware/webOS or remote was exercised for this batch. Host UID
role-cycle fixtures substitute identity metadata while using real host inodes;
they do not prove retail ownership policy. Final versioned artifact provenance,
desktop/Android packaged execution and affected physical recovery, Home, power,
input/emergency and update/rollback scenarios belong to the release coordinator's
scoped acceptance. No release, compatibility or original-issue resolution follows
from the development checks alone.
