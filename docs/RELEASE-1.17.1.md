# v1.17.1 — setup, recovery and app catalog fixes

- No-root setup activates Home after a successful install and preserves an
  explicit Stop issued during setup (#495). Helper startup also handles
  firmware-expanded permissions on known private state records (#514).
- Stop and removal recover known firmware-expanded Helper storage without
  clearing an existing emergency Stop. The installer preserves proof of a
  completed Root-to-No-root handoff across a restart.
- System Updater setup can continue after a verified transition from Root to
  No-root. Previous removal records remain available for recovery.
- The Home app picker refreshes confirmed app removals and installed app icons.
  Helper inventory replies also restore the app catalog at startup (#505).
- Weather city search renders results on legacy webOS browsers (#499).
- No-root removal can verify the boot marker when Developer Mode's temporary
  directory allows traversal without listing (#472).
- Root setup and cleanup retain the original diagnostic cause. If native setup
  lacks deployment evidence, the installer can offer verified full removal.
  The original reports in #101, #397 and #418 remain open for diagnosis.

## Versions

| Component | v1.17.0 | v1.17.1 candidate |
| --- | --- | --- |
| Home FHD/HD | 1.15.1 | 1.15.2 |
| Helper | 0.8.1 | 0.8.2 |
| cytv | 0.17.1 | 0.17.2 |
| Android / versionCode | 0.16.1 / 32 | 0.16.2 / 33 |
| Root / infrastructure | 0.16.1 | 0.16.2 |
| Both edition Updaters | 0.5.7 | 0.5.8 |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.8 / 1 |

The Android package ID and signing identity are retained. Homebrew Installer
promotion remains disabled. The [candidate verification ledger](history/2026-11-11-release-1.17.1-candidate.md)
records the compatibility probe, build and device acceptance.
