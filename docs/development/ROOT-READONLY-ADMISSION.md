# Read-only admission for an interrupted Root install

When the original worker error is missing, start with the separate
[passive failure diagnostic](ROOT-PASSIVE-DIAGNOSTICS.md). It reads bounded saved
data without staging code or calling recovery/routing services. It cannot grant
cancellation admission, and third-party Home routing still blocks removal.

This maintainer procedure prepares a device-specific proof for the
[existing narrow cancellation tool](../ROOT-INSTALL-CANCELLATION.md). It is
not a recovery result or firmware support. The isolated entry/candidate lookup
is **unreleased**. Pin a reviewed source commit and generated code bundle before
any owner-side use. Do not substitute a release number for those exact bytes.

## Agree on the scope before connecting

For #133, the latest reporter response already answers the LG Home/control and
preserved-state questions. Do not ask for those historical answers again. The
original saved connection has not been rechecked. First ask only whether the
original installer profile is still available on the same PC user account;
this is not a request to reconnect, pair, reinstall or reset anything.

After that prerequisite, coordinate **one inspection** with the owner. Explain
that it uses their existing pinned SSH identity/host key; no new trust prompt,
password request or pairing is admitted. Authentication failure is a stop, not
permission to alter the saved profile, trust store or TV. Do not use ordinary
Restore, Uninstall, install/resume, recovery-service calls or retained runtime
status as substitutes for this procedure.

Read-only means no product/package/routing/LS2/recovery-state changes. It still
creates a new mode-0700 temporary code tree on the TV, uploads mode-0600 code and
removes that same tree after a successful invocation. It takes the local host
session lock and SSH may rewrite the existing known-host file. Original pending,
submission, snapshot and recovery records stay intact. Obtain agreement to this
bounded staging/connection before execution. This document authorizes no TV work.

## Prepare locally without a TV connection

Use the source checkout and dependencies from the cancellation runbook. Build
`build/root-recovery-code`, record the source commit and run `digest`. Save the
code digest privately with the exact generated bundle and both recovery modules.
Do not copy these modules into the original TV state or refresh an already
admitted cancellation to different code.

On the original installer PC, under its original user account, identify the
pending UUID with the following local-only command from that checkout. It emits
only an identifier; it does not print profiles, addresses, keys or diagnostics:

```sh
python3 - <<'PYTHON'
import re
from cytv.state import Store
store = Store()
operations = []
for profile in store.profiles():
    if profile['edition'] != 'root':
        continue
    pending = store.pending(profile) or {}
    identifier = pending.get('product_operation')
    if pending.get('action') == 'install' and isinstance(identifier, str) and re.fullmatch('[a-f0-9]{32}', identifier):
        operations.append(identifier)
if len(operations) != 1:
    raise SystemExit('Exactly one original pending Root install is required; retain state and request private review.')
print(operations[0])
PYTHON
```

No matching/ambiguous/corrupt profile is a blocker. Do not manufacture a UUID,
edit `operation.json`, use another PC's profile or copy credentials into an issue.
If a maintainer already knows the UUID, the host tool must still find exactly one
matching saved Root profile. The candidate may be omitted **only for inspect**:
it is read from that UUID's saved device request and verified by full admission,
including matching submission and recomputed snapshot digest. No latest-release
package, inferred route or guessed candidate is substituted.

## Inspect once, then stop for review

Use the exact `inspect` command in the cancellation runbook. It never falls
through to removal or reconciliation. Keep the small JSON response privately.
It contains only operation, original candidate/code/proof hashes, state, terminal
lease flag, payload count and `home_changed`; it excludes raw snapshots, LS2
contents, app inventories and unrelated Settings entries.

An `admissible` response is a source/evidence proof for one unchanged operation.
It does not authorize removal, show physical remote acceptance or demonstrate a
working installation. Review the original UUID, source/bundle pin, candidate and
proof together. A later mutation still requires explicit original candidate,
reviewed proof, unchanged code and fresh owner control confirmation, and repeats
all checks under the original locks. Do not run that mutation in this procedure.

On refusal, connection loss or timeout, stop and preserve the original state.
There is no proof and no permission to retry a package operation or relax a guard.
A failed invocation retains its unique staging tree; confirm that its process has
stopped before considering cleanup of only that tree. Do not upload raw stderr,
profiles, recovery directories or diagnostics. Arrange a private review if a
stable refusal reason cannot be extracted without those materials.

For the finalize-failure path, the existing proof checks Settings, inactive
ActivityManager state, the exact four LS2 registrations, original package/private
code/interpreter and absence of later readiness/activation state. It deliberately
does not query the missing System Profile service. It does not call Settings
writes, registration rescans, service activation, package removal, firmware/root
changes or recovery finalization. Other proof paths retain their existing
System Profile requirements.

## Firmware support remains a separate blocker

The observed combination of absent `defaultApps.home` and missing System Profile
cannot identify an effective Home route or its reversible write contract.
Working Home keys cannot establish that contract either. Do not treat absence as
LG Home, emulate profile replies, seed a Home setting or reuse a newer C3 result.
The [normal installation gate](HOME-INSTALL-GATES.md#root-firmware-interfaces)
remains fail closed; #82's absent-key setup requires readable effective profiles.
The older-firmware proposal in #107 also lacks reviewed contract/patch evidence;
it does not establish a compatible adapter for #133.

A future adapter needs independent evidence for effective route/default/idle
readback, write and readback semantics, preservation of unrelated defaults,
restoration after uncertainty, recovery permissions/activity and early-boot
behavior, followed by exact-firmware install/rollback/removal and separate
standby/cold-boot acceptance. Do not perform writes merely to discover an API.
No firmware upgrade or re-root is part of admission preparation.

## Private proof record and public updates

Keep source commit, bundle/code digest, original UUID/candidate, proof response,
model, firmware/webOS, remote (or unknown), original release/components, host
platform and expected/actual checks in the private handoff. Mark untested fields:
physical controls, sound, standby, cold boot, update and rollback. A historical
report is not a fresh inspection or completed recovery.

For another user's installation/recovery result, prepare a concise redacted
text and name its destination, then obtain the owner's approval before posting.
Remove credentials, addresses, serials, app inventories, private paths, snapshots
and raw recovery evidence. Routine issue comments may describe source preparation
and the pending prerequisite without claiming device work or publishing proof.
Keep the unresolved issue open; use `status:needs-info` only once the focused
owner prerequisite/proof request is actually outstanding. Partial source work
alone does not justify `status:released` or closure.
