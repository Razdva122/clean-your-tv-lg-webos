# Issue #454 Home takeover attribution

Device publicly reported as OLED55C16LA, firmware 03.53.45, webOS SDK
6.5.3. Root edition and Windows host. Remote model unknown. The affected
preflight was CYTV 0.20.7 from v1.20.7. The [standalone report](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454#issuecomment-6894666532)
was diagnostic only and used a 0.17.2-based launcher. It recorded:

- `stat -f` returned `ef53`. The fixed Home executable path was covered by
  an ext4 file mount with writable VFS and superblock flags. The root mount was
  read-only SquashFS, and the `/usr` overlay had a read-only superblock.
- KeyFilters contained 16 entries, including one out-of-contract absolute
  path. The export retains the category `other-absolute`, not its value.
- The earlier [ELF header](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454#issuecomment-6765828462)
  and [file attributes](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454#issuecomment-6768229793)
  identify the file as UID 1001, mode 0755, size 4,530,960 bytes.

## Offline attribution and replay

The public ARM IPKs were verified against GitHub release asset SHA-256 values
and inspected without executing Luma. The packed executable in both
[Luma 2.18.0](https://github.com/ecklf/lg-luma/releases/tag/v2.18.0) and
[Luma 2.18.1](https://github.com/ecklf/lg-luma/releases/tag/v2.18.1) matches
all 52 reported ELF-header bytes, UID, mode and size. Their complete executable
SHA-256 values differ: `79d51c5446a8858ff940b32380e0b2694b02253427874b2a0135eea269ecdadf`
and `9daf8a444939a22d239aaadff6090da4cb4a0d921a6d4f031e02777dfda720d4`,
respectively. The 2.16.2 and 2.17.0 controls were 4,530,944 bytes and failed
the header match. This strongly identifies the earlier mounted file as Luma
without resolving its exact version or current on-device hash.

Luma's [2.18.1 takeover](https://github.com/ecklf/lg-luma/blob/v2.18.1/tv-helper/src/home.rs)
binds its executable over the native Home path and registers a Homebrew
startup hook. [Luma PR #88](https://github.com/ecklf/lg-luma/pull/88) adds
early boot support. Starting with the inspected
[2.19.0 package](https://github.com/ecklf/lg-luma/releases/tag/v2.19.0),
enablement for executable takeover can append the
[exact entry](https://github.com/ecklf/lg-luma/blob/v2.19.0/tv-helper/src/home.rs#L22-L26)
`/var/lib/luma-home/home-filter.js` / `lumaHomeKey`. Older matched IPKs
lack that filter. The timeline allows Luma to explain both observations at
different times. Live filter identity and the active installed version remain
unverified.

The verified CYTV 0.20.7 Windows desktop executable supplied the preflight
bytecode. The previously extracted LG C1 W21O 03.53.45 image supplied the 15
factory entries. The offline harness appended the exact Luma entry, used the
matched packaged ELF header, and modeled the reported ext4 file mount with
`stat -f` equal to `ef53`. The standalone probe returned 16 entries, one
`other-absolute`, and the same three mount rows. CYTV returned
`vendor-filesystem-unverified` and `path-outside-contract`. The original
15-entry chain passed. The mount sources and IDs were harness values.

## Device acceptance

No TV was contacted. A read-only comparison of the active Home executable
fingerprint and Luma's exact KeyFilters pair would confirm the live
attribution. No disable, install, routing check, standby, reboot or cold boot
has been observed on this C1 in this investigation.

## Maintainer decision for Root setup

Starting ordinary Root installation authorizes replacing the active Home
integration. The installer should handle a verified conflict automatically
in interactive and unattended setup. It should remove the competing mount,
filter and startup registrations from their active locations and continue
through ordinary CYTV preflight and activation. Scope file replacements and
removal to the resources that control Home. Keep a recovery snapshot and leave
unrelated apps and preferences intact.

For the Luma fixture, validate the active bind source and the exact
`home-filter.js` / `lumaHomeKey` entry. Snapshot the takeover state before
clearing the cold-boot hook and early-start registrations that can recreate the
bind. Re-read the mount and filter chain after the handoff, prove stock LG Home
beneath the file mount, and then activate CYTV. Account for the factory BSP
overlay separately from the single-file mount. Preserve recovery evidence if
the operation is interrupted or the live state changes during setup.

Acceptance is a complete Root installation from the Luma fixture without an
extra compatibility prompt, verified CYTV Home routing and no Luma takeover
after cold boot. Also verify retry after an interrupted handoff and the stock
C1 control with no competing integration.

## Implementation evidence

Ordinary Root setup checks the competing file bind and both the retained
filter chain and startup registrations. After the normal installation review,
a verified handoff runs automatically. The installer checks the uncovered
native Home in a private mount namespace, snapshots the competing takeover
state, and verifies the stock binary, filter chain and absence of the captured
startup paths after the live detach. A single-purpose literal boot bind is
also supported without an integration-specific name. Mixed shell programs,
unattributed registrations and a conflicting active Root installation stop
before takeover.

The recovery journal and archives reside at
`/var/lib/clean-your-tv-home-handoff` with root-only access. The saved
records keep the original takeover state, exact chain and scope of each
activation resource. An interrupted install can either restore the verified
pre-detach state or finish quarantine once stock Home is verified. The
program skips automatic mutation when the saved identity or routing has changed.

The host debug run used the hash-verified Luma 2.19.0 ARM IPK, the C1 factory
Home from W21O 03.53.45, and an isolated Linux container with a real
bind mount and a separate LS2 registration filesystem. The detached file
matched the factory ELF. The modeled configd chain changed from 16 to 15
entries. The script quarantined the startup symlink, dedicated takeover
folder and four LS2 registrations. The unrelated hook and launcher executable
remained accessible. The deployed compositor admission accepted the replay
using factory QML, with device IDs, LS2 and evdev input modeled.

The regular CLI fixture ran `install --yes --non-interactive`, repeated
preflight after the handoff, read the modeled catalog and reached the
installation call. Tests also exercised a second launcher with a literal
boot bind and interrupted handoffs before and after the native file was
uncovered. No package install, Home key, standby or cold boot has run on
the reporting C1. Live mount propagation, Python libffi and final Home
activation remain device acceptance checks.
