# Installer diagnostic evidence (unreleased)

The shared desktop, console and Android installer now exports diagnostic context
without treating it as recovery authority. These changes are in source only;
v1.5.4 does not contain them. No TV compatibility or completed recovery follows
from a diagnostic report.

## TV Node version (next candidate)

Root and No-root preflight and status checks read `/usr/bin/node --version`
before checking other requirements. Diagnostic `tv.node_version` retains a
validated numeric version, including an older version rejected by admission.
`tv.node_version_status` distinguishes `read`, `missing` (no file or symlink),
`launch-error` (present but execution failed, including a broken symlink or
missing executable permission), `invalid-output` (a successful command without
a recognized version), and `unavailable` (the read could not be completed).
Each new read clears any previous version so an older observation cannot be
reported as current after failure. Both fields survive failure-history export.

This optional read never replaces or relaxes the existing Root, Root Beta or
Helper runtime probes. A version-read failure does not hide the primary failure
or authorize package preparation. Only the validated version and fixed status
are exported; raw command output, stderr and exception text are excluded.
No new TV installation, configuration, permission or endpoint is introduced.

## Network connection causes (next candidate)

During `ssh-connect`, inspect typed socket errors, including the values of
Paramiko `NoValidConnectionsError.errors`. `EACCES`/`EPERM` map to
`ssh-access-denied`, `ECONNREFUSED` to `ssh-refused`, and socket timeouts to
`ssh-timeout`. Mixed causes and other errors retain `ssh-unreachable`; a host
unreachable error does not establish that macOS Local Network permission was
denied. Diagnostics export only these allowlisted codes, never the address keys,
exception text or raw errors. Trust, authentication and local key-file failures
retain their separate guidance. Classification is limited to initial connection.

Desktop connection guidance replaces the scrolling report/checklist at failure
with the cause, next step and explicit Doctor recheck. Doctor checks prerequisites
and status; it does not submit package installation or resume setup. Its usual
SSH trust/authentication prompts and saved-profile checks still apply. Edited
connections are validated before running Doctor. Pending operations keep their
original identity and recovery flow; no new edit/recheck shortcut is offered.
On macOS, settings access is a user action, not an automatic permission change.
Settings may show an older duplicate name; the app does not claim to read that
permission state.

## Optional Root input inventory (next candidate)

Root setup still requires a validated, nonempty application catalog. An unavailable
EIM input snapshot no longer discards that catalog: setup warns and continues
with an empty captured input list. A successful snapshot is preserved; malformed
host envelopes, failed/empty application reads and SSH failures remain blocked.
The shared installer checklist retains `inventory: unknown` for this partial read.
Home can add inputs through its existing live status reader when available;
inputs may remain absent while the TV refuses that reader.

`tv.root_inventory` independently projects `applications` and `inputs` as `read`,
`unavailable`, `invalid` or `unknown`. `unknown` means the boundary did not produce
a classified result. Only these fixed keys/values are exported, including in
failure history. No IDs, names, raw replies or exception text are retained there.
This fixes a reproduced source failure path; it does not establish the cause or
resolution of a reporter's device failure. Rebuild installers to deliver it.
No TV package, permission, endpoint, persistent device state or pairing changes.

## Root inventory failure detail (unreleased, #397)

`tv.root_inventory_failures` retains independent `applications` and `inputs`
failures from the fixed Root SSH reader. Each entry contains a fixed `reason`
and, for a negative Luna reply, an optional signed 32-bit integer `error_code`.
Reasons distinguish root-required, client-start-failed, client-error, timeout,
oversized-reply, negative-reply, permission-denied, service-missing,
method-missing and malformed-reply. Unknown categories become `unknown`; raw
stdout/stderr, bus error text, application lists, IDs and filesystem paths are
excluded both at collection and report export. Retrying clears stale failure
detail before collecting the new observation.

These categories explain a current read failure; they never authorize recovery
or relax required application validation. Optional input failure still permits
valid applications with the existing warning. Rebuild the shared installers and
Root service/support packages through the next candidate; existing public
packages cannot recover discarded detail from a historical report. No new
permission, endpoint or user prompt is introduced. Physical reporter-device
acceptance and the original #397 cause remain unverified.

## Local recovery storage (next candidate, #201)

