<a id="installer-diagnostic-evidence-unreleased"></a>

# Installer diagnostic evidence

The shared desktop, console and Android installer now exports diagnostic context
without treating it as recovery authority. Use current released installers; older releases such as v1.5.4 lack this context. No TV compatibility or completed recovery follows
from a diagnostic report.

<a id="no-root-icon-inventory-next-candidate-311"></a>

## No-root icon inventory (v1.13.0, #311)

The existing No-root inventory read records aggregate `tv.icon_inventory` in
success/failure reports and filtered failure history. It performs no additional
TV calls and does not change icon admission, download limits or fallback policy.
A missing object means this path was not observed by this installer; older reports
cannot be reconstructed. Root's separate icon reader is not instrumented here.

- `schema`: 1. `status`: `unavailable` before catalog/input retrieval completes,
  `reading` during validation/icon processing, or `complete` when inventory returns.
  This describes collection, not successful loading of all icons or Home acceptance.
- `apps`, `embedded`, `fallback`: processed unique visible apps and their icon
  outcomes. Hidden/duplicate entries do not consume these counts.
- `missing_uri`: apps without a nonempty icon candidate in the supported fields.
- `rejected_uri`: candidates rejected for invalid metadata, URI syntax, scheme,
  host, credentials or port. No blocked address is requested.
- `fetch_failed`: accepted candidates whose existing download raises an I/O or
  value error, including TLS/HTTP failures and the existing size check.
- `invalid_image`: downloaded candidates without a supported image signature.

Cause counters count candidates, except `missing_uri` which counts apps. One app
can fail a larger candidate and embed a smaller one, so cause counts need not
match fallback counts. Only fixed numeric counters (0–1800) and fixed statuses
are exported and revalidated in report/history projections. No URIs, paths,
application IDs/titles, image bytes or exception text are retained in this object.
The summary does not identify which app failed or prove any suspected device
cause. Status/Doctor alone do not reread icons or reconstruct an earlier attempt.

<a id="retained-root-activation-checks-next-candidate-355"></a>

## Retained Root activation checks (v1.13.0, #355)

For a retained `activate-root` receipt, `tv.root_setup_recovery` adds a fixed
`reason` and `checks` map to the normal report and revalidated failure history.
The ordered checks are `receipt`, `stock-home`, `restored-journal`, `files`,
`product`, `updater`, `rollback-baseline`, `updater-transaction` and `binding`.
States are `verified`, `unverified`, `not-run`, `pending` and `not-required`;
unknown or malformed persisted values become `unknown`. Reasons are `verified`,
`restoration-pending`, `pending`, `not-run` or the failed check plus `-unverified`.

`not-run` means short-circuit evaluation never reached that check. `pending`
means the remote aggregate check was submitted but its substep result could not
be established, such as after transport failure. The existing Updater check now
returns only a fixed failed-boundary marker, distinguishing its integrity/bootstrap
from the rollback baseline/cache/package checks. Its separate service transaction
read remains mandatory. The original success marker, predicates, call order,
timeouts and continuation decision remain unchanged. No extra probes are added.
The `binding` category groups refusal/error of the existing locked recovery proof;
it does not export tokens, generations, transactions, hashes, routes, paths or
exception text, and it cannot identify a discarded historical health-context cause.

These fields explain a generic `observation-unverified` refusal; they do not fill
installation preflight checks that recovery never ran. Recovery checks can execute
retained/support code and take existing locks; this patch does not turn `recover`,
`status` or `doctor` into wholly passive commands. It does not activate, restore,
remove or reinstall anything automatically, and grants no recovery authority.
Do not rerun an operation merely to populate diagnostics. Earlier reports cannot
recover discarded detail. Rebuilt desktop/console/Android installers are required;
no TV package, permission, endpoint or persistent device state is added. No device
recovery or hardware compatibility is established by these synthetic host tests.

<a id="tv-node-version-next-candidate"></a>

## TV Node version

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

## Network connection causes

During `ssh-connect`, inspect typed socket errors, including the values of
Paramiko `NoValidConnectionsError.errors`. `EACCES`/`EPERM` map to
`ssh-access-denied`, `ECONNREFUSED` to `ssh-refused`, and socket timeouts to
`ssh-timeout`. Mixed causes and other errors retain `ssh-unreachable`; a host
unreachable error does not establish that macOS Local Network permission was
denied. Diagnostics export only these allowlisted codes, never the address keys,
exception text or raw errors. Trust, authentication and local key-file failures
retain their separate guidance. Classification is limited to initial connection.

