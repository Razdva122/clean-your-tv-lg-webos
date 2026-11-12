# v1.18.1 — Legacy webOS and installer fixes

## No-root

- Restore the shared Home Helper channel for Home status and **Add app** when
  webOS changes the installed directory mode to 0775. The fallback requires
  both updated packages (#544, #505).
- Developer Mode setup can proceed when the installer confirms that `/tmp`
  uses ramfs with no measurable capacity and verifies space on
  `/media/developer` (#550, #434, #541).
- Reinstall asks Home Helper to stop and verifies that it exited before
  replacing packages. After reinstall, select **Start Helper** to turn it
  back on (#554).
- The diagnostic report records which checks required a restart during
  No-root removal over Developer Mode SSH (#545, #472).

## Root and shared changes

- Root Settings shows an unknown **Change Home** status when it cannot confirm
  the current value and offers **Check status** after a failed read (#548, #355).
- Root Home can return after the foreground app exits on firmware that omits
  the window type in the stop event (#551).
- **Check TV status** can read a matching interrupted native Root setup
  receipt without staging Python (#547, #101).
- On legacy webOS, the Home and Updater services load each certificate in the
  bundled TLS trust store. The Down key can move from the final Weather
  option to the settings footer in both Home editions (#552).
- The desktop installer selects the Debloat options initially and applies them
  after **Continue**. Clear individual options or skip the step. Debloat
  reads and writes through LG Settings Service on Root SSH connections (#553).

## Versions

| Component | v1.18.0 | v1.18.1 |
| --- | --- | --- |
| Home FHD/HD | 1.16.0 | 1.16.1 |
| Helper | 0.8.2 | 0.8.3 |
| cytv | 0.18.0 | 0.18.1 |
| Android / versionCode | 0.17.0 / 34 | 0.17.1 / 35 |
| Root / infrastructure | 0.17.0 | 0.17.1 |
| Both edition Updaters | 0.5.9 | 0.5.10 |
| Fresh System / protocol | 1.2.9 / 1 | 1.2.9 / 1 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/549)
for package verification and device acceptance.
