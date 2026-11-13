# v1.20.2

- No-root uninstall uses the standard webOS package removal service for
  registered apps. Recovery and uninstall can verify stock LG surfaces on older
  TVs where the LG Home app cannot be launched directly (#586, #152).
- Interactive Root setup checks whether No-root can run over the existing SSH
  connection when the required Home interfaces are unavailable. No-root over
  root SSH supports confirmed ramfs and checks disk space before submitting
  packages. The user explicitly chooses the edition (#592, #593, #410, #541,
  #587).
- Root removal can resume past incomplete temporary uploads after verifying
  they are inactive. Root diagnostics preserve the blocked inspection or
  installation reason (#589, #591, #594, #216, #418, #588).
- Regression coverage includes cleanup after interrupted native deployment and
  legacy Root preflight on the LG 43UK6450PLC (#590, #595, #101, #383).

The original reports still require verification on the affected TVs.

| Component | v1.20.1 | v1.20.2 |
| --- | --- | --- |
| cytv | 0.20.1 | 0.20.2 |
| Android / versionCode | 0.19.1 / 38 | 0.19.2 / 39 |
| Home FHD/HD | 1.18.1 | 1.18.1 |
| Home Helper | 0.8.4 | 0.8.4 |
| Root / infrastructure | 0.19.1 | 0.19.2 |
| Both edition Updaters | 0.5.12 | 0.5.13 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/596)
for artifact verification and device acceptance.
