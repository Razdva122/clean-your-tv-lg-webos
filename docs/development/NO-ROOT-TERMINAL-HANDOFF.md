# No-root original-transaction terminal handoff (#201)

## Decision and scope — 2026-11-02

No supported historical terminal readback has been established for the two
legacy No-root pending actions in [#201](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201).
This handoff records the source result and the missing contract. It does not
provide a new recovery command. No TV was contacted, no installation result is
published, and no journal, profile, permission or package operation is changed.
The successful C2 `/dev/listApps` answer is complete; do not request it again.
The pending-uninstall and pending-install reports remain separate.

The official CLI HEAD remains `ed7a6994be443207f3427b19f210f6606f004eb6`.
The additional installer source is LG's **OSE** `appinstalld2`, HEAD
`938ffd716c0c250bdb860100e9a41d3bd5b0b452` (2025-01-21). These are reviewed
public source revisions, not identified binaries from either reported TV.
Retail TV behavior, public-bus ACLs and restart semantics cannot be inferred
from OSE alone. “No supported contract established” does not mean no private or
firmware-specific mechanism exists.

## What the sources establish

| Source | Finding | Consequence |
| --- | --- | --- |
| [Official CLI command map](https://github.com/webos-tools/cli/blob/ed7a6994be443207f3427b19f210f6606f004eb6/files/conf/command-service.json) and [install/remove implementation](https://github.com/webos-tools/cli/blob/ed7a6994be443207f3427b19f210f6606f004eb6/lib/install.js#L204-L240) | Subscribed `dev/install` / `dev/remove` calls wait for their reply stream's terminal state; inventory uses `/dev/listApps`. | They do not supply an original transaction ID or a historical lookup method. |
| [OSE service methods and status handler](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/service/AppInstallService.cpp#L48-L65), [status handler](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/service/AppInstallService.cpp#L263-L293), [status request schema](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/files/schema/appInstallService.status.schema) | Registered methods are install/remove/status and dev install/remove. Status serializes `AppInstaller::toJValue()` and can subscribe to changes. The schema defines `subscribe`, without a historical receipt selector. | No history/replay API is exposed in these reviewed registrations. Supplying an invented operation field has no established lookup semantics. |
| [OSE task lifecycle](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/AppInstaller.cpp#L133-L263) | Updates are broadcast to `status_<appId>` and `status`. Finish schedules removal from `m_mapTask`; `toJValue()` enumerates that map. | A late empty response cannot recover the removed task's success/failure. An unrelated later event for the same package is not the original outcome. |
| [OSE request submission](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/AppInstaller.cpp#L54-L125) | Install/remove creates and runs a task when the app has none; a currently known app receives a duplicate-command error. | Resubmitting with `subscribe:true` is a mutation request, not reattachment. A duplicate refusal is not a terminal receipt. |
| [OSE task serialization](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/Task.cpp#L294-L390), [step order](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/files/conf/appinstalld-conf.json.in), [status enum](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/InstallHistory.h) | 30/31 are full install/remove success; 17/21 are intermediate IPK milestones. Service/security/data steps remain. `InstallHistory.h` defines steps, not a persisted queryable history. | Files, package absence or intermediate milestones cannot replace full terminal proof. |
| [OSE API and access groups](https://www.webosose.org/docs/reference/ls2-api/com-webos-appinstallservice/#status), [source access map](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/files/sysbus/com.webos.appinstalld.api.json) | `status` uses `applicationinstall.management`; dev install/remove uses `applicationinstall.devmode`. | Permission to install does not imply permission to monitor status. No role/ACL elevation is admitted. |

The existing Root `observed_install.py` subscribes **before** submitting its new
operation and matches app, staged package path and client. `installer_status.py`
recognizes a live matching completion; neither is a historical-query adapter.
Importing that code into No-root cannot recover a terminal event already lost,
and would still depend on the denied monitor capability. Root behavior belongs
to a separate workstream and is unchanged here.

## Why the host journal cannot bind a later event

`cytv/state.py::Store.begin` reserves a host journal and a `diagnostic_id`.
For legacy No-root installs, `operations.py::install` stores expected file hashes
and versions, then submits Helper and Home separately. It does not persist the
Luna sender identity, a vendor transaction token or each install terminal.
`diagnostic_id` is a host correlation value, never a vendor installer identifier.
For removal, `removals[app]` distinguishes submitted/terminal/done but does not
supply a vendor historical lookup key. Keep any nested `previous` record intact.

Consequently, a terminal event with the right app ID, a new luna-send client or
a matching package path alone cannot be retroactively attached to the legacy
journal. Do not invent a binding from elapsed time, missing processes, snapshots,
file timestamps/hashes or the last visible app version. PID-based sender names
also need lifetime/reuse guarantees before historical matching can be accepted.
An authenticated future journal protocol could protect future operations; that
would not repair these legacy receipts without separate evidence.

## Read-only handoff before any device session

1. Select **one** original pending operation and retain its private host journal
   byte-for-byte, including nested prior operation and per-package removal stages.
   Use the already trusted Developer Mode identity; do not create a new profile,
   journal or diagnostic ID as a replacement binding. Inspect an existing private
   copy offline. Missing/corrupt binding is an explicit blocker, not permission
   to reconstruct one. Do not publish profile paths, credentials or raw journals.
2. Obtain the vendor contract below from public documentation/source or a vendor
   response. No new device command is requested now. Do not repeat the answered
   `/dev/listApps` or denied `status` probes, read broad logs/app inventories,
   modify ACLs, reset Developer Mode, or resubmit installation/removal.
3. Only after the contract is identified, design a separately authorized bounded
   read-only query for that original operation: exact method/payload, original
   lookup key, trusted identity, one bounded session, ten-second ceiling and
   redacted output allowlist. Denial, EOF, timeout, unknown/missing record,
   conflicting identity, duplicates and restart ambiguity must stop the query.
   Do not infer a result or switch to a mutation endpoint on failure.
4. Review the readback without changing host or TV state. Require an exact
   original-operation binding and documented terminal disposition for every
   affected package, with registration and partial/conflicting-task semantics.
   A result for a new operation or another pending action is insufficient.
   Reading a success record alone does not authorize cleanup or a reinstall;
   an implementation and regression review must define the next permitted step.

The existing explicit-removal idle gate remains as shipped. It has not become
a proof that the old operation succeeded, nor is this handoff an endorsement of
a new automatic reconciliation path. Permission, unknown-outcome and duplicate
submission guards remain intact; no journal clearing, blind reinstall or replay.

## Precise vendor-contract request (draft; not sent)

Destination: LG webOS TV developer support / the maintainer's vendor contact.
This requests API semantics, without another owner's installation report:

> Is there a supported read-only API on retail webOS TV, callable through an
> existing Developer Mode SSH/public-bus identity, to retrieve the terminal
> result of an earlier `com.webos.appInstallService/dev/install` or `dev/remove`
> after its original subscription disconnected? Please provide the exact method,
> request/response schema, required permissions, supported firmware range and
> correlation key. How can a legacy caller recover that key if it retained only
> app IDs, expected versions/hashes and host-side progress? Does the result
> distinguish install from remove and success from failure/cancellation, include
> service-registration completion, exclude partial/conflicting/repeated operations,
> and remain uniquely bound across installer/TV restarts and client PID reuse?
> Please specify retention/expiry and unknown/duplicate/disconnect behavior.
> If no such lookup exists for legacy requests, please confirm that limitation
> rather than suggesting resubmission as a status query.

A reply giving only inventory or current idle status would leave the blocker
unresolved. Do not mark the issue `needs-info` as if its owner still owed the
already answered app-list probe. Until a vendor answer or new primary source
establishes this contract, remaining work is maintainer research (`status:planned`).
No contact or publication beyond this repository handoff is initiated here.

## Deterministic verification and limits

[`no-root-terminal-authority.json`](../../tests/cytv/fixtures/no-root-terminal-authority.json)
contains synthetic source-shaped late empty snapshots and live full terminal
successes for both actions. It is not a TV capture or a vendor emulator. The
tests verify that the transport parser accepts the late snapshot as an
acknowledgment but not a terminal result. Actual status orchestration retains
original legacy receipts and makes only the app-list Luna call, never replaying
install/remove; a live terminal-shaped response to
the existing idle check cannot authorize mutation or overwrite the journal.
The event's app/client fields do not make it a receipt for the host journal.

These extend the existing guards; no new recovery fix or red/green product
change is claimed. All twelve user guides retain the shipped instructions;
this source-only handoff changes no setup or controls. Physical service
registration, Home routing, controls, audio, standby, cold boot, OTA and rollback
were not tested. Candidate selection, versioning and full release acceptance
remain with the release coordinator.

Local validation used `npm ci` and the repository's pinned Python build/runtime
requirements in a private venv. `python -m unittest discover -s tests/cytv -p
test_operations.py` passed 72 tests after review; `scripts/test.sh installer`
passed Homebrew checks and 642 cytv tests (38 optional-component skips).
Initial runs lacked network/fontTools; preparing the documented build dependencies
resolved those environment failures without a product change. Independent
read-only review found an unused fixture branch; it was corrected and re-reviewed
with no remaining actionable findings. Local Markdown links, fixture JSON and
`git diff --check` passed. Nine downloaded OSE source files were matched to their
blob IDs in the pinned upstream Git tree. Ordinary PR CI remains a separate gate.

## Helper install error and asynchronous cleanup (#307)

The [2026-11-05 follow-up](../history/2026-11-05-helper307-recovery-boundary.md)
checks the reported status 24 against the same pinned OSE source. ErrorInstall
is not an idle receipt: `onFinishTask()` can asynchronously release the original
task and schedule an internal removal of unpacked content. The original failure
summary therefore cannot authorize a new mutation or reconstruct a legacy vendor
transaction binding. Retail behavior remains unverified.

The installer now presents the existing localized package-status capability
blocker at the exception boundary instead of suggesting Doctor as a workaround.
This preserves numeric diagnostic evidence and both original/inherited host
journals. It changes no recovery authority and supplies no historical lookup.
The vendor contract requested above is still missing; do not repeat owner probes
or introduce an install/remove, file-only or bus-permission bypass.
