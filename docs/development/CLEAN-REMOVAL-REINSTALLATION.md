# Clean removal and a subsequent edition installation

This is the removal/reinstallation contract delivered in v1.13.0. A completed uninstall must leave a TV
ready for another supported Root or No-root setup. Disabling Home control alone
does not uninstall the Root edition. Current installation, controls, firmware
requirements and emergency-stop checks still apply.

## Completion retires destructive authority

Full removal deletes known project packages/services, startup, private runtime,
pairing/configuration and temporary installer evidence, after the existing
restart and live absence checks. Root-owned No-root staging is also swept.
Minimal inactive locks, compact receipts and revocation records remain so old
processes cannot recreate an installation. They contain no retained executable
payload or pairing key and cannot be treated as a blanket installation conflict.

Under the original ownership/worker locks, final cleanup persists a planned
`final_fence` UUID and its `final_original_lease`, rotates the ownership UUID,
publishes the completed receipt, then marks the new fence verified. Success is
returned only after all writes. An interrupted publication resumes that same
planned UUID. The ownership lock inode is never replaced or unlinked.

Old Root coordinators and Node finalizers retain the original lease and cannot
reclaim the rotated fence. Current completed retries perform live readback only;
reappeared apps/files cause refusal, never another sweep. A new explicitly
requested Remove creates a separate goal. Try again on an active removal retains
that goal. This protects a later Developer Mode installation too, without asking
the jailed Developer Mode account to inspect Root-private storage.

## Root SSH to No-root

The old shell probe correctly rejects an installed or incomplete Root edition,
but also rejected every verified full removal because minimal Root evidence
remains. The updated path uses current hash-verified Node cleanup support under
the original native locks; it does not provision a TV Python runtime. Ordinary
Node 8+ support and the packaged Node 0.12.2 Beta closure retain their own floors.

A legacy completed cleanup may have its inactive final fence published after
the same current readback, without repeating deletion. Unfinished, mismatched,
unsafe, restart-pending or reappeared project state is not admitted.

The new No-root plan canonically binds the cleanup operation, removal goal and
final fence. Its authenticated host capsule is saved before an atomic TV
reservation with a distinct successor UUID, exact plan/source hashes and a
pre-submission marker. The same plan can resume; changed active plans refuse.
A closed original observer can hand off to the next install. A full removal
revokes the old observer binding before restoring the inactive completed fence.

Every observer call and actual detached package worker retains the original
Root locks; direct EIM and launch effects use the same guard. A bounded native
busy wait keeps the SSH input open and never replays a vendor request. Missing
evidence after submission remains unknown. Before submission only, current
read-only observation can offer continuation of the authenticated saved plan.
The immutable `PROGRAM` and `ROOT_PROGRAM` observer bytes remain unchanged;
this support is the outer ownership wrapper, not a rewritten recovery capsule.

The capability probe restores empty staging leaves to absence. After the exact
successor is reserved, its install `prepare` recreates the public staging parent
under the same native locks. It checks the inner plan, paths, sender and original
source before creation, pins the root-owned parent without following links,
creates mode 0755 atomically regardless of umask and syncs both directories.
An existing unsafe leaf refuses without changing its mode. A repeated prepare
keeps the existing parent inode and original observer evidence. Removal does not
create this install-only parent. This is new setup state, not residue kept by
the preceding full cleanup.

The disposable native gate verifies and retires its own temporary file before
checking clean state. Large legacy support is sent on stdin, rather than a
single oversized argv element. Descriptor I/O uses APIs available on exact
Node 0.12.2. Unknown or changed support refuses before effects.

An absent managed-Python parent means there is no promotion descriptor. Node may
reuse fd 4 internally; only a descriptor matching the real `.install.lock` inode
is inherited when that parent exists. A Linux integration test runs the actual
native gate, guard, VM observer and detached worker with real `/proc/self/fd`
and flock; only fixed host paths/UID and the independent cleanup proof are modeled.

## Verification scope

`tests/cytv/test_root_no_root_handoff.py`, Root `test_clean_removal.py` and
`test_cleanup_tail.py` cover ownership, stale work, current readback, publication
interruptions, explicit new goals, revocation, legacy runtime and native flock
waiting. The Node filesystem/RPC adapters and mocked child observations have
their stated limits; they are not device or Linux namespace-race acceptance.
Existing real detached-observer integration remains a separate dependency check.

No Root-to-No-root full uninstall/reinstall on a physical TV is established by
these host tests. See the dated candidate observations for actual device work.
Home/remote, sound, standby, cold boot, OTA and rollback require their own exact
artifact observations; an uninstall restart or package installation proves none
of them.


### Removing a No-root successor reached through Root SSH

The minimal inert predecessor fences are not a reason to strand the successor's
full-removal goal. On `root-access-required`, the same No-root goal may use the
shared Root cleaner only with a native-locked proof of its current No-root lease,
exact closed observer and completed predecessor final fence, absent Root packages
and hooks, and the fixed inert private-file inventory. Persist the proof before
continuation and refuse changed leases, selectors or removal intents. A live or
unverified Root installation still requires its Root workflow. Node 0.12.2 uses
the verified nested Beta payload. This does not weaken the normal No-root private
cleaner or retain public staging after full removal.

Native System bootstrap runs with bytecode disabled, matching managed/standalone
setup. Older verified System staging may contain a top-level CPython cache.
Retire it as data only when safe regular leaves match canonical cache names for
manifest-listed top-level Python modules. Unknown files in an independently verified, inactive System staging directory
are retained with their exact directory identity and reported as a nonblocking
temporary-files warning. Python and the final native/Node gate use the same
exception; unrelated/current support stages and live processes remain guarded.
Never load a retained `.pyc` to authorize removal.

## Installer removal compatibility follow-up

Current source reuses the existing confined tree remover for host-checkpointed
`/tmp/cytv-root-tail-<UUID>` scratch directories. Their old executable, atomic
upload temporary files and cache entries are inert data, removed together under
the matching operation/lease and original locks. Filename or old support hashes
do not create another recovery state. The exact private directory scope,
no-follow traversal, ownership and inode checks remain mandatory; links inside
an owned scratch tree are unlinked without traversing their targets. Persistent
ownership/removal journals are separate from scratch data and remain intact.

A completed matching TV cleanup receives current package, startup, routing,
activity, input and private-file absence checks. A retained legacy completion
can publish its final fence once; it does not reopen package removal or acquire
another destructive cleanup stage merely because the host still says pending.
This is source behavior for a future rebuilt installer, not published device
acceptance. See [implementation evidence](../history/2026-11-09-installer-removal-four-issues.md).
