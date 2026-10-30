# C5 Home settings and renewal storage investigation

Date: 2026-10-26. Investigated source: `1b9273f470bd4cd635cce12eefc92c6d68a39891`
and published v1.2.0 / Home 1.4.1. This is an investigation, not a product fix
or physical-TV acceptance record.

## Conclusions and evidence limits

There are three independent boundaries:

1. Home Helper's native controller and relay handle the physical Home button.
2. Home settings uses the Home package's renewal service to exchange request and
   response files with that controller in another package's state directory.
3. Developer Mode renewal stores its own settings under the renewal service's
   installation directory.

A working Home button establishes neither successful file access by the renewal
service nor a successful status RPC from the launcher. Developer Mode SSH access
is a fourth execution context; its ability to collect Helper diagnostics does not
establish the renewal service's filesystem access.

The supplied device report and user confirmation establish successful Home
handling during one recording on OLED65C5RLA / webOS26 11.2.0-3706. They do not
contain the renewal service's filesystem error, effective identity, mount table,
or the failed launcher's `homeStatus` reply. The installation was subsequently
removed. No TV was contacted for this investigation. We cannot distinguish an
actual C5 `EACCES`, `EROFS`, hidden path (`ENOENT`), invalid configuration, bus
denial, or response timeout using the existing reports alone.

## Why the settings switch does not operate

In published Home 1.4.1, `launcher/renewal-panel.js:49-58` renders any failed,
timed-out or malformed `homeStatus` response as “Home Helper unavailable. Open
Home Helper, then reopen settings.” It leaves a disabled switch visible, even
though its actual value is unknown. `homeEnabled` remains `null`, so the click
handler at line 60 refuses a write. This explains the non-operating switch and
the misleading off appearance without requiring a stopped Helper.

The actual path is:

```text
Home launcher PalmServiceBridge
  -> com.gathin.tvhome.renewal/homeStatus
  -> validate caller application ID
  -> write/chmod/rename Helper state/home-request.tmp to home-request.json
  -> native controller reads request and writes home-response.json
  -> renewal service reads matching response, within five seconds
```

See `renewal-service/service.js:60-66`, `renewal-service/home-control.js:18-29`
and `native/app/native.js:76-92`. A write/chmod/rename exception becomes
`Home Helper data unavailable` without retaining the filesystem error code.
Response read errors are swallowed; after five seconds they become
`Home Helper did not respond`. A caller mismatch returns
`caller-not-authorized` before submitting a request. The UI conflates them all.

