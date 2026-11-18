# Root Beta final-status envelope on the B9

The [new public report in issue #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160#issuecomment-6969774668)
comes from CYTV 0.21.2 on Linux x64, OLED65B9PLA, firmware 05.50.00 and
SDK 4.10.0. Previously reported webOS is 4.10.2-31. The remote is unknown.
The failure is `final-status / failed`. The passive snapshot observes a
patched runner, patched pending and ready proof runner hashes, activity and
startup-hook receipt files, an open deploy lease and the retained
`provision-finalize-starting` stage. Receipts alone do not prove live activity
or boot behavior. The public report does not contain the actual LS2 payload.

The installed service's handler wraps the Python CLI envelope in another
`result`. A verified reply has this shape:

```json
{"returnValue":true,"root":true,"result":{"returnValue":true,"result":{"recovery":{"integrity_verified":true}}}}
```

The repair checked `result.recovery` instead of `result.result.recovery`.
It therefore rejected every normally wrapped reply, including verified
integrity, before writing the completed deployment stage. The fix reads the
Python result and requires the root process, successful Python envelope and
verified integrity. Negative and malformed replies remain failures.
This proves a deterministic installer defect consistent with the report;
it does not establish the reporter's undisclosed integrity result.

## Offline verification

Reused the exact official W19H B9 05.50.00 image and v1.21.0 installed
package from the [original offline investigation](2026-11-16-issue160-beta-recovery.md).
In a disposable container with `--network none --cap-drop all`, QEMU ARM
ran the factory Node 0.12.2, vendor bootstrap, webos-service, LS2 hub and
luna-send. The existing packaged JS service served status from a fixture
with the already-patched runner and both proof files. The Python child used
the retained runtime's actual integrity verifier against actual manifest
hashes, including the native guard. Container Python substituted for the
private TV interpreter, its binding verification was modeled, and the
native board status was represented by the fixture. Lab LS2 policy and
Activity Manager were modeled as in the previous investigation.

The resulting reply contained `root=true` and the nested
`integrity_verified=true`. The old final-status expression rejected it.
The fixed final-status code, extracted directly from the candidate source,
accepted that same reply. Controls with non-root, negative Python and
failed integrity replies were rejected. No repair or provisioning was
invoked in this replay. Installation file hashes matched before and after
status; the service's PID, startup telemetry and lab log were excluded.
Python bytecode writes were disabled for the observer child.

The earlier replay supplied a simplified Python child result without the
CLI envelope. That fixture missed this defect and its final repair success
cannot establish correctness of the real status envelope. This replay
corrects that boundary. The regression now executes the real JS handler
with the Python CLI envelope, fails on the old code and passes on the fix.
The startup suite passed 10 tests and provisioning passed 17 tests.
`git diff --check` passed.

No reporter device was contacted. Application removal, repeated recovery,
Home routing, sound, physical input, standby, cold boot, OTA and rollback
were not run on the reporter's B9. Actual live integrity and installation
completion remain device acceptance gaps. This change requires delivery
through the normal release flow.
