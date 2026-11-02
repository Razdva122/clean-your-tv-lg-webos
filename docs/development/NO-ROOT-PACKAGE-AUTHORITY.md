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

## Remaining evidence

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
