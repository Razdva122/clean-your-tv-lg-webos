# No-root package authority (#201)

## Scope and decision (2026-11-01)

The [original report](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201)
has pending **uninstall** after manual removal. The
[C2 follow-up](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201#issuecomment-6541747043)
has pending **install**, without manual deletion. These are separate state
machines. No device was contacted or changed for this investigation. The
regressions use synthetic inventories and private temporary host stores; they
are not new installation results for either device.

The supported outcome is **no alternative reconciliation admitted**. Status
must retain the legacy pending journal byte-for-byte. File hashes, manifests,
app absence, stopped Helper processes and an LG Home screen cannot establish
installer idle, original transaction termination or installed service registration.
The previous file-only/absence-only status reconciliation is removed. Normal
installation and explicit guarded removal are unchanged. No new endpoint,
permission, persistent state or automatic retry is introduced.

## Existing mechanisms and their limits

The official [TV CLI guide](https://webostv.developer.lge.com/develop/tools/cli-dev-guide)
provides app listing/install/removal. Source review is pinned to official
`webos-tools/cli` commit `ed7a6994be443207f3427b19f210f6606f004eb6`:

- [command-service.json](https://github.com/webos-tools/cli/blob/ed7a6994be443207f3427b19f210f6606f004eb6/files/conf/command-service.json)
  uses public `com.webos.applicationManager/dev/listApps` and
  `com.webos.appInstallService/dev/install` / `dev/remove`.
- [install.js](https://github.com/webos-tools/cli/blob/ed7a6994be443207f3427b19f210f6606f004eb6/lib/install.js)
  subscribes to the submitted install/remove call and waits for its terminal
  `details.state` (`installed` / `removed` or `SUCCESS`); acceptance/progress is
  not completion. Listing returns app inventory, not transaction history.
- cytv uses those same endpoint paths. Its transport keeps stdin open, waits
  through acceptance/progress, rejects negative replies and closes the channel
  on terminal success, denial, EOF, interruption or timeout. This does not
  persist a replayable original transaction receipt.
- Existing explicit recovery first calls
  `com.webos.appInstallService/status` with `{"subscribe":true}` and requires
  `status.apps == []` before removal. It currently takes the first positive
  response (`luna-send-pub -n 1`), not a retained install/remove subscription.
  Denial, timeout, missing state or a nonempty list blocks before checkpointing
  or mutation. This is an existing gate, not a newly proven cross-firmware idle
  contract. The reviewed CLI source supplies no replacement historical terminal
  query or evidence that a file snapshot can replace this gate.

The [C2 owner's exact-endpoint correction](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201#issuecomment-6556401396)
confirms that `/dev/listApps` succeeds and returns Home 1.6.0 and Helper 0.6.20.
The original denied probe used `/listApps`. The endpoint question is answered
for this C2; do not ask that owner to repeat it. Its reported `package-status` refusal does establish failure of
that attempt's existing recovery gate. Neither observation proves that the
original install completed. Package hashes in `operation.json` bind expected
content; they do not identify a live installer transaction or prove registration.

## Source follow-up (2026-11-02)

[The pinned source investigation and operation-bound handoff](NO-ROOT-TERMINAL-HANDOFF.md)
checks the official CLI and OSE installer implementation. In the reviewed OSE
implementation, status serializes the current task map and finished tasks are
removed; it is not a retained terminal journal. Repeating install/remove starts
another request. OSE source is supporting evidence, not a contract for retail TV
firmware. No supported historical readback was established, so neither legacy
pending action gains a reconciliation path. The handoff identifies the exact
vendor contract needed before a device probe can be designed.

<a id="normal-install-catalog-convergence-unreleased"></a>

## Normal-install catalog convergence

After both live `dev/install` streams return terminal success, the No-root
installer uses a ten-second polling budget for one `/dev/listApps` snapshot
containing both expected component versions. Each response-read timeout is
limited to the remaining monotonic budget, and mismatches are polled at intervals
of up to one second. A response arriving after the deadline cannot authorize
continuation. Existing SSH channel setup remains governed separately by the
shared transport; this is not a hard end-to-end wall-clock timeout.
This accommodates delayed SAM catalog visibility without repeating installation.
A current matching snapshot proceeds immediately; denial, timeout or malformed
inventory stops immediately. A persistent mismatch preserves the pending journal
and the latest component snapshot, without configuring or starting Helper.

This wait runs only inside the new installation's existing verification step.
`status()` and recovery do not use it to reconcile a legacy operation, and the
denied global-status guard is unchanged. It does not supply missing historical
terminal evidence or repair already pending installations. Synthetic host tests
cover the timing mechanism; the original #295 device cause and physical recovery
remain unverified. There is no new endpoint, permission, state format or user
confirmation. Shared console/desktop/Android packages need a normal future build;
this focused change does not select or modify a frozen release candidate.

## Remaining evidence

<a id="observer-storage-next-candidate-2026-11-07"></a>

### Observer storage (from v1.12.0)

The v1.11.0 storage correction keeps private observer evidence in `/tmp/.cytv-installer` (0700),
under verified sticky temporary ancestry. IPKs remain in the vendor SDK staging
namespace `/media/developer/temp`; the observer accepts the fixed root-owned
SDK containers with their retail permissions, while its private evidence keeps
the stricter ancestry rules. No vendor permission is changed. The public staging
path retains the SDK's shared-namespace trust limitation; inode checks do not
make the installer's later pathname open atomic with host verification.

Before recording pending, one storage check exercises private write/hardlink/sync
and public staging creation/removal. Failure leaves no new operation receipt or
capsule. This does not guarantee later writes against disconnects or full disks.

Already pending operations retain their journal/capsule. All earlier observer
sources, including partial installations, use the cleanup fallback after this
source change. A source mismatch or
lost volatile evidence cannot authorize replay. **Review recovery options** offers
the existing separately confirmed project removal, which archives the original,
skips absent packages and requires its normal full-restart verification. A new
setup is a separate action after verified removal; status never clears pending
because files are absent. Cleanup recognizes both the old and new private roots.
No new confirmation, package endpoint or recovery protocol is introduced.

The implementation has host regression coverage only; retail installation and
recovery remain unverified. See the [source record](../history/2026-11-07-no-root-observer-storage.md).

<a id="developer-mode-private-storage-selection-unreleased"></a>

### Developer Mode private storage selection

Developer Mode can expose a jail with an owned, writable `/` while `/tmp` is
execute-only. New Developer Mode operations first make one read-only selection
between `/tmp/.cytv-installer` and `/.cytv-installer`. A sole existing root is
retained; two existing roots refuse setup rather than hide another reservation.
An existing unsafe leaf is never repaired or bypassed. With neither root present,
the jail root is admitted only for a non-root UID owning its real parent, with
owner read/write/traversal and no group/other write bits. Otherwise the legacy
temporary root remains selected. The existing storage check must then pass all
private ownership/0700/ancestry, write/link/fsync and SDK staging checks before
pending is created. There is no fallback after storage refusal or package work.

New jail-root plans carry `private_root` inside the plan covered by the observer's
canonical hash and the host capsule digest. The host admits only the two fixed
Developer Mode locations. Continuation, observation and detached workers use the
original selected path; they never select another root when evidence is missing.
Legacy plans without the field still mean `/tmp/.cytv-installer`. Both bound
observer source strings are unchanged, so this addition does not invalidate
otherwise compatible existing capsules. Earlier incompatible sources retain the
historical confirmed-cleanup fallback described above. Root SSH keeps its exact
private/public roots and does not run selection.

Developer Mode cleanup includes the fixed jail leaf in its resident-worker,
staging-scope, idle and explicit sweep checks, retaining the ordinary restart
fence. It requires a real, owned `0700` leaf and strict private ancestry; foreign,
symlinked or writable private roots block cleanup. Root SSH cleanup does not
interpret `/.cytv-installer` in its different filesystem namespace as owned
Developer Mode evidence. Cross-namespace device cleanup is not established by
host fixtures. No parent chmod/chown, automatic migration or capsule editing is
introduced; SDK IPKs stay under `/media/developer/temp`.

The existing volatile restart-proof marker remains under `/tmp` with its original
strict sticky-parent checks. A persistent jail directory cannot replace proof of
a full restart. Firmware refusing that marker may still block explicit removal;
this change must not turn that refusal into a clean result or permission to replay.
Host continuation and cleanup fixtures do not establish physical installation,
restart proof, removal or compatibility on a reporting TV. Rebuild shared
desktop/console/Android installers and Root Updater's embedded cleanup bundle;
do not reuse a previously built candidate as evidence for these changed bytes.

The earlier conservative per-filesystem installation budget remains separate:
SDK package staging, private observer evidence and vendor package-manager scratch
are different needs. `storage.install` still checks the unpacked-package estimate
plus reserve on `/tmp` before selection. Zero available `/tmp` space therefore
stops before pending or package submission even with a writable jail root. This
change neither proves that vendor scratch is accessible in the jailed namespace
nor moves its estimate to the private evidence directory. Revising that estimate
requires separate filesystem/vendor evidence; it is not a workaround for a
capacity refusal.

### Original historical transaction contract

The next work belongs to maintainer research into terminal authority, rather
than another C2 inventory request. Before implementing reconciliation, establish
the following contracts; any later device observations require separately agreed
read-only scope and the original trusted Developer Mode identity:

1. Exact `/dev/listApps` evidence is complete for the C2 follow-up only.
   Keep the original UK6400 pending-uninstall case separate; do not transfer
   the C2 result to it. App inventory still cannot establish transaction completion.
2. The precise `appInstallService/status` response schema and semantics over its
   bounded subscription: initial acceptance, active operations, idle, termination
   and denial/disconnect behavior. Do not submit a new package transaction merely
   to collect evidence or assume initial subscription acceptance proves idle.
3. A supported, operation-bound authoritative terminal readback for the original
   transaction, plus package identity/version and installed service registration.
   Establish how it excludes still-active/partial/conflicting operations and
   survives restart. An SDK inventory listing alone does not supply this proof.

If the firmware cannot expose that authority, automatic reconciliation remains
unsupported. Keep the original journal/history and report the capability limit;
do not infer removal, reinstall, clear state or reset Developer Mode. No new
reporter probe was executed as part of this source-only work.

## Regression scope

Tests distinguish both pending actions and both app-list endpoints, and exercise
idle denial/timeout/active/unknown states without changing the host journal or
calling removal. Matching expected hashes and both app versions, or absence after
manual removal, cannot clear pending. Transport fixtures cover acceptance,
progress, terminal success, denial, interrupted EOF and timeout for both install
and removal. These are host models; actual service registration, UI controls,
sound, standby, cold boot, OTA and rollback remain untested.

## Vendor-normalized pairing-key mode (#437, unreleased)

An authenticated Developer Mode install continuation may restrict the existing
`ssap-key.json` mode from exactly 0775 to 0640 after Helper is observed stopped
or stale. Both configuration leaves must first pass the existing ownership,
regular-file, single-link and no-world-write checks. The key must belong to the
current SSH UID; an opened no-follow directory and file descriptor bind the
change to the checked inode. The mode change preserves key bytes, UID and GID,
and does not alter `apps.json`, `blocked`, watchdog or controller state. Other
unsafe modes, foreign owners, links and substituted paths still refuse.

This repair runs before the existing configuration claim/upload so the immutable
observer can keep enforcing private key permissions. Both bound observer source
strings, operation plans, capsules and package receipts remain unchanged. Root
SSH keeps its previous behavior. Status/configuration readback remains read-only
and does not repair permissions or reinterpret missing transaction evidence.
An emergency stop still prevents automatic Helper launch until reviewed through
the existing TV controls. No new endpoint, persistent record or permission grant
is introduced; embedding desktop/console/Android installers require rebuilding.

The exact reported refusal and corrected host continuation are covered by
synthetic filesystem/process regressions. The origin of the firmware's 0775 mode
and acceptance on the reporting C2 remain unconfirmed. See the
[dated verification and limits](../history/2026-11-08-issue437-key-mode-repair.md).
