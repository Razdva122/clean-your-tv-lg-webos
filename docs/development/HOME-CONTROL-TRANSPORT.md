# No-root Home settings transport

[Development references](README.md) · [Diagnostics](../SETTINGS-DIAGNOSTICS.md)

<a id="unreleased-correction-for-146"></a>

## Service transport correction for #146

The original broker used the Helper application's absolute `state` path from a
jailed JavaScript service. LG documents that JS services can access their own
files but cannot assume access to another app/service's files:
[JS service usage](https://webostv.developer.lge.com/develop/guides/js-service-usage).
A hidden application mount produces `home / write / ENOENT` before the controller
can receive the request. A working native Home controller does not establish
visibility from the renewal service's separate filesystem namespace.

Scoped [project C3 source QA](../history/HOME-CONTROL-TRANSPORT-QA-2026-10-29.md) confirms the
channel and actual jail visibility; it is not frozen release or C1 acceptance.

The regression runs the actual service entry point with a filesystem adapter
that exposes only its own package. Before the correction it reproduces the
reported `write / ENOENT`; afterward the authorized Home RPC completes through
the service-owned channel. This models mount visibility, not an observed C1 mount
table. The exact C1 namespace and effective permissions remain unmeasured;
the subsequent C3 source-QA observations are recorded separately.

## Ownership and protocol

Home submits to `__dirname/state/home-control`. The native controller polls the
corresponding installed renewal-service directory and replies there. The native
Developer Mode environment must expose that directory. This was observed in
the project C3 source-QA run; other devices remain unverified. No jail
configuration or platform mount is changed.

Both the renewal `state` directory and its `home-control` child are packaged as
`prisoner:jailer` (5999:5000), mode 2770. The setgid bit makes files inherit the
shared group across the service and controller's different UIDs. Request and
response files retain mode 0660. Renewal preference/history files retain their
existing private modes. Only these two owned leaf directories receive these
permissions; SDK parents and application/service code directories stay unchanged.

The service still checks the caller application before I/O. The protocol retains
its fixed three commands, boolean validation, random request ID, five-second
expiry, request serialization and correlated response. There is no socket,
network endpoint, broad LS2 grant or automatic Helper start/resume. A stopped
controller remains stopped; unavailable status stays unknown. The native
controller still reads the old channel for older Home packages, with independent
request-ID tracking. New Home submits once to the new channel; it does not replay
an uncertain command through the legacy channel.

Both build paths provision the channel. Installer personalization retains its
ownership/modes. Installed rollback capture retains only its empty `.keep`
sentinel and fixed directory metadata; settings, history, requests and replies
remain excluded from the package. Existing mutable-state preservation handles
preferences separately. A nonempty/indirect sentinel is rejected rather than
copied into a baseline.

## Packaging and acceptance gates

Keep versions unchanged during preparation. At candidate freeze, select new Home
and Helper versions, synchronize manifests, rebuild Home/renewal and Helper,
embedded desktop/console/Android payloads, and verify a compatible signed Helper
transition and rollback pin. The builders deliberately reuse the immutable
published Helper 0.6.19 archive while that version remains selected: source edits
alone do not deliver this correction. A Home-only update with the old Helper
cannot complete the new channel; never advertise that combination as repaired.

The changed installed-baseline capture is computer-side setup code; existing
fixed supervisors are not automatically replaced. Verify both a newly captured
corrected baseline and historical rollback packages at freeze. An old Home still
uses its old channel and retains that version's limitations on jailed firmware.

On the maintainer/project-owned test TV, record its model, firmware/webOS, remote
and exact candidate versions, then verify safe diagnostics,
then status, explicit Home off/on, one-time LG Home visit, physical Home/Back and
unrelated keys, triple-Home stop and intentional resume. Separate standby from
true AC-off cold boot. Also verify renewal persistence and no automatic enabling,
a signed whole-edition update/rollback, and service/controller access in their
actual execution contexts. Keep #146 open until delivery and requested device
acceptance on the project test device; a C1 retest is not a release gate.
Results on the project device do not establish C1 or other-model compatibility.
