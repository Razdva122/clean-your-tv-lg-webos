# v1.10.0 — practical removal and installer recovery

Unpublished release candidate. Downloads are not public until publication completes.
Final package/device acceptance is pending; source checks do not establish TV compatibility.

## Changes

- Explicit removal cleans present project packages and known owned files after successful, partial or interrupted setup (#363). Missing objects are skipped. A real full restart stops old resident controls/installers before the final cleanup when required. Connection loss offers **Try again** for the same approved TV/goal. Actual OS busy/access errors remain explicit; protected Root residue requires Root access. Final success requires verified absence, not an old install result.
- Removal compatibility covers modern Node stdin execution, fixed SDK shared directories and known historical Root/System receipts. Broken optional old services use the same boot-before-cleanup checkpoint; diagnostic codes and Retry advice remain specific. [Source verification](history/2026-11-07-removal-compatibility.md).
- Installer recovery preserves the original connection, payload and first-failure evidence, distinguishes Root password from Developer Mode credentials, and observes future No-root install subscriptions. Existing unknown package outcomes stay unknown. All 13 guides/locales describe retry and restart without a separate recovery wizard. The original device reports remain partially unresolved pending their actual supported recovery/confirmation.
- Root startup waits for the active System profile and validated health before reporting readiness (#352, #357). Home-off completion remains separately confirmed; retained runtime diagnostics distinguish recovery and complete setup (#354). The original #334 cause and device recovery are unconfirmed.
- Updater cache and sealed completed staging retirement are bounded; active recovery evidence and referenced blobs remain protected (#349). Retained System 1.1.2 does not receive new supervisor hooks through a Home-only update.
- Wallpaper continuity, theme-trial restoration and colour consistency improve in Home/Root; Ribbon 1.3.1 includes the corrected Black Hole poster (#358). Readable size/4K/motion badges and maintained Crăciun 1.2.0 UHD/FHD still video are included (#360). Still video does not imply native 4K image detail.
- Root app refresh reads the full installed catalog; shared visibility/deduplication keeps an actually discovered Live TV app. Development utilities are excluded from Add app without removing saved tiles (#361).
- Installation guides are simpler and Czech extends to desktop/Android/Homebrew/website interfaces (#356). Matching authenticated PR test units can be reused; unverifiable or changed units run afresh (#346).

## Versions and delivery

| Component | Published 1.9.0 | Candidate 1.10.0 |
| --- | --- | --- |
| Home FHD/HD | 1.10.0 | 1.11.0 |
| Home Helper | 0.7.4 | 0.7.4, byte-identical |
| cytv | 0.10.0 | 0.11.0 |
| Android / versionCode | 0.9.0 / 23 | 0.10.0 / 24 |
| Root / infrastructure | 0.10.0 | 0.11.0 |
| Both edition Updaters | 0.4.5 | 0.5.0 |
| Fresh System Updater / protocol | 1.2.2 / 1 | 1.2.3 / 1 |

Rebuild Home/Root, updater/infrastructure and all platform installers. Helper retains
its authenticated published bytes; no new Helper lifecycle/shared-UID or removal-observer
framework ships. Five cleanup/cancel helpers are authenticated in the installer
stage only, preserving the published persistent Root Updater/OTA path set. Existing interrupted operations keep their original pins. Fresh
System changes do not add general supervisor migration or retrofit older rollback
packages. Homebrew Installer promotion remains disabled without accepted evidence.
Android keeps its application identity and original signer.

## Validation and limits

See [practical removal source evidence](history/2026-11-06-practical-clean-removal.md)
and [candidate PR #350](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/350)
for the exact selected build, checks and remaining acceptance. The candidate remains
draft until its complete build and affected physical acceptance are recorded.

No TV removal/installation was performed in this implementation task. Physical Home
routing, remote, sound, standby, cold boot, OTA and rollback on these candidate bytes
remain untested. Earlier firmware observations retain their original artifact scope.
Third-party files/Home settings are preserved; genuine ownership backups and minimal
non-executable removal evidence may remain. Saved computer connection keys/reports
are not TV residue and are retained.
