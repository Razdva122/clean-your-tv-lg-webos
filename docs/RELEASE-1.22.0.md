# v1.22.0

- Open **Home settings → Appearance → Screensaver** in Home or Root to choose
  the built-in clock and date or a personal photo or video. The available scope
  depends on the installed edition and TV. Preview the selection from settings.
  On No-root, run the installer to deploy the screensaver companion.
- Root systems on v1.21.0 with System Updater 1.2.9 need the one-time
  [supervisor replacement](UPDATES.md#update-root-from-v1210). Start it with
  LG Home active, then reopen Clean Your TV from the app list before selecting
  **Update all** on the TV. The signed Root update adds the screensaver companion
  and its service permissions. **Rollback** restores the previous Root release,
  including its prior screensaver package and permissions.
- Home Helper reports more about its current routing mode and startup. Weather
  temperatures no longer show a leading plus sign (#660, #662, #666).
- Root Restore recovers a verified managed Python installation obstructed by
  generated cache files. Results on the original reporting TV remain open
  (#668, #389).
- Root setup can hand off a verified native Home replacement before installation.
  The installer also records fresh routing diagnostics when a physical Home
  check fails (#657, #661).
- **Reconnect after factory reset** can start a fresh No-root setup through
  Developer Mode while retaining the previous connection and removal history
  (#667, #664).
- New Root Beta bundles keep the private recovery service available while the
  legacy dispatcher waits for a per-request Activity Manager response. Physical
  B9 boot and repair of older partial installations remain open (#670, #160).

| Component | v1.21.0 | v1.22.0 |
| --- | --- | --- |
| cytv | 0.20.9 | 0.21.0 |
| Android / versionCode | 0.19.9 / 46 | 0.20.0 / 47 |
| Home FHD/HD | 1.19.0 | 1.20.0 |
| Home Helper | 0.8.7 | 0.9.0 |
| Root edition | 0.20.0 | 0.21.0 |
| Both edition Updaters | 0.5.17 | 0.6.0 |
| Screensaver | — | 0.0.5 |
| System Updater | 1.2.9 | 1.2.10 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/658)
for exact build and hardware verification.
