# Embedded LG Home adapter: offline implementation evidence

Related report: [#410](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410).
This is focused development evidence, not release acceptance or a confirmed fix
on the reporter's TV. No TV was accessed during this work.

## Inputs and admission

The public report identifies 60UJ6050-UA, firmware 06.10.55, SDK 3.9.0 and TV
Node 0.12.2. The implementation selects capabilities, not these identifiers.
Synthetic unrelated model/firmware/SDK observations also pass the same host
capability fixtures. Each actual activation rechecks the selected executable's
identity; its recorded hash is an integrity fence, not a firmware allowlist.

The official [LG support page](https://www.lg.com/us/support/product/lg-60UJ6050.AUS)
provided download file ID `ioviWIFd4xPc9WOroceQpQ`. The archive was extracted
offline with epk2extract source revision
`a0ccd8a4b4f48d05675a4cddd233f8780ee36767`. Extraction does not establish
cryptographic verification of LG's firmware signature.

| Input | SHA-256 |
| --- | --- |
| Download ZIP | `0e998a49d387be5dd6b37d8c30e05edca88d665f99e083327ec987ef59aa6c38` |
| EPK | `4313641107c4353170dd2f27436162d3ea540a50edb4fa5d1d02623fc2dfd758` |
| Stock compositor | `3436252e8f41b1a853d71c52105b84cefbb0f8d447aba68fa1af7cd30df10199` |
| Stock initctl | `5b95e00c521f121c922a0910db03caee016d067838848298db733fdc1f531303` |
| Stock init.upstart | `7248dcfe8f6011faa6526eea75d2264f0fd1654301f72121c13ab37682309415` |

Firmware files remain outside Git. The factory compositor job uses a script
ending in `exec $WEBOS_NICE /usr/bin/surface-manager-starfish -platform starfish`,
with respawn and no external QML override. The compositor contains the external
entry-file capability and its original QML resource. Its native policy chain
exposes `handleSystemKeys`; the adapter discovers that entry and imports the
stock policy enum instead of assuming an index, array length or enum value.

## Observed offline cases

| Case | Expected and observed result |
| --- | --- |
| Stock ARM Upstart/initctl, isolated D-Bus session | Explicit launch receives the wrapper URL; stop followed by an ordinary start receives no override. Passed. |
| Stock ARM compositor, actual Qt/QML VM | Adapter attaches to the original parentless stock root and intercepts a short Home pair. Passed. |
| Same QEMU run, real shared Python `watch()` | SIGKILL produces exit status -9 and EOF on CONTROL. The first following short Home pair reaches the original dispatcher; its Home down/up signals each fire once and YSM becomes `visible`. Passed. |
| Shared native guardian embedded target | Controller EOF latches routing off; cleanup closes only the owned Root app, without launching a nonexistent standalone Home executable. Passed. |
| Launch recovery fixtures | Cancellation, parent disappearance, interrupted stop/start, changed job/process identity, foreign entry file, busy transition, stock readback and supervisor retirement checked. |
| Recovery inventory | New executable QML/JS assets are required and hash-bound for schema4; historical inventories remain readable. Passed. |
| Stock ARM Luna client/hub | Named ordinary request reaches the hub and returns exact missing-service for an absent alias. `queryServicePermissions` is unsupported locally in this stock client library. |
| Embedded removal proof | Exact restored snapshot plus fresh exact missing-service reply verifies live/activatable alias retirement. Denials, malformed responses, timeouts and incomplete snapshots refuse removal. Other backend schemas keep their prior permission-query path. |

The stock SAM binary exposes `getAppLifeStatus`, not the newer
`getAppLifeEvents` subscription used for native-Home automatic return. Schema4
does not implement automatic return and therefore omits that subscription. It
reuses the controller's intent, guardian, attachment, startup-grace and CONTROL
health loop. Missing lifecycle APIs cannot silently prevent activation.

The QEMU fixture models SAM/OS status and lease-broker delivery through a local
bridge. The actual native guardian is tested separately. Display creation is
skipped at one digest-bound instruction; the stock root is parentless to avoid
the unavailable TV input/display stack. This proves neither rendered panel
presentation nor the complete production Loader, service activation and
guardian-to-QML transport together.

## Verification record

- Host Root-related suite: 262 cases, passed with 3 skips.
- Root suite: 1,428 cases, 5 skips; one old enrollment fixture expected the
  previous LS2 inventory. Its expectation was corrected and the affected
  removal/enrollment cases passed in the focused rerun. The unchanged full
  suite was not repeated solely for a second summary.
- Subsequent changed units passed separately: 67 shared C1 runtime, 20
  embedded runtime, 24 provisioning, 9 compositor recovery manifest, 112
  clean-removal and 3 transport cases. The JavaScript adapter passed 11 cases;
  the broker suite and unchanged shared filter also passed.
- After removing the unnecessary SAM lifecycle subscription, the affected
  native QEMU run was repeated against the changed controller. All six markers
  passed, including `controller-sigkill-eof` and `stock-home-visible`.
- Ordinary bundle integration: 9 cases passed using the existing verified
  source-font cache, without downloading fonts again.
- Shared C1 JavaScript filter and scoped formatting checks passed.

Reproduce the native cases in a disposable Linux container providing QEMU ARM,
GDB multiarch, squashfs-tools, Python, D-Bus and coreutils. Mount this checkout
read-only at `/project`, the extracted rootfs at `/stock` and EPK partition files
at `/image`. QEMU 7.2.22 was used. Run with networking disabled:

```sh
sh /project/root-edition/tests/embedded-home-native.sh
dbus-run-session -- sh /project/root-edition/tests/embedded-home-upstart.sh
```

The fixed compositor hash in the native fixture protects its display-skip
address only. Production admission has no such hash list.

## Remaining acceptance

Installation and removal on a target TV, actual production LS2 routing,
physical Magic Remote Home/hold/emergency input, panel rendering, other app
focus, HDMI/audio, standby, AC cold boot and rollback are untested. Network
remote input is also untested. Package delivery and public release are not part
of this record. Keep #410 open; its pending No-root Helper check is separate
from acceptance of this Root adapter.
