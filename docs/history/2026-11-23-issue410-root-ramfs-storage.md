# Issue 410: Root staging on confirmed ramfs

[Reporter result](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410#issuecomment-7109112026)
provides the following public installation evidence. No reporter identity,
connection details or raw diagnostic is copied here.

| Field | Observation |
| --- | --- |
| TV | LG 60UJ6050-UA |
| Firmware / SDK / Node | 06.10.55 / 3.9.0 / 0.12.2 |
| Remote | Unknown; no remote-input test in this report |
| Edition / installer | Root Beta, cytv 0.24.1 console on Linux x86_64, Python 3.12.16 |
| Existing Home / Helper | 1.20.5 / 0.9.3; installation inventory only |
| Attempt | Native backend schema4 selected; Python inventory matched; stopped at storage.check before package submission |
| Expected / actual | Proceed to Root installation / `tv-storage-ramfs` refusal |
| Home, audio, standby, cold boot, rollback | Untested by this attempt |

The diagnostic establishes the ramfs guard, not damaged flash or a measured
storage shortfall. No USB workaround was attempted. Earlier No-root Home
routing was confirmed publicly; that is separate from Root acceptance.

## Root cause and selected fix

The native installer still uploaded the entire bundle into `/tmp`, even though
its observed package-submission helper already exposes the verified IPK from
`/var/lib/clean-your-tv-installer`. Root preflight refused ramfs's zero block
capacity. The fix selects a private internal payload source at
`/var/lib/clean-your-tv-root-staging` after capability checks. It does not
change `/tmp`, LG's mount configuration or any daemon environment.

Large native/product/updater/migration payloads use that source only for a
confirmed ramfs layout. Normal measurable `/tmp` budgets remain unchanged.
Small coordinator and package-free recovery support keep the existing volatile
lifetime. Disk demand includes the extra retained source copy. Vendor scratch
is still RAM-backed: its estimate uses expanded package blocks plus the
existing 16 MiB reserve, compared with live `MemAvailable` or conservatively
`MemFree`. Unknown or insufficient resources refuse package submission.

The fixed private root must have UID 0, mode 0700, protected non-symlink
ancestors and the same filesystem as its checked `/var/lib` anchor. A nested
memory mount cannot masquerade as disk. Uploaded nested directories remain
0700; payload files are private. No model, firmware or SDK value authorizes
storage selection. USB is not a dependency or an automatic fallback.

The host saves source paths before uploading bytes. Terminal native/product
readback permits retirement of the exact uploaded hash inventory. Unknown
outcomes preserve their source, pending receipts and duplicate-submission
barriers. Cleanup understands both fixed roots; unknown files are never
recursively removed as an installation shortcut. Recognized but unlinked
partial sources can remain as reported temporary evidence rather than being
silently discarded.

## Exact firmware and offline environment

Reuse the [W17M image provenance](2026-11-20-embedded-home-adapter.md): EPK
SHA-256 `4313641107c4353170dd2f27436162d3ea540a50edb4fa5d1d02623fc2dfd758`,
pinned epk2extract revision
`a0ccd8a4b4f48d05675a4cddd233f8780ee36767`. Extraction success does not establish
verification of LG's firmware signature. Firmware files stay outside Git.

The exact factory files show `/tmp` mounted as ramfs, `RW_FS_TYPE=ext4` and
`/var` bound from `/mnt/lg/cmn_data/var`. `/var/lib` is a real directory;
`/var/tmp` instead points to volatile storage and is unsuitable as a persistent
candidate merely because of its name.

Stock BusyBox SHA-256 is
`53697918b4091e80310ea39e4c15bf6ba1a8b2e3bd08798cd604a956b9f63ca8`.
Stock appinstalld SHA-256 is
`3103987d8598b83a2ebdd664a137c7a2294a2f4256388a718e81ff0fa262e3b5`.
The factory daemon is launched with CHARSET, and its binary contains fixed
`/tmp/`, `/tmp/alias` and `/cryptofs/tmp` strings. A caller's TMPDIR cannot
redirect an already-running daemon. Its actual scratch peak is not established
by these strings and the daemon was not run.

QEMU ARM 7.2.22 ran stock BusyBox and Node with the image's loader/libraries in
an offline disposable Linux container. `/tmp` was modeled with an actual ramfs;
private data/app partitions used disposable disk-backed XFS volumes. Factory
configuration establishes ext4 on the TV; the runtime control does not claim
to emulate ext4, TV mounts or a complete boot.

Important harness correction: `qemu-arm -L` prefixes existing absolute paths,
not just libraries. Pointing it at the full rootfs redirected `/var/lib` stats
to extracted factory files, while new descendants hit the container volume.
The final harness uses `/qemu-libs` containing **only** `lib` and `usr/lib`
links to the stock libraries. This makes storage paths resolve consistently to
the disposable live filesystems. The initial mismatch was a harness artifact;
production filesystem identity checks were retained.

## Observed cases and verification

- Stock BusyBox on writable ramfs reports `0/0/0` blocks and magic `858458f6`.
  The original guard refusal is reproduced.
- The changed Root preflight admits positive internal disk and live RAM
  evidence. Stock Node creates a 0700 staging root and nested private source,
  including an executable guardian fixture, then verifies and retires it.
- Unknown extra bytes refuse retirement before any authenticated payload is
  deleted. Symlink roots and separate tmpfs mounts are refused without adoption.
- Stock Node initially rejected a strict-mode block function declaration;
  replacing it with a function expression resolved the legacy-engine failure.
- Host regression fixtures cover missing/low RAM, MemFree fallback, full or
  unknown disk, unsafe parents, source-path receipts before the first byte,
  unknown outcomes, normal `/tmp` routing and exact successful retirement.
- Device cleanup fixtures cover both fixed roots, unsafe/unknown entries,
  coordinator identity, pinned product retirement and legacy recovery paths.
  The implementation PR lists final affected test counts and platform skips.

Focused verification ledger (final changed units; unchanged successful cases were
reused rather than rerun for branch/status changes):

| Unit | Result |
| --- | --- |
| Root host suites | 279 cases, 3 skips; six outdated filesystem fixtures were corrected and all 26 affected cleanup/recovery cases passed in the focused rerun |
| Installation operations | 97 passed |
| Storage / private staging | 11 / 7 passed |
| Beta migration | 9 passed |
| System Updater / remote directories | 11 / 1 passed |
| Device private staging | 5 passed |
| Device final cleanup tail | 81 cases, 3 platform skips |
| Clean removal | 113 cases passed, including two import-setup corrections retried separately |
| Installation driver | 55 cases passed, including one filesystem-fixture correction retried separately |
| Optional handoff | 1 platform skip |
| Stock ARM storage integration | Passed; includes unknown-file preservation, nested executable source retirement, symlink and separate-memory-mount refusal |
| Formatting / whitespace | Scoped Prettier and git diff check passed |

To reproduce the firmware integration, mount the checkout read-only at
`/project` and extracted image at `/sysroot`, provide QEMU/Python/mount tools,
mount disposable disk-backed volumes at `/var/lib` and
`/media/developer/apps`, disable container networking and grant mount capability
only inside that disposable container:

```sh
mount -t ramfs ramfs /tmp
mkdir -p /qemu-libs/usr
ln -s /sysroot/lib /qemu-libs/lib
ln -s /sysroot/usr/lib /qemu-libs/usr/lib
LC_ALL=C LANG=C python3 /project/root-edition/tests/root-ramfs-storage-offline.py
```

## Remaining acceptance

No TV was accessed or changed in this investigation. Actual Root package
installation, appinstalld peak RAM, live permissions/activation, physical Home,
visual/audio/HDMI behavior, standby, AC boot, removal and rollback remain
unverified on the reporting TV. Offline storage admission is not Root hardware
acceptance and does not close the original issue. Do not ask for another report
merely to repeat the already reproduced filesystem guard.
