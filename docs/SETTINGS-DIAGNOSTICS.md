# Home settings diagnostics

[Documentation](README.md) · [Feedback and privacy](FEEDBACK.md)

The published diagnostics help identify failures; they do not by themselves fix
the unresolved C5/webOS26 status transport. The [packaged transport correction](development/HOME-CONTROL-TRANSPORT.md)
for [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146) moves requests into the renewal service's own package; it requires coordinated Home/Helper packaging and physical acceptance.

## Collecting a report

On No-root Home, open **Settings → Developer Mode → Show diagnostics**. Viewing
this panel does not enable auto-renewal, start Helper or change Home routing.
Wait for the Home status request to finish; an already visible diagnostic report
updates when its response arrives. Share the displayed report with the TV model,
firmware and the observed Home-button behavior. Do not publish raw logs or keys.
The report receives remote focus when opened. Use Up/Down to scroll its card;
at a scroll boundary focus returns to an action. Left/Right and Enter return to
the surrounding actions, and Back returns to Home settings.

The report includes the installed renewal **serviceVersion**, not a hard-coded
launcher version. `diagnostic` describes the current renewal/settings failure;
`home` records the latest result of each Home RPC in this settings session:
`homeStatus`, and `setHomeControl` / `openLGHome` only if used. A failed action
remains distinguishable from its subsequent successful status refresh.

Each diagnostic has three allowlisted fields:

```json
{"component":"settings","operation":"mkdir","code":"EACCES"}
```

- Components: `settings` (renewal preferences), `renewal` (check history), or
  `home` (controller request/response transport).
- Operations distinguish read/parse, mkdir/write/rename, Home request chmod,
  response wait, caller authorization and the launcher's RPC boundary.
- Codes distinguish access denied (`EACCES`/`EPERM`), read-only filesystems
  (`EROFS`), space/quota failures (`ENOSPC`/`EDQUOT`), missing paths (`ENOENT`),
  invalid JSON/state and timeouts. Unrecognized exceptions become `UNKNOWN`.
- A bounded numeric `errorCode` may accompany a bus failure. Its presence alone
  does not prove why the bus rejected the request. Raw `errorText` is omitted.

Paths, credentials, arbitrary exception text, raw service replies and unrecognized
status strings are not copied into the displayed report. Diagnostics are held
in memory, not added to persisted renewal preferences or history. They describe
the observed attempt; a service restart cannot recover a previously lost errno.

## Interpreting a working Helper with unknown settings

The native controller can handle physical Home while the renewal service cannot
reach its request files. Developer Mode SSH, the native controller, the web
launcher and the renewal service are different execution contexts. A successful
SSH recording does not establish filesystem access from the service context.

When status cannot be verified, the switch stays hidden/disabled. The Helper
panel also reports unknown Home status instead of recommending reinstall solely
because this request failed. Starting Helper again cannot repair an access denial.

`storage-error` now means a failure at a known configuration/history I/O or parse
boundary. An unexpected queued-operation exception is `internal-error` instead.
Neither error is automatically a disk-full diagnosis. Historical reports whose
`launcher` field says `1.2.0` used a hard-coded diagnostic value; it was not proof
of the actual installed Home version.

## Scope and remaining device verification

Related reports: [#12](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/12)
and the separate cross-package status denial in
[#59](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/59).

This change does not alter storage locations/ownership, grant permissions,
introduce a service endpoint, change the file protocol, restart Helper, or clear
an emergency stop. In published packages, the missing writable renewal-state directory remains an
access/provisioning hypothesis until effective service permissions are measured.
The #146 transport change provisions only the renewal service's two owned
state/channel directories; it does not change platform mounts or shared SDK
parents. Effective C1/C5 service/controller access remains unverified.

Reported acceptance target: OLED65C5RLA, webOS26 / 11.2.0-3706. Expected: show
the exact safe failure category while preserving actual Home-button behavior.
The initial implementation used host tests. Subsequent [project C3 source QA](history/HOME-CONTROL-TRANSPORT-QA-2026-10-29.md)
verified the new channel in actual unprivileged jails; C5 status/control and renewal
persistence remain unverified. Standby and cold boot require separate checks.
The original C2 acceptance request in #59 remains independent.

At candidate freeze, rebuild/version Home and the embedded desktop/console and
Android payloads, and synchronize the affected manifests. Shared settings CSS
also requires rebuilding Root Home and both Updaters. Helper 0.6.19 and its
published archive pin are unchanged. No compatibility claim follows from the
host tests or package dependency check.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="home-settings-diagnostics-next-candidate"></a>
