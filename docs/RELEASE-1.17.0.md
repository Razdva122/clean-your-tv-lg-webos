# v1.17.0 — Helper recovery, diagnostics and website

## Changes

- Preserve the original No-root operation while authenticating and reclaiming
  its retained pairing key after Helper ownership handoff (#488, #487).
- Recognize narrowly confirmed input disappearance during power-off without
  turning ordinary sleep into an emergency stop. Preserve explicit Stop,
  triple Home, Home Off, watchdog and cleanup-failure protection (#488).
- Restore private Helper state when firmware expands the mode of known boot
  records. Load the verified installer payload for saved No-root recovery and
  complete Root activation when there is no Helper process to stop (#510,
  #509, #487).
- Fix fresh System updater setup on TVs where reading a small cached file
  with the maximum buffer size exhausted memory. The installer reads the
  verified file size and still detects size changes (#508, #507).
- Share checked storage, lifecycle/power and recovery advice contracts. Retain
  bounded typed first-cause context in the standard diagnostic report (#493).
- Admit stock Home up to 16 MiB across installer, compositor runtime and guardian;
  vendor UID 1001 requires immutable SquashFS and read-only device evidence.
  Other file-integrity, recovery and input checks remain (#492, #494, #454).
- Redesign the multilingual website with recorded animated previews, a separate
  interactive demo and 52 practical articles across 13 languages (#470).

## Versions and packaging

| Component | v1.16.0 | Prepared target | Reason |
| --- | --- | --- | --- |
| Release | 1.16.0 | 1.17.0 | Website and shared-contract integration |
| Home FHD/HD | 1.15.0 | 1.15.1 | Renewal uses the changed shared storage contract; new Helper rollback baseline |
| Helper | 0.8.0 | 0.8.1 | Rebuild controller, relay, storage and power behavior together |
| cytv | 0.17.0 | 0.17.1 | Authenticated continuation, recovery advice, reports and corrected System setup |
| Android / versionCode | 0.16.0 / 31 | 0.16.1 / 32 | Changed shared installer sources and TV payload |
| Root / infrastructure | 0.16.0 | 0.16.1 | Changed compositor admission and guardian/support |
| Both edition Updaters | 0.5.7 | 0.5.7 | Actual packages and Root Updater bundle are byte-identical |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 | Fresh setup script and bundle manifest change; the installed supervisor package stays byte-identical |

Both-resolution Home/Root, ordinary/Beta support and embedding computer/Android
installers need coherent packaging. Preserve Android package ID and original
signer. No Homebrew Installer promotion is selected. No new permission grant,
network endpoint or persistent state format is introduced by this inventory.

## Validation and limits

The complete platform, browser and runtime build passed. The macOS, Windows,
Linux and Android installers passed embedded payload checks. The Android APK
retained the original signer and preserved recovery data in an emulator upgrade
from the published version.

On the maintainer C3 (43.21.71, SDK 11.2.0), the final No-root installer
completed the original pending operation after explicit Helper Start. Home
routing, Home Off/On, navigation, audio and remote-button standby worked. The
same Helper archive passed triple Home with the published rollback Home.
Active cold boot was deferred and remains unverified.

The corrected System setup completed on the same TV. The production-signed
Root set installed through the ordinary System worker, preserved Home Off
and retained the actual UI profile. The supported rollback restored Root
0.16.0, the original profile and controls. The same signed set then
installed 0.16.1 again. Root short Home and triple Home worked, with LG Home
active after the emergency exit.

The [verification ledger](history/2026-11-11-release-1.17.0-candidate.md)
records exact artifacts, device steps and limitations. The original #487 C2
and #454 C1 installations still need reporter confirmation on the published
installer.
