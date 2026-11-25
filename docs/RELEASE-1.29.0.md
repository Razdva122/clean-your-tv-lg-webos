# v1.29.0

- Root and No-root leave the remote’s Back gesture to LG firmware. **Open LG Home** in Home settings remains available for a one-time visit.
- No-root Home stays resident when webOS supports background suspension. The Helper retries a late LG Home takeover after an IR Home press and stays available after a slow launch. A brief system transition can still appear (#820, #822).
- No-root Home uses tuner artwork when the TV provides no usable Live TV icon. The Helper checks that it can dismiss the screensaver popup before enabling it and falls back to LG's screensaver when that check fails (#835, #836).
- No-root setup can resume an interrupted SSH upload after verifying staged files. No-root removal can verify stock Home by alternate readbacks on firmware that explicitly reports an absent defaultApps setting (#834, #831).
- Root Beta preserves the QML compositor scripts and can clean up a verified pre-submission failure through the ordinary installer. Root recovery reports include the last observed local startup milestone (#832, #823).
- The Root guardian can recover Home after confirmed normal shutdown when the remote disconnects during shutdown. The C1 backend also discards optional return hints that time out and keeps sending its normal heartbeat (#821, #826).

| Component | v1.28.0 | v1.29.0 |
| --- | --- | --- |
| cytv installer | 0.24.2 | 0.24.3 |
| Home FHD/HD | 1.21.0 | 1.22.0 |
| Home Helper | 0.10.0 | 0.11.0 |
| Root edition | 0.24.2 | 0.25.0 |
| Both edition Updaters | 0.6.7 | 0.6.8 |
| Android installer / versionCode | 0.23.2 / 55 | 0.23.3 / 56 |
| No-root screensaver popup | 0.0.6 | 0.0.7 |

The [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/827) tracks artifact verification, tested devices and outstanding reporter confirmations.
