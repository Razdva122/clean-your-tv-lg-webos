# W19P Root removal: cleanup exec budget

## Public report and scope

The [latest public report in #692](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/692#issuecomment-7022302802)
uses v1.25.0 / cytv 0.22.0 on 55UM7450PLA, firmware 05.40.97,
webOS SDK 4.10.0, system Node 0.12.2, Root Beta, macOS CLI.
Host architecture and remote model are unknown for this run. A fresh Root
installation stopped at activation; ordinary Uninstall then stopped at
`requested` with `OSError`, errno 7, and `original-writer-active`.
The reporter observed LG Home and a responsive TV, without another ls-hubd
crash, and completed manual removal and reboot. No-root over Root SSH then
installed successfully after remaining package metadata was removed.
Standby, AC cold boot, sound, OTA and rollback were not established by this
follow-up. These are public technical observations, not a new device test.

## Boundary and fix

`LocalDevice.shared_cleanup()` verifies the bundled cleanup program, then
previously passed every byte as one `node -e` argument. This is an early
subprocess boundary before original writers are fenced. The generated
v1.25.0 program is 104556 bytes, below Linux's usual 128 KiB per-argument
ceiling; the reported errno alone does not prove that ceiling was reached.
The combined argument/environment budget can also reject this invocation.
The report does not identify the child boundary or the TV's process limits.

Stream the verified bytes through the existing Node 0.12-compatible stdin
loader, with a fixed marker and the small JSON request still in argv.
Source hash admission, environment filtering, request selectors, timeout,
locks and LS2 rollback ordering are preserved. There is no new persistent
state, permission or endpoint. This transport change intentionally matches
[PR #749](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/749), which
addresses the same boundary for #160. Integrate the shared edit once; the
W19P replay and package-stub regression here supply separate #692 evidence.
The frozen release scope/build are unchanged by this focused PR.

## Offline firmware replay

Reused the exact W19P image already extracted for the preceding investigation.
[LG's model support page](https://www.lg.com/uk/support/product-support/cs-55UM7450PLA.AEK/)
lists Software File 05.40.97 for 55UM7450PLA.AEK. The archive contains
`starfish-dvb-secured-k5lp-grampians-29-05.40.97_prodkey_usb_V3_SECURED.epk`;
its extracted platform identifier is `05.40.97.01-HE_DTV_W19P_AFADABAA`.
The retained epk2extract log reports successful header/partition verification;
extraction and those prior signature results were reused, not rerun.

- ZIP SHA-256: `ed58b65b6b1192b6f382712f883bd10325573ae63b400447edf97633d6aaaf67`.
- Factory `/usr/bin/node` SHA-256: `dd6abfe10aa293a12b8e12e75ca49e4e753a91a6d9da5e38a2530c7b4e487349`.
- Generated v1.25.0 cleanup source SHA-256: `2eab6ae9c9f275f9012ef7ade04aedabd505f4c69ee9ae74299c6371a9c82a4a`.

In a disposable Linux container with networking disabled, all capabilities
dropped, read-only firmware/source mounts and writable temporary storage,
QEMU ARM 7.2.22 ran the factory Node and libraries. The invocation used:

```sh
qemu-arm -E LD_LIBRARY_PATH=/firmware/lib:/firmware/usr/lib \
  /firmware/lib/ld-2.24.so /firmware/usr/bin/node ...
```

Using the loader explicitly avoids QEMU `-L` redirecting `chdir('/')` into
the firmware tree, which initially caused the cleanup's directory identity
check to reject the lab layout. No production guard was weakened.

The replay assembled the published program from the v1.25.0 Python source
and its three trusted JS contracts, relocating filesystem namespaces into
the disposable fixture. With an explicitly modeled 512 KiB stack and 32 KiB
environment padding, the former invocation failed with errno 7. The candidate's
actual `LocalDevice.shared_cleanup('inventory', {})` passed with the same
source and budget. These limits are not measurements from the reporting TV.
Container Python substituted for the TV's private interpreter.

The same candidate adapter and factory Node removed isolated packageinfo-only
stubs for Root Preview, TV Home, Home Helper and Screensaver. Only inventory
and the explicit package-sweep action ran; no live routing, LS2 or device
operation was performed.

## Verification and remaining acceptance

The host regression executes the current JS, padded beyond 128 KiB, while
modeling Linux's per-argument ceiling on macOS. It fails with errno 7 before
the transport change and passes afterward. Inventory preserves the stubs;
explicit project sweeps remove them and preserve a foreign package. A changed
script digest is rejected before execution.

Focused commands use the repository virtualenv and these selectors:

```sh
PYTHONPATH=.:root-edition:root-edition/tests "$PYTHON" -m unittest \
  test_simple_removal test_cleanup_tail
"$PYTHON" -m unittest discover -s tests/cytv -p test_root_clean_tail.py
PYTHONPATH=.:root-edition:root-edition/tests "$PYTHON" -m unittest \
  discover -s tests/cytv -p test_simple_root_removal.py
```

Across the three selections, 118 cases ran: 113 passed and five were skipped
for optional exact host runtimes or Linux-root-only fixtures. The changed
regression and factory replay also passed after aligning the fixed marker
with #749. Independent code review found no actionable issue.

The package metadata directories are already within the owned cleanup scope.
`FRESH_PROBE` must continue to reject retained Root package stubs rather than
silently treating an incomplete manual removal as a fresh TV. No probe bypass
or broader deletion was introduced. User setup and controls are unchanged;
localized guides need no change for this transport fix.

This verifies the reproduced exec boundary, not complete removal on the
reporter's TV. The precise original failing child, ordinary end-to-end removal
on the rebuilt installer, routing and hardware acceptance remain unverified.
Do not reinstall Root Beta on the now-working No-root TV solely for this test.
The original issue remains open. Rebuild Root updater/coordinator support and
its enclosing installer payload when this change is selected for a release;
no release/component version or candidate selection is changed here.