Optional `local_recovery` distinguishes host directory ownership/permissions,
directory type/access, unavailable storage, missing/unsafe/changed/invalid capsule
bytes, invalid operation selectors and incompatible retained observer source.
It appears in current errors and revalidated first/current-observation history.
Only fixed `reason` and `location` (`profile`, `ancestor`, `capsule`, `operation`)
categories, an optional four-digit octal `mode`, and an optional `owner`
(`root`, `current-user`, `other`) cross the export boundary. Unknown values are
filtered; paths, account names, numeric IDs and raw exceptions are excluded.

A local ancestry refusal happens before capsule content is read: it does not
prove that a file disappeared or changed, and is separate from TV Luna refusal.
Before a new No-root receipt, local storage validation exercises a temporary
private write/flush/fsync and directory sync. Failure creates no pending journal
or capsule and does not invoke the TV observer. This is an early usability check,
not a reservation of disk capacity; later failures retain ordinary pending state.
No ownership/permissions are changed, no old source is executed, and no recovery
or removal confirmation is bypassed. Existing old reports cannot gain a newly
invented cause. These source changes require rebuilt installers.

## Report contents

The next recovery candidate adds a fixed semantic `frontend` field:
`console`, `desktop` or `android`. It is separate from the existing Python
runtime/operating-system fields; an Android installer must not be inferred from
the Python platform name. Original installation failure, current inspection or
authentication failure, source package versions, observed installed components
and physical outcomes remain separate. Unknown old failure causes stay unknown.
Do not repeat installation, doctor or status merely to populate these fields.
The safe clean-removal summary contains only fixed state, stage, reason and
original-outcome categories. It does not export the original receipt, private
recovery data, operation IDs, tokens, paths or raw replies, and grants no mutation
authority. [Failure-injection matrix](INSTALLER-RECOVERY-MATRIX.md).

The next candidate also keeps the first Root cleanup `failure` separate from
`last_failure`, which describes the latest failed attempt and its cleanup stage.
For bounded Luna reads these contain only a fixed call identifier, a fixed reason
(permission denial, missing service/method, negative/malformed/oversized reply,
timeout or client startup failure), and an optional signed 32-bit error code.
Both the TV producer and host exporter filter these fields. Raw error text,
request payloads, inventories and routes are excluded. Existing old failures
remain unchanged; new detail cannot reconstruct an earlier discarded exception.
These fields diagnose a blocker and never authorize skipping control restoration.

New package rejection reports preserve the fixed `install failed` and
`remove failed` Luna states. When the original reply includes `details.reason`,
optional `luna.reason` retains only the nine fixed LG OSE IPK failure categories
listed in the [packaging comparison/source record](../history/2026-11-04-package-install-diagnostics.md).
Other strings, structured values and null become `unknown`; absent stays absent.
Current errors and retained history are revalidated at export. This next-cycle
change cannot recover details discarded by old reports; do not repeat an
installation merely to obtain them. Payloads, permissions, transaction parsing
and pending guards are unchanged; #307's installation/recovery remains unresolved.

The existing schema-1 fields remain. Additive fields include fixed `reason_code`,
checklist IDs/statuses, a filtered `status` projection, and `first_failure` with
`failure_history`. Known model/firmware/SDK values and observed project component
versions are included when available. Missing observations remain missing, never
inferred from an installer note or package target. A best-effort read with a five-second reply timeout
(and the existing SSH channel-setup deadlines) of the existing `tv.systemproperty/getSystemInfo` endpoint asks
only modelName, firmwareVersion and sdkVersion after trusted SSH sign-in for
install/status/doctor. Denial, timeout and unsupported fields do not block setup;
no serial, network identifier, pairing operation or permission change is requested.

Doctor exports the result of its existing status call, rather than collecting a
second status result for the file. The projection includes only known CYTV app
versions, fixed Helper/product/deployment states and relevant readiness booleans.
It excludes app inventories, addresses, profiles, UUIDs, paths, raw command output,
exception messages and free-text checklist details. Matching app versions still
cannot establish installer completion, service registration or physical Home.

Successful setup, status and restore also offer a report through the existing
Save diagnostic report control. Optional report-write failure does not turn
successful TV work into a failed command. `doctor --report` remains explicit.
Review every report before sharing. The special Home-button recording retains
its separately documented application-ID/timing scope.

## Recovery journal summary (unreleased)

Additive `recovery` is computed from the original local journal snapshot already
used by the report, without another TV query or receipt rewrite:

- `category`: `none`, `other-edition`, `removal-not-submitted`,
  `inherited-operation`, `interrupted-install`, `removal-started`, `unknown-journal`.
- `next_action`: `none`, `review-recovery` for an original pre-submission No-root
  removal, otherwise `retain-evidence`. These are advisory codes, never capabilities.