The reason-code guidance above shipped in v1.12.1 (#402). Published v1.13.0
additionally preserves `connection.protocol: "ssh"` and `connection.causes`
for socket failures at `ssh-connect`. This sorted, unique list contains only
`access-denied`, `refused`, `timeout`, `host-unreachable`, `network-unreachable`,
`name-resolution` or `unknown`. Categories come from the existing typed socket
exception/errno (including Paramiko's per-address values), not error messages.
Mixed causes retain the existing generic guidance while the list preserves each
observed category. It is not a diagnosis of the firewall, selected port, Root
availability or TV compatibility.

The shared `create_report` / `failure_summary` path retains and revalidates these
categories in the standard desktop/console/Android export, recorded first failure,
previous attempt and current observation. Old reports without the field remain
valid; discarded causes cannot be recovered retroactively. SSH authentication,
trust and local key-file errors, unrelated phases and successful connections do
not acquire socket causes. There are no extra connection attempts, TV probes,
permissions, endpoints or recovery-state changes. Rebuild the embedding installers
to deliver this diagnostic change (#420); physical Windows ARM64/TV acceptance
remains separate from host synthetic tests.

Desktop connection guidance replaces the scrolling report/checklist at failure
with the cause, next step and explicit Doctor recheck. Doctor checks prerequisites
and status; it does not submit package installation or resume setup. Its usual
SSH trust/authentication prompts and saved-profile checks still apply. Edited
connections are validated before running Doctor. Pending operations keep their
original identity and recovery flow; no new edit/recheck shortcut is offered.
On macOS, settings access is a user action, not an automatic permission change.
Settings may show an older duplicate name; the app does not claim to read that
permission state.

<a id="optional-root-input-inventory-next-candidate"></a>

## Optional Root input inventory

The Root installer reads both fixed Luna catalogs directly over the existing
authenticated SSH transport, as the normal Root installation path rather than
retrying a failed Node subprocess. Each query keeps stdin open until its reply,
has an eight-second deadline and retains the original 1 MiB application / 256 KiB
input response bounds. Queries run sequentially, so two timeouts can take about
16 seconds plus SSH channel setup. No new pairing or permission is requested.

Captured replies are passed as JSON data to the current on-TV catalog/icon
reader through its existing I/O-provider argument. That step still runs Node for
bounded local icon reads and normalization, but cannot load `child_process` to
launch the queries. No TV service or TV package sources change. The installed
service's separate runtime readers are unchanged; this is an installer fix, not
physical Home/input acceptance. No-root retains its existing inventory transport.

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

<a id="root-inventory-failure-detail-unreleased-397"></a>

## Root inventory failure detail (v1.13.0, #397)

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
valid applications with the existing warning. Use the matching v1.13.0 installers and Root service/support packages. New packages cannot recover discarded detail from a historical report. No new
permission, endpoint or user prompt is introduced. Physical reporter-device
acceptance and the original #397 cause remain unverified.

<a id="local-recovery-storage-next-candidate-201"></a>

## Local recovery storage (#201)

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

Published v1.13.0 also keeps the first Root cleanup `failure` separate from
`last_failure`, which describes the latest failed attempt and its cleanup stage.
For bounded Luna reads these contain only a fixed call identifier, a fixed reason
(permission denial, missing service/method, negative/malformed/oversized reply,
timeout or client startup failure), and an optional signed 32-bit error code.
Both the TV producer and host exporter filter these fields. Raw error text,
request payloads, inventories and routes are excluded. Existing old failures
remain unchanged; new detail cannot reconstruct an earlier discarded exception.
These fields diagnose a blocker and never authorize skipping control restoration.

Published v1.13.0 Root cleanup adds `cleanup_step` to `status.product.failure` and
`status.product.last_failure` when control restoration fails inside an instrumented
boundary: `routing-inverse`, `runtime-restore`, `provision-rollback`, `startup-hook`,
`legacy-lockdown`, `registration-restore`, `legacy-permissions` or `home-readback`.
This distinguishes subprocess failures sharing `original-writers-fenced`; it does
not expose the child's command, output or detailed cause. Failures outside those
boundaries omit the field; old records remain unchanged. Both worker and host
allowlist values; unrecognized persisted/remote values export as `unknown`.
The operation-matched coordinator reply feeds the existing host status summary,
Save diagnostic report action, `observation_failure` and retained first-failure
history projection. Rebuild Root coordinator/Updater and embedding installers
through the coordinated release; host source alone cannot add TV-side context.
No new TV call, state file, recovery admission, timeout or cleanup ordering is
introduced. Saved backups, original receipts and failure-before-package-removal
behavior are preserved. An old exit status cannot identify its historical step;
these fields neither authorize a retry nor prove recovery or physical Home.

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

<a id="recovery-journal-summary-unreleased"></a>

## Recovery journal summary

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

<a id="root-admission-and-connection-advice-unreleased"></a>

## Root admission and connection advice

Optional `guidance` contains only an allowlisted advice code and a Boolean pending
flag. Root `tv.root_capabilities` uses two fixed check keys and reasons: readable,
rejected, invalid-reply, unconfirmed or not-checked. `root_capability_codes` retains
only bounded numeric Luna error codes for these keys. Raw service replies and
Home routes are excluded. Current and retained first-failure projections are
revalidated; these fields cannot grant recovery authority or prove compatibility.
See the [preflight and guidance contract](INSTALLER-PREFLIGHT-HELP.md).

<a id="root-activation-evidence-unreleased"></a>

## Root activation evidence

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

<a id="setup-outcomes-unreleased"></a>

## Setup outcomes

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

<a id="no-root-observer-failures-next-candidate-376-and-378"></a>

## No-root observer failures (#376 and #378)

The published Developer Mode storage selector adds `command: storage-select`.
It performs only metadata reads before the existing `storage-check` and pending
creation. An unsafe existing location or ambiguous pair of roots is a refusal,
not permission to erase recovery data. Selection is never run for an existing
capsule or Root SSH. See [storage selection and recovery binding](NO-ROOT-PACKAGE-AUTHORITY.md#developer-mode-private-storage-selection-unreleased).

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

<a id="filesystem-failure-context-next-candidate"></a>

### Filesystem failure context

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
