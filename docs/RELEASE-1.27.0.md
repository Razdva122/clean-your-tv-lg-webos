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
- Root preserves the previously active Home preference during an update when
  boot recovery runs or the updater repeats a verified suspension (#762).
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

- Root can recover and resume a verified retained Home activation in place.
  It can reuse the C1 backend for supported embedded LG Home configurations,
  recover the route after an input lease expires, and offer LG Home after a
  safety stop. The embedded path needs target-device verification
  (#763, #769, #771, #772, #781).
- Removal resumes after a verified restart when terminal-service cleanup is
  pending, handles stock Home over content on webOS 6, and checks Root
  reinstallation when a lifecycle controller PID has been reused
  (#764, #765, #768, #775).
- A completed install that fails the Home button check now identifies that
  check in the issue draft. No-root Home diagnostics can include foreground
  window details when webOS reports them. The reported YouTube startup
  redirection remains under investigation (#793, #794).
- The Android installer includes its desktop operation bridge. The replacement
  build uses versionCode 54 so it can upgrade both the previous stable APK
  and the code 53 development APK (#776, #787).
- Home can remove an unavailable downloaded theme after rollback. The
  installer explains how to retry a refused TV remote connection
  (#784, #788).

| Component | v1.26.0 | v1.27.0 |
| --- | --- | --- |
| cytv installer | 0.23.0 | 0.24.1 |
| Android installer / versionCode | 0.22.0 / 52 | 0.23.1 / 54 |
| Home FHD/HD | 1.20.5 | 1.20.7 |
| Home Helper | 0.9.3 | 0.9.4 |
| Root edition | 0.23.0 | 0.24.1 |
| Both edition Updaters | 0.6.4 | 0.6.6 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.14 | 1.2.16 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/761)
for build and verification evidence.