The Helper tile first uses a different path:
`com.local.nativehome.service/status`. This is a cross-package bus request.
[Issue #59](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/59)
contains an actual denied-method reply on a C2, independently of the file broker.
Its published manual-start fallback does not fix the settings file broker.
Starting Helper again does not change these access boundaries.

Current `release/next` already includes
[PR #71](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/71), which
hides an unknown switch and changes the message. It explicitly does not repair
the status transport. Do not describe that UI correction as a working toggle fix.

## Where storage-error comes from

`renewal-service/service.js:4,11-16` reads `state/settings.json` underneath its
own `__dirname`. Saving creates `state` if missing, writes `settings.tmp` mode
0600, then renames it. `renewal.json` uses that same directory.

`renewal-service/manager.js:5` converts any configuration load exception other
than the service adapter's handled ENOENT into `storage-error`. At line 9,
**any rejected queued operation** is also converted to `storage-error`, including
non-storage exceptions. The response can have `returnValue:true` while its
`state.error` is `storage-error`. That means the service answered, not that
renewal succeeded.

Consequently the message is not a specific disk-full diagnostic. It loses both
the failed operation and the underlying error code. Invalid settings JSON can
produce the same initial display as unreadable settings. A newly missing
settings file alone produces `{enabled:false}`, without an error; a subsequent
failed save can produce the screenshot's error state.

### Published package inspection

Downloaded the actual
[published Home 1.4.1 IPK](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.2.0/com.gathin.tvhome_1.4.1_all.ipk)
and verified its digest against the release SHA256SUMS:

```text
d92cc6cf4597a285a045dbd24b900ae784c0711585e49b4ba6e78daa8214de68
```

The archive contains:

```text
usr/palm/services/com.gathin.tvhome.renewal/   uid=0 gid=0 mode=0755
service.js, manager.js, local-io.js, ...     uid=0 gid=0 mode=0644
```

It does not contain `com.gathin.tvhome.renewal/state`. In contrast, the Helper
builder explicitly provisions its own writable state directories. No equivalent
provisioning was found for renewal in the cytv package builder.

This is a concrete packaging/runtime assumption: the service depends on being
able to create a directory inside its installed package. If the installer leaves
that parent foreign-owned 0755, or the service sees a read-only mount, saving
fails. A service with no owner-write access reproduces this exact failure.
**Archive ownership is not proof of the installed directory's ownership, mount
flags or the service's effective permissions on this C5.** The device cause
remains a strong access-boundary hypothesis, not a measured errno.

## Reproduction

Run on a non-root local account:

```sh
node docs/research/2026-10-26-c5-settings/reproduce.cjs
```

To test published code, extract the release IPK's renewal-service JS files into
a temporary directory, then pass that directory as the first argument. Both
the published files and current source passed the same seven assertions.

The harness runs the actual service registration, manager and file-broker code.
It substitutes a local webOS message bus and renewal worker; it never reads a
TV session token, contacts a TV/LG endpoint, or schedules an activity. Filesystem
permission denials in the first and third cases are real local OS errors. The
unwritable directory models missing runtime write access, not actual TV ownership.

| Case | Observed result |
| --- | --- |
| Missing configuration, then enable under an unwritable parent | Initial status has no error; mkdir gets EACCES; enable returns storage-error and disabled |
| Invalid settings JSON | Initial status returns storage-error without a failed write |
| Helper directory inaccessible to broker | home-request.tmp write gets EACCES; returns Home Helper data unavailable |
| Writable request but no visible correlated response | Returns Home Helper did not respond after timeout |
| Unexpected scheduling exception with working save | Incorrectly categorized as storage-error |
| Different caller application ID | caller-not-authorized before Home request submission |
| Writable service storage | Enable succeeds with error=null |

Existing focused tests also passed: `renewal-manager.cjs`, `renewal-storage.cjs`,
`home-control-bridge.cjs` and `controller-home.cjs`. They use local filesystem
state or simulated controller/bus contexts and do not model the actual TV jail.

The complete `scripts/test.sh` passed with the prepared Python environment at
`/private/tmp/c4-test-venv/bin` and loopback access. The initial sandboxed attempt
stopped at `helper-compat.cjs` because the sandbox denied its local WebSocket
listener (`listen EPERM 127.0.0.1`); the full rerun completed with exit code 0.
No product source was changed. Node syntax and document whitespace checks passed.

## Required next correction and device evidence

Do not equate the two storage locations or conclude that the C5 controller
crashes. The working controller and failing settings broker are separate facts.

Before choosing the transport/permissions fix, capture bounded service-context
diagnostics at the actual failing boundary:

- For renewal: load/mkdir/write/rename versus unexpected-operation failure, and
  an allowlisted errno/category. Distinguish JSON corruption from permission,
  read-only filesystem and disk-full errors.
- For Home: the launcher-context RPC result, the failed broker operation, and
  whether the controller received the matching request. Distinguish caller/bus
  rejection, missing/inaccessible path and response read/timeout.
- Compare effective service/controller identities and accessible directory
  metadata privately. SSH-shell permissions alone are insufficient.

Export no tokens, configuration contents, pairing keys, arbitrary exception
messages or raw mount/process logs. Current doctor/Home recording reports do
not collect these boundaries, so repeating those reports cannot resolve them.

The eventual fix must provision persistent storage writable in the actual
service context and use an IPC path accessible to both participants, with
existing caller validation and correlated replies preserved. Merely chmodding
the shared platform tree, granting world write, bypassing status validation,
auto-starting Helper, or displaying an enabled switch cannot establish a fix.
Verify settings changes and renewal persistence on the C5 after a future normal
installation; assess standby and cold boot separately. No reinstallation is
requested solely for this investigation, and no physical fix is claimed.

LG's [JS service basics](https://webostv.developer.lge.com/develop/guides/js-service-basics)
lists Node 20.12.2 for webOS26 and explains service file access. The official
[JS service usage](https://webostv.developer.lge.com/develop/guides/js-service-usage)
describes same-app service packaging. Neither establishes that an installed
third-party service can write this project's chosen cross-package state path.
