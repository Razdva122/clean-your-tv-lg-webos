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
| `requestStop(directory, options)` | Publish a new Stop generation, recover known firmware-expanded storage, preserve or create the blocked latch, and write the Stop command. Process quiescence is checked by the caller. |
| `atomicRecord(directory, kind, bytes, options)` | Write one fixed named output class with checked staging and rename. It cannot target configuration, locks or emergency latches. |
| `readConfiguration(directory, kind)` | Read checked `key` or `apps` only; runtime apps reads never chmod or adopt the inode. |
| `appendLog(directory, line)` / `readLogEvents(directory)` | Bounded checked local logging / fixed safe-event projection; neither grants recovery authority. |

The pairing key's private mode is 0640. Runtime privacy repair can adopt its
inode while preserving exact bytes and shared group. Installer reclamation does
not trust a numeric runtime UID: it authenticates the original bytes as well as
metadata and the surrounding recovery guards. Foreign apps ownership remains a
refusal for installer preparation. Apps remain installer configuration; runtime
reads do not normalize legacy modes. Normal installation writes apps as 0644.

A caller may repair its own boot-expanded key in place. A trusted packaged
owner permits reading an already private key; it does not grant mutation rights.
A noncaller key needing privacy repair uses the same exact-hash authenticated
replacement path as an untrusted foreign key, creating a caller-owned 0640 inode.
An already private trusted packaged key remains unchanged.

Firmware-expanded 0777 records use the same checked storage session. Bootstrap
copies only the retained key and Home/startup values from a caller-owned or
packaged inode into a private replacement. This preserves preferences and
restores permissions; SSAP still authenticates the credential. Ordinary
configuration reads remain strict. Helper leaves installer-owned apps alone;
if that list is unavailable it uses the existing authenticated TV catalog,
with a bounded retry after a transient failure. The installer can restrict its
own apps inode in place without changing its owner or contents.

Fixed fresh outputs can replace an expanded same-group leaf without using its
old contents. This applies to control/PID/logs, startup writes and all channel
request/response classes under their existing directory rules. Stop preserves
an existing regular latch; it still refuses unsafe directories and links.
The installer, standalone Stop, No-root cleanup and Root coordinator and
edition handoff use the same checked Stop writer. Cleanup can retain the
SDK's legacy directory mode when the checked caller cannot normalize it,
while a normal Stop requires successful normalization before claiming
completion. The controller uses its
latch-preserving operation when it terminates. The native input relay uses
the same generation and latch format on its synchronous emergency path.
Bootstrap never clears Stop/watchdog or replaces native locks.

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

Group access uses the session's captured OS identity: UID 0 can access the
packaged group without membership; other callers must hold its primary or
supplementary group. This supports Root SSH Stop while a successful disable
reply is still waiting for the controller to exit. Caller options and telemetry
cannot grant this capability. Trusted directory ownership, matching
configuration/directory groups, foreign-key exact-hash proof and all inode,
mode, link and type checks still apply. UID 0 with insufficient kernel rights
still fails the actual read/write/chown/chmod operation and checked staging;
group admission does not waive syscall failures or establish Helper quiescence.

`cytv/tv_sources.py` allowlists `state-permissions`, `contract-events` and
`boot-proof`.
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


## No-root removal restart evidence

`native/contracts/boot-proof.js` owns kernel UUID parsing, proof validation and
`boot-create`, `boot-probe`, `boot-retire`, `boot-release` via `run(input, context)`.
The host embeds these exact trusted bytes in the standalone cleanup program;
Root updater embedding therefore remains self-contained. It uses the same
staging infrastructure as storage contracts, without adding unused code to the
Helper package. `readKernel()` provides the same identity validation to inventory.

The one current No-root journal record is `cleanup_boot_proof`; the legacy
`cleanup_boot_id` field is cleared when capturing it. Existing schema-1 proofs
retain private per-goal markers on a real root-owned sticky `/tmp` (01777),
including inode/content checks. Captured proofs never switch kinds on retry.

The Developer Mode SSH layout with a real root-owned `/tmp` of exactly 0111
captures schema 2 (`kind: kernel-only`, goal and kernel UUID), without opening,
reading or writing that directory. Only a changed kernel UUID proves a restart.
Marker absence, successful release, elapsed time and a repeated UUID do not.
The same-ID snapshot/cold-boot case stays pending with diagnostic guidance;
there is no alternate marker in persistent or nonsticky shared storage.
Other modes, owners and symlinks remain refusals. Root SSH cannot select this
fallback; Root's separate runtime `boot_identity` contract remains unchanged.

This evidence does not replace process, control/startup, package/file and
previous-operation checks. Unknown prior operations retain the restart gate.
See [the focused verification record](../history/2026-11-11-issue472-devmode-boot-proof.md).
