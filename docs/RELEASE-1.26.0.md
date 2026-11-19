# v1.26.0

- Home Helper checks the foreground again before an automatic startup launch.
  An app you already opened stays in front while Helper starts handling Home
  input. The reported Quick Start+ off sequence on webOS 4.5 still needs device
  confirmation (#730, #686).
- The desktop installer explains when Root reinstallation is waiting for a
  restart. After restarting the TV, use **I restarted the TV — check and continue**.
  The diagnostic report retains the checks that required the restart (#731).
- Root and No-root updates preserve explicitly selected Simplified and
  Traditional Chinese Home preferences. Android Root setup can keep, change or
  reset the Home screen name (#732).
- System Update and Repair capture the Root profile once Home has rendered.
- The screensaver is enabled when you have never set a preference. A saved Off
  choice is preserved. The desktop installation switch for sorting apps starts
  at **Keep current settings** (#733).
- The compatibility catalog groups reported results by TV family and webOS
  generation. Each report links to its evidence and describes the observed
  scope (#734).
- No-root removal can complete when verified empty service directories remain
  after package removal. Files, registrations or running processes still require
  cleanup. Confirmation on the reported EF950V remains open (#735, #152).
- LG screensaver requests continue through a timestamp rollover. Root can
  renew its LG subscription after a rejected reply (#736).

| Component | v1.25.0 | v1.26.0 |
| --- | --- | --- |
| cytv installer | 0.22.0 | 0.23.0 |
| Android installer / versionCode | 0.21.0 / 51 | 0.22.0 / 52 |
| Home FHD/HD | 1.20.4 | 1.20.5 |
| Home Helper | 0.9.2 | 0.9.3 |
| Root edition | 0.22.0 | 0.23.0 |
| Both edition Updaters | 0.6.3 | 0.6.4 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.13 | 1.2.14 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/729)
for the candidate build and verification.
