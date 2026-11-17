# v1.23.0

- On rooted TVs with the compatible System Updater, **Update all** can update
  the updater itself before applying the selected Root or No-root release.
  **Recovery → Reinstall System Updater** repairs the installed updater version
  while keeping Home and its settings. Existing Root installations with
  System Updater 1.2.10 can use the [one-time computer
  replacement](UPDATES.md#update-root-from-v1220). Replacement verifies retained
  records from the earlier supervisor format (#675).
- No-root Home and Screensaver settings can explain a stopped Home Helper
  and offer **Start Helper**. If the status is unavailable, you can retry the
  check or explicitly confirm a start. The settings check again after launch
  (#682).
- The screensaver package has its own landscape icon (#681).
- Root Beta can repair an eligible interrupted recovery-service setup in place
  after confirmation. Setup does not activate Home as part of the repair.
  Physical B9 confirmation remains pending (#676, #160).
- Root recovery can reconcile a retained CYTV filter after a specific native
  refusal, when the current runtime verifies stock LG Home and routing.
  Diagnostics include the refusal and the recovery step. Confirmation on the
  reporting C1 remains pending (#677, #418).
- No-root removal can complete when the TV confirms Helper removal and only
  verified empty Helper directories remain. Physical removal and reinstallation
  on the reporting EF950V remain unverified (#680, #152).
- The localized installation guides focus on first setup and link to advanced
  procedures. The compatibility list records the reported No-root installation
  on LG 43UQ75003LF (#672, #673, #654).

| Component | v1.22.0 | v1.23.0 |
| --- | --- | --- |
| cytv | 0.21.0 | 0.21.1 |
| Android / versionCode | 0.20.0 / 47 | 0.20.1 / 48 |
| Home FHD/HD | 1.20.0 | 1.20.1 |
| Home Helper | 0.9.0 | 0.9.0 |
| Root edition | 0.21.0 | 0.21.1 |
| Both edition Updaters | 0.6.0 | 0.6.1 |
| Screensaver | 0.0.5 | 0.0.6 |
| System Updater | 1.2.10 | 1.2.11 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/674)
for build and hardware verification.
