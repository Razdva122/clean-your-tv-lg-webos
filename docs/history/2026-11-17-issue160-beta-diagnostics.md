# Root Beta failure-stage diagnostics

In [issue #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160),
CYTV 0.21.1 from v1.23.0 reached the private Python command on an
OLED65B9PLA with firmware 05.50.00 and SDK 4.10.0. The failed recovery report
contained SSH exit 1 but no stage from the device. The original Root Beta
installation came from v1.21.0 (Root 0.20.0), and the reporter used Linux x64.
The remote model is unknown. The report does not establish which writes,
if any, completed on the physical B9.

The standard report now allows fixed stages and bounded RPC counters from
the repair command. The failed command also tries a read-only observation.
On the saved Beta connection, `cytv status --edition root --root-variant
node012-beta` includes a snapshot of the launcher, manifest runner hashes,
deployment lease, available receipts and most recent startup record. At
the interrupted finalize stage with no local pending operation, the
installer uses the passive snapshot without invoking retained recovery
code. It treats receipts as evidence of local files, not proof of live
Activity Manager or boot state.

## Offline replay

Reused the verified LG W19H 05.50.00 image and v1.21.0 embedded Root Beta
bundle from the [in-place recovery investigation](2026-11-16-issue160-beta-recovery.md).
The isolated QEMU 7.2.22 lab ran the factory ARM Node 0.12.2, launcher and
Luna components with the original packaged service. The old runner exited
with code 0 before serving status when the test Activity Manager went
silent. The experiment then let the corrected runner serve status and
injected a timeout at the separate persistent registration step.

The repair emitted `register / timeout`. The stock Node passive reader
reported the original runner and pending proof before repair and the patched
runner and pending proof afterward. Readiness and activity receipts were
still absent. The two observations left file hashes and inventories
unchanged. All 148 installed package files and the original failure report
also matched after the failed repair.

The lab modeled the persistent registration response, stock Home readback
and Python runtime binding. The injected timeout is not evidence of the
physical B9 failure stage. Physical status, Home, sound, standby, cold boot,
OTA and rollback were not tested. No TV was contacted.