- `removals`: only `home`/`helper` keys with `submitted`, `terminal` or `done` values.
  Unknown IDs, values, paths, receipt identifiers and nested operation data are omitted.

The exact pre-submission predicate is shared with `require_removal_idle` (#256),
so a nested prior operation, unexpected field or malformed removal map cannot be
presented as the safe pre-submission case. Runtime mutation still re-reads its
private journal; exporting or editing a report never grants recovery authority.
A current `recovery-status-rejected` guidance code identifies a definite TV
package-status refusal during No-root removal/recovery. `removal-not-submitted`
guidance offers explicitly confirmed inspection after a failed original removal.
Original error capture/history behavior is unchanged; these fields do not reconstruct
legacy first failures or establish that a submitted package transaction terminated.

## Root admission and connection advice (unreleased)

Optional `guidance` contains only an allowlisted advice code and a Boolean pending
flag. Root `tv.root_capabilities` uses two fixed check keys and reasons: readable,
rejected, invalid-reply, unconfirmed or not-checked. `root_capability_codes` retains
only bounded numeric Luna error codes for these keys. Raw service replies and
Home routes are excluded. Current and retained first-failure projections are
revalidated; these fields cannot grant recovery authority or prove compatibility.
See the [preflight and guidance contract](INSTALLER-PREFLIGHT-HELP.md).

## Root activation evidence (unreleased)

Root activation now preserves existing typed installer errors instead of replacing
SSH command failures or definite TV launch rejections with a generic activation
error. SSH failures retain only their numeric exit status and fixed Root action
and execution boundary; launch rejections retain the existing allowlisted Luna
metadata. Fresh reports and retained first failures use the same action allowlist,
including `enable`, `restore` and `uninstall`. No remote output or exception text
is exported, and existing reports cannot reconstruct evidence already discarded.

Pending activation stages remain unchanged. An error does not retry activation,
repeat a launch, clear the recovery journal or establish that Home is active.
This installer-only correction does not fix or identify the original device
failure in [#282](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/282).
See the [investigation and verification record](../history/2026-11-04-root-activation-evidence.md).

## New Root worker evidence

Newly built Root coordinator code retains only a fixed worker exception category
and bounded numeric subprocess exit status / OS errno in its existing request
record. The first categories survive later status and continuation failures.
Raw command arguments, paths, stdout/stderr and exception text remain private.
The host copies the revalidated categories only from its already-returned,
operation-matched coordinator reply; it does not reread a worker log or repeat an
operation for the report. This is a source/runtime change requiring rebuilt Root
coordinator packages and installer payloads at candidate freeze. Old coordinators
cannot retrospectively supply these fields. Even a subprocess exit code does not
establish the child's detailed cause or authorize recovery.

## Primary versus later failures

New host operation receipts receive a private random `diagnostic_id`. It is
reserved against caller override and retained through checkpoints. It is not a
TV operation UUID, signature, lease, resume proof or authorization. Existing
receipts are not rewritten or upgraded to add it.

Only the invocation that created a receipt can save its initiating failure.
`diagnostic-failures/ID.json`, inside the private per-TV host directory, is created
exclusively and never replaced by later errors. The failure summary contains
allowlisted action/phase/type/reason, installer version/time, safe command/Luna/
Python/recovery categories and observed checks/metadata. A later status/doctor
report exports this saved primary separately from its own current failure.
The receipt is snapshotted before releasing the normal TV lock, so another
session cannot attach its new receipt to this invocation's error.

For legacy or unobserved failures, `first_failure` is null and
`failure_history=not-recorded`. A later status failure must never be relabelled as
the original deployment cause. Unsafe/corrupt/unreadable evidence is
`failure_history=unavailable`; it is retained, not repaired or bypassed.

A failure before an operation receipt exists can be retained separately as
`previous_attempt_failure`. It is historical context, never proof about a later
pending operation. Successful setup clears only this previous-attempt pointer;
existing reports and per-operation failures remain. Different TVs and new
operations do not share a primary-error association.

History is diagnostic-only private state. Its creation/read errors do not alter
operation results or journals. Every loaded history/status/metadata field is
revalidated at export. Unknown strings become fixed unknown categories; no raw
logs or free-form exception messages are added. Diagnostic evidence never
clears pending, launches recovery, retries a package transaction, enables Home,
clears emergency stop or changes permissions.

## Setup outcomes (unreleased)

`tv.setup_outcome` distinguishes fixed package verification, launch request,
startup observation and owner-reported physical Home results. These are
invocation-local evidence, not deployment authority. Unknown or extra persisted
values are removed/reclassified at export. See the [outcome contract](INSTALLER-OUTCOMES.md).

## Passive Root submission status (next cycle)

Root install status at `coordinator-submitted` reads original-operation data
through system Node without staging a coordinator or executing retained Python.
The additive `status.product.passive` projection contains fixed status,
operation-consistency, worker and Python-byte categories only. Recovery-required
remains; it cannot finish a pending record or grant resume. Matching interpreter
bytes are not execution proof and a later status cannot identify the original
SSH-127 deployment cause. See [the passive contract](ROOT-PASSIVE-DIAGNOSTICS.md#original-operation-bootstrap-and-path-selection)
and [dated checks/limits](../history/2026-11-02-root-pinned-passive-inspection.md).


## Candidate: retained Root activation observations (#334)

`tv.root_diagnostics` is an additive, revalidated projection. It contains only
`components` (`root`, `root_updater`, `system_updater` versions), fixed
`component_reads` outcomes, optional `runtime_release`, and `health_log`.
App metadata and release metadata are observations, not verification of private
runtime bytes. Existing recovery integrity/current-product checks remain separate.
Product readback merges its result into the retained status rather than erasing
runtime/readiness observations. A retained pre-enable status is explicitly marked
`observation_phase: before-enable`; it is not a post-failure readback. Root activation receives the advisory
`root-activation-pending` recovery category instead of `other-edition`.

For an installed recovery-only Root, status/doctor/recovery sends a bounded,
stdlib-only program through the already selected verified interpreter. The
program imports no retained deployment/runtime code and writes no TV file.
Uncertain submitted product install/remove paths keep their earlier inspection
boundary. Reads check ancestors, file ownership/type, links and unsafe modes;
metadata reads are capped at 64 KiB and only a 64 KiB emergency-log tail is read.
Collection failure never hides a primary error or authorizes another operation.
The program is embedded data, so frozen desktop and Android builds do not need
an unpacked Python source file.

Enable captures an ephemeral log cursor before the command and observes after
its reply/failure. A validated same-file bounded overlap permits `since-enable`;
rotation, truncation, changed/lost overlap or missing cursor falls back to
`historical-tail`. Only complete lines are classified. `health_refusal` is
`generic` for the old fixed ValueError or one of the seven existing reason codes;
`supervisor_error` is a boolean. An absent refusal is not evidence of success.
Raw lines, timestamps, transaction IDs, PIDs, boot/session identities, token
values, paths, cursor identity/hash and arbitrary exception text are not exported.
Historical evidence cannot establish the current cause; concurrent TV writers
cannot be excluded by this cursor. Reports and retained failure history revalidate
all fields, including hostile structured reason values.

The separately confirmed Home-off completion archives the original local receipt
and repeats existing activation eligibility checks before resolving that pending
activation. It neither enables Home nor updates code. See the [candidate recovery
path](../RECOVERY.md#candidate-finish-verified-root-setup-with-home-control-off).

## No-root observer failures (next candidate, #376 and #378)

An optional `no_root_observer` object identifies the fixed observer `command`
and `failure` category. It is revalidated in the current report, `first_failure`
and `observation_failure`. It contains no operation identifier, command text,
Node environment, filesystem path or remote output. Numeric SSH exit status
stays in `ssh_command.exit_status`; existing insufficient-storage guidance is
preserved. The SSH receive deadline now has the fixed reason `operation-timeout`.

| Failure | Established fact | Next investigation or correction |
| --- | --- | --- |
| `observer-error` | The launched Node invocation returned a matching error envelope. | Inspect the fixed `exception_name`, `exception_code` and `observer_reason` categories. The envelope is always rejected as an observation; it cannot authorize recovery. |
| `command-failed` | The SSH command returned nonzero. | Use the numeric status to narrow shell/runtime/storage investigation. Status 127 can mean a missing command, but does not identify which one. Do not infer an IPK failure or change permissions from it. |
| `timeout` | The SSH receive deadline expired or the transport raised a timeout. | Inspect the original operation using its saved connection when available; timeout does not prove cancellation or allow resubmission. |
| `connection-interrupted` | The existing transport identified connection loss. | Restore the existing trusted connection with the TV awake; preserve recovery data. |
| `transport-error` | Another transport exception prevented observation. | Maintainer investigation is required; arbitrary exception text remains private. |
| `invalid-json` | The command response could not be decoded as JSON. | Investigate runtime output/encoding privately; do not treat raw output as recovery evidence. |
| `invalid-reply` | JSON was returned with the wrong top-level shape. | Investigate the response contract; do not continue setup. |
| `foreign-operation` | The response did not identify the expected original operation. | Retain the original receipt and investigate the mismatch; never adopt another operation's response. |
| `invalid-status` | The matching response failed status validation. | Investigate the status schema/evidence; do not weaken validation or clear pending. |

Observer launch uses POSIX shell `unset NODE_OPTIONS NODE_PATH` before Node,
removing the dependency on an `env` binary with `-u` support. Failure to unset
stops before Node; the command is never retried. The trusted observer program,
its hash, original capsule and package/configuration protocol are unchanged.
This is a portability correction, not evidence that the affected TV lacks `env -u`.

The current launcher wraps synchronous observer execution with a bounded error
reply. `exception_name` admits standard Error/TypeError/SyntaxError/ReferenceError/
RangeError names; `exception_code` admits fixed module, permission, storage and
filesystem codes; `observer_reason` admits the observer's fixed guard reasons.
Unknown values become `unknown` on the TV and again during current/retained report
export. No exception message, stack, path, operation ID or arbitrary object is
exported. `ENOSPC`/`EDQUOT` retain the existing TV storage guidance and
`tv-storage-full` reason. A handled runtime failure returns a JSON error envelope
on stdout; it is not a successful observer result or a numeric SSH failure.
The host checks the operation binding and rejects every error envelope, including
empty or malformed detail. There is no retry, extra probe, permission repair or
receipt cleanup.

The wrapper does not change the bound `PROGRAM`, protocol or existing capsule
hashes. It covers synchronous runtime/guard errors in the current invocation,
including `prepare` and `status`. Shell/Node startup failures, parse failures
before execution and later asynchronous/detached-worker failures can still use
`command-failed`, transport or existing terminal evidence; absence of a runtime
category does not identify the cause. No TV compatibility is inferred.

### Filesystem failure context (next candidate)

For synchronous `observer-error` replies, the launcher additionally projects the
existing exception's `syscall` and `path` into two optional, allowlisted fields:

| Field | Values and meaning |
| --- | --- |
| `filesystem_operation` | Native filesystem operation: `lstat`, `stat`, `open`, `read`, `write`, `mkdir`, `rmdir`, `link`, `unlink`, `rename`, `scandir`, `readdir`, `fsync`, `fchmod`, `fchown`, `fstat`, or `close`; otherwise `unknown`. |
| `storage_area` | `private-storage` for the invocation's private observer root or descendants; `public-staging` for its public staging root or descendants; `storage-parent` for an ancestor of either root; otherwise `unknown`. Applies to Developer Mode and Root SSH roots. |

Classification uses only a normalized absolute pathname already carried by the
exception, with directory boundaries preserved. It does not resolve symlinks,
read metadata, or identify a physical mount. The original pathname, syscall
text outside the allowlist, exception message, stack and operation identifiers
are never exported. Relative paths, missing/non-string paths, descriptor-only
errors (such as `fsync` without a path) and unknown operations remain `unknown`;
there is no inference from the exception message or another filesystem probe.
Both fields are revalidated in current reports and retained failure history;
older envelopes/records without them remain valid and do not gain invented data.

For example, `storage-check` / `EACCES` / `mkdir` / `public-staging` narrows a
failure to creation in SDK staging. It does not identify the denying policy or
authorize chmod/chown, cleanup or retry. The storage check precedes creation of
a new pending operation and package submission, so the generic
`pending-operation` reason alone does not establish that pending exists.

The context is added only by the launcher wrapper. Developer Mode and Root SSH
observer source bytes, source hashes and capsule bindings are unchanged. No
additional TV command, filesystem operation, permission change, automatic retry
or recovery action is introduced. Detached/asynchronous worker errors remain
outside this synchronous error envelope. Rebuilt host and Android installers
are required for delivery; these additions are not in published CYTV 0.12.0.

`first_failure` belongs to the pending operation's diagnostic ID, not the TV's
entire installation history. Different timestamps across exports do not establish
that the same operation's first failure was overwritten. Preserve original
records and investigate the intervening workflow privately; do not publish the
private operation receipt or repeat installation to populate history.

Old `pending-operation` reports cannot recover the discarded command exit code
or distinguish these categories retrospectively. Do not repeat installation to
populate a report. A new report may describe a later observation failure while
the original cause remains unknown. Neither these categories nor the portable
launch establish recovery or compatibility on the reporting device. See the
[source verification record](../history/2026-11-07-no-root-observer-evidence.md).
