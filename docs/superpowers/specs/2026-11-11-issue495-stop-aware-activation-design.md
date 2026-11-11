# Stop-aware activation after No-root setup (#495)

Date: 2026-11-11. Proposed architecture for owner review; not implemented or
accepted device behavior. Related implementation draft: #503. Separate removal
fix: #498. Neither is admitted to the currently frozen release by this document.

## Required behavior

A successful new or repeated installation enables CYTV Home. It does not merely
start a Helper that still has Home control disabled. Existing user preferences
other than the explicitly requested Home On transition are preserved.

An existing safety Stop may be consumed by that new installation intent. Every
Stop published after that intent's baseline wins, including during package work,
configuration, restart preparation and input acquisition. The installer must not
silently turn such a cancellation into Home On, a startup pass or physical Home
acceptance. Later explicit owner Start is a new intent.

Old pending installations retain their original capsule/source bindings and
original strict startup behavior. Status remains read-only. No package, launch
or activation request with an unknown original result may be blindly replayed.
Lost-profile recovery retains the separately confirmed clean-removal flow and
its restart/process/absence guards, including the separate #498 dependency.

## Why a launcher flag or marker snapshot is insufficient

Current C and JS producers can rewrite the same blocked/watchdog file with the
same bytes. Inode/hash/timestamp snapshots do not distinguish every Stop.
Checking before unlinking does not make that unlink conditional. Current
nativeHomeStart clears both latches and the initial control request without
preserving a new Stop. Starting Helper also preserves home-control.enabled=false.

These facts rule out a launcher-only fix. Moving deletion earlier moves the
race. Native controller exclusion alone does not serialize every Stop producer.
No new claim about old marker contents can supply the missing event identity.

## Proposed protocol: retain distinct Stop events

Reuse the existing reviewed Stop inbox/private journal/native broker foundations
rather than introducing a second unreviewed clear-by-timestamp mechanism:

- Native Stop publication creates a fresh exclusive event ID for each stop.
  Concurrent producers never overwrite one another's event. Existing physical
  input release, key-up, ungrab and watchdog cleanup remain mandatory and are
  not conditional on successful diagnostic publication.
- A trusted controller lease owns private journal transitions. The native broker
  retains actual exclusion across the entire asynchronous transaction, not a
  Boolean lease claim supplied by Node or a launcher parameter.
- New installer intent binds the exact initial Stop set and a fresh operation
  identity into the canonical plan and host capsule before product work. Only
  that set may be consumed. A new record remains unconsumed even if a Stop lands
  during prepare/commit; no unknown event is deleted to enable startup.
- Activation consumes the bound initial set under the journal contract and
  verifies the Stop set again before opening Home and before input acquisition.
  Controller and relay gates continue checking for newly published Stops. A
  racing new Stop produces blocking and full input cleanup, not automatic retry.
- Only after verified activation does the existing Home-control operation set
  enabled=true, with fresh readback. A Stop arriving during that transition
  retains priority and terminates input ownership. Physical Home acceptance is
  still an independent owner observation.
- Prepared or unacknowledged Start is never automatically replayed. Loss of
  lease, malformed/unsafe/missing evidence, capacity exhaustion or unverified
  durability blocks activation. Matching diagnostics contain fixed categories,
  not raw event IDs, credentials, paths or private journal contents.

The current foundations deliberately have no production trusted provisioning
or Home authority. Do not enable their HOST fixture factory, accept a path/UID/
FD/pin from app parameters, infer trusted bindings from the directory being
admitted, or treat nativeHomeStart as new journal authority. Production
provisioning and the authenticated installer-to-controller intent handoff must
be implemented and independently reviewed before any runtime consumer is wired.

The frozen foundations currently bound the Stop inbox to16 records and the
private chain to64 entries. Exhaustion remains an explicit blocking condition.
This task must include a reviewed lifecycle/capacity decision before production
promotion; silently deleting or rotating records would invalidate the guarantee.

## Legacy transition boundary

An old Helper has no unique record of each Stop. No new reader can reconstruct
that missing history. Importing a legacy blocked/watchdog marker as an old event
is not proof that it was not rewritten during installation.

Consequently an upgrade must not report automatic activation as verified unless
it establishes a new generation-aware baseline with all old producers fenced.
The migration must inventory actual controller/relay/service writers, establish
quiescence and install all cooperating producers before admitting that baseline.
A restart is allowed only when the supported migration actually needs it; merely
waiting or observing file absence cannot substitute for fencing.

If this cannot be established on an existing legacy installation, packages can
be verified but activation stays blocked with an explicit legacy-transition
reason. A separately confirmed owner Start after the new baseline is established
is a new intent, not permission to retroactively consume an unknown Stop from
the original installation. This is a visible compatibility limit, not a pass or
an implied exemption from the owner's new-Stop precedence requirement.

This legacy limitation is part of the design review. Do not promise that the
original #495 device will automatically activate on its first upgrade before
migration evidence exists.

## Implementation boundaries

1. Production provisioning and lifecycle for fixed Stop/private journal storage;
   explicit ownership/group/FD provenance and bounded capacity behavior.
2. Wire all producers: relay emergency/failure/watchdog paths, controller block
   paths and existing explicit Stop operations. Keep input cleanup independent.
3. Wire broker/journal into bootstrap/controller/relay. Pass actual checked lease
   authority through trusted code; keep automatic boot and explicit owner Start
   as distinct intents and preserve legacy pending readers.
4. Bind installer activation intent and initial Stop set into new plans/capsules;
   configure Home On through verified runtime readiness/readback. Project cancel
   results separately from package/startup/physical Home evidence on all clients.
5. Review installer/update/rollback compatibility and legacy migration. Root's
   own guardian/recovery authority must not be changed incidentally.
6. Retain #503's fixed lost-profile guidance and #498's separate removal scope;
   rewrite the PR, ledger and practical localized steps around final behavior.

## Verification and acceptance

Write failing real-flow tests before each implementation. Required distinctions:
old Stop versus new Stop; two identical consecutive Stop requests; Stop before,
during and after prepare/commit; lost replies and closed retries; duplicate or
stale intents; unknown launch result; process/lease loss; full/corrupt/missing
journal; malformed producer records; legacy migration with an active old writer;
Home initially Off; Stop during Home On readback; and no physical Home claim from
a package install or launch ACK.

Run affected C/input/cleanup tests and exact Node0.10.15/0.10.25/0.12.2 cases for
changed consumers. Reuse unchanged foundation evidence, while adding actual
production-provisioning, cross-process/cross-UID and real syscall failure tests.
Build wiring must cover CLI/desktop/Android, Helper app/service and rollback
source closure. An independent reviewer must assess races and migration.

One future selected installer/Helper pair then needs owner-supervised physical
acceptance: establish actual model/firmware/webOS/remote/edition/host/versions;
verify ordinary activation, deliberate fresh Stop, key-up/unrelated buttons,
Home On/Off, standby versus cold boot, and affected update/rollback/recovery.
No preliminary package or host model replaces final artifact/device evidence.
The release coordinator owns inventory, version, candidate dispatch and admission.
