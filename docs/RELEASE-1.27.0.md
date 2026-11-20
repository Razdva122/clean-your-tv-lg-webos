# v1.27.0

- Choose **Română** in Root and No-root Home. Automatic language selection
  recognizes Romanian system locales, and updates preserve the selected
  language in saved profiles (#744).
- Root Beta can migrate its retained startup runtime in place while keeping the
  installed app and settings. The runtime checks the native guard and shutdown
  capabilities before allowing reboot resume, and keeps explicit Off and
  emergency stops authoritative (#751, #754). The migration and rollback passed an
  offline replay with the B9 firmware. Physical startup and remote behavior on
  that model still need confirmation.
- Root recovery uses local request activities on legacy webOS. A separate repair
  command can resume a supported interrupted Root setup from its original saved
  receipt. Diagnostics distinguish initial input readiness from a heartbeat
  timeout (#745, #746, #753).
- Root removal can recover a verified Python cache and stream the authenticated
  cleanup program when the firmware's process argument budget is too small.
  Cleanup covers verified package metadata remnants (#738, #749, #758).
- No-root cleanup can continue after a failed Root setup left only the shared
  Python cache. Root activation can roll back its filter after independently
  verifying that LG Home returned (#757).
- On Linux, the installer can use the system certificate bundle to download
  the pinned private Python runtime when its default bundle is absent (#742).

| Component | v1.26.0 | v1.27.0 |
| --- | --- | --- |
| cytv installer | 0.23.0 | 0.24.0 |
| Android installer / versionCode | 0.22.0 / 52 | 0.23.0 / 53 |
| Home FHD/HD | 1.20.5 | 1.20.6 |
| Home Helper | 0.9.3 | 0.9.3 |
| Root edition | 0.23.0 | 0.24.0 |
| Both edition Updaters | 0.6.4 | 0.6.5 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.14 | 1.2.15 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/761)
for build and verification evidence.
