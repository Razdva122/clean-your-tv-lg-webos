# v1.18.0 — HDMI tiles and installer improvements

- Pin HDMI inputs next to apps in Root and No-root Home. Pinned inputs retain
  their position when temporarily unavailable (#524).
- Weather starts with automatic location when enabled and no city is saved.
  A saved manual city takes precedence (#530).
- The Home settings panel retries Helper status once when the first check
  fails. Starting Helper still requires confirmation (#515).
- The desktop installer and interactive CLI offer an optional Debloat step.
  All settings start unselected. Readable original values are saved, but
  restoring them from the installer is outside this release (#520).
- No-root removal can check the foreground through an existing TV pairing on
  affected firmware. If the foreground cannot be confirmed, removal stays
  pending (#539). The installer also distinguishes unmeasurable ramfs space
  from a measured storage shortfall (#527).
- Root setup recognizes the verified read-only BSP overlay layout and reports
  more specific Qt admission failures (#517, #522).
- Updated Root and System Updaters retry interrupted cleanup of verified
  installer staging at startup. Existing System supervisors do not receive this
  change through ordinary component OTA (#523).
- Added compatibility records for the LG UM7450PLA and OLED42C24LA with the
  scope of each reported result (#521, #526).

## Versions

| Component | v1.17.1 | v1.18.0 |
| --- | --- | --- |
| Home FHD/HD | 1.15.2 | 1.16.0 |
| Helper | 0.8.2 | 0.8.2 |
| cytv | 0.17.2 | 0.18.0 |
| Android / versionCode | 0.16.2 / 33 | 0.17.0 / 34 |
| Root / infrastructure | 0.16.2 | 0.17.0 |
| Both edition Updaters | 0.5.8 | 0.5.9 |
| Fresh System / protocol | 1.2.8 / 1 | 1.2.9 / 1 |

Fresh setups use System Updater 1.2.9. The existing explicit replacement
eligibility remains unchanged. See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/540)
for CI and hardware acceptance.
