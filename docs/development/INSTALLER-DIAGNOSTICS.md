# Installer diagnostic evidence (unreleased)

The shared desktop, console and Android installer now exports diagnostic context
without treating it as recovery authority. These changes are in source only;
v1.5.4 does not contain them. No TV compatibility or completed recovery follows
from a diagnostic report.

## Report contents

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

## Root admission and connection advice (unreleased)

Optional `guidance` contains only an allowlisted advice code and a Boolean pending
flag. Root `tv.root_capabilities` uses two fixed check keys and reasons: readable,
rejected, invalid-reply, unconfirmed or not-checked. `root_capability_codes` retains
only bounded numeric Luna error codes for these keys. Raw service replies and
Home routes are excluded. Current and retained first-failure projections are
revalidated; these fields cannot grant recovery authority or prove compatibility.
See the [preflight and guidance contract](INSTALLER-PREFLIGHT-HELP.md).

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
