# v1.30.0

- The desktop installer can restore selected Debloat settings and, when the TV exposes the setting, turn off LG promotional streams. Check the result for each option before leaving setup (#851).
- Root Doctor reports whether the TV advertises Magic Remote Home and Back inputs. An advertised input is a diagnostic observation (#852, #364).
- The installer can distinguish an active Home process from installed package and service runtimes during No-root removal. Helper startup diagnostics record when the input worker becomes ready (#845, #846, #841, #152).
- No-root removal can resume after a verified Root handoff and use the firmware-appropriate LG Home readback (#847, #830).
- A previously submitted Root uninstall stays pending in the desktop installer if a different saved connection completes removal. Keep the original recovery receipt for investigation (#849, #368).
- The compatibility catalog records the reported physical Home check on an OLED55C47LA with a fresh No-root setup (#850, #635).
- System Updater Engine 1.2.18 carries the updated removal and recovery support.

| Component | v1.29.1 | v1.30.0 |
| --- | --- | --- |
| cytv installer | 0.24.3 | 0.25.0 |
| Home FHD/HD | 1.22.0 | 1.23.0 |
| Home Helper | 0.11.0 | 0.11.1 |
| Root edition | 0.25.0 | 0.26.0 |
| Both edition Updaters | 0.6.8 | 0.6.9 |
| Android installer / versionCode | 0.23.3 / 56 | 0.23.4 / 57 |

The [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/844) tracks tested devices and remaining limits.
