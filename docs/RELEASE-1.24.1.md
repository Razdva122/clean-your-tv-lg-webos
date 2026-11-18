# v1.24.1

- After a successful desktop connection check, choose **Continue setup** to
  reuse the selected TV, edition and connection. A pending operation offers
  recovery first, and the wizard checks current cleanup status before asking
  for another restart (#704).
- Root Beta removal supports the stock Node 0.12.2 runtime and verifies live
  LS2 permission rollback before removing the preview package (#705, #692).
- **Set up my TV → Root → Reinstall Root** can replace an eligible retained
  compositor installation with Home control off and recovery verified.
  Reinstallation resets saved Clean Your TV preferences. The original Home
  activation issue remains open (#708, #615).
- An already-open global Root screensaver can survive a brief status gap.
  Opening a new screensaver or deferring LG's screensaver still requires
  fresh Root status (#709).

| Component | v1.24.0 | v1.24.1 |
| --- | --- | --- |
| cytv installer | 0.21.2 | 0.21.3 |
| Android installer / versionCode | 0.20.2 / 49 | 0.20.3 / 50 |
| Home FHD/HD | 1.20.2 | 1.20.2 |
| Home Helper | 0.9.0 | 0.9.0 |
| Root edition | 0.21.2 | 0.21.3 |
| Both edition Updaters | 0.6.2 | 0.6.2 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.12 | 1.2.12 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/703)
for build and device verification.
