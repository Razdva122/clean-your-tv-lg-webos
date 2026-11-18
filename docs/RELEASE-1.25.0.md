# v1.25.0

- Desktop, CLI and Android guide you through the original TV connection when
  setup or removal is interrupted. Check a failed prerequisite again, observe
  an unconfirmed package request or continue an authorized uninstall after
  Restore or restart. Package presence and the Home-button result are reported
  separately. Desktop and Android can prepare a local issue draft from the
  diagnostic report (#718).
- No-root Home can recover status and refresh the live app catalog if webOS
  changes the private Home control directory to mode `0775`. Install the updated
  Home and Helper together. Confirmation on the reported C1 is pending
  (#721, #720).
- On LG 65NANO913NA with firmware 04.64.00 and webOS 5.6.2, a verified
  normal startup can resume an explicitly enabled Root Home route. Restore
  verifies the factory LG Home destination. Explicit Off and emergency Stop
  require another explicit Enable. Device confirmation is pending
  (#714, #716, #710).
- Root restores LG Home if the active input device disappears during standby
  preparation. A matching standby confirmation can retain the intent for the
  next normal startup. Incomplete evidence leaves LG Home in control. The
  reported G3 standby sequence remains to be confirmed (#723, #702).
- The native Root guardian can recover a recreated Magic Remote input device
  within its existing safety deadline. Recovery requires one validated
  replacement and released keys. Real device recreation remains to be
  confirmed (#728, #615, #702).
- Root diagnostics retain the available installation classification and
  cleanup refusal code. Diagnosis of the reported B1 installation and cleanup
  failures remains open (#719, #678).

- Root removal on webOS 5 can recognize the stock LG Home ribbon while
  Live TV remains the foreground app. The fix applies to removal after a
  native UI-release failure. The reported provisioning failure remains open
  (#726, #722).
- After verified full removal, a stale receipt from another saved connection
  no longer blocks fresh installation on the same TV. The installer archives
  superseded receipts and retains newer or unverified operations for recovery
  (#727, #152).
- The device catalog records confirmed removal recovery, Root reinstallation
  and physical Home routing on LG OLED65C1PSA with firmware 03.53.45, from
  the owner's public v1.24.0 report (#725, #418).

| Component | v1.24.1 | v1.25.0 |
| --- | --- | --- |
| cytv installer | 0.21.3 | 0.22.0 |
| Android installer / versionCode | 0.20.3 / 50 | 0.21.0 / 51 |
| Home FHD/HD | 1.20.3 | 1.20.4 |
| Home Helper | 0.9.1 | 0.9.2 |
| Root edition | 0.21.3 | 0.22.0 |
| Both edition Updaters | 0.6.2 | 0.6.3 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.12 | 1.2.13 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/724)
for build and device verification.
