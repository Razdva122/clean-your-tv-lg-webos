# v1.20.0

## Home and installation

- On compatible TVs with the legacy LG Home ribbon, the installer can offer
  No-root over the existing root SSH connection when Root Home checks fail
  (#575). Compatibility on the reported LJ622V remains unverified.
- New No-root installations through root SSH hide Developer Mode settings and
  skip renewal status requests. Developer Mode installations retain those controls
  (#577).

## Removal, recovery and diagnostics

- During Root removal, verify the stock Home chain and preserve independently
  owned Home filters (#573). Recovery on the reporting C1s remains unverified.
- Recheck the boot when continuing interrupted Root removal and retain the
  original removal target (#566).
- An explicit standalone Root rollback retry can reopen an expired readiness
  window and relaunch the restored profile (#567).
- For malformed Helper Stop records, require a verified full restart and
  process readback before continuing No-root removal (#578). The original
  failure on the reported OLED55B9PSB remains unconfirmed.
- Distinguish a missing KeyFilters configuration, Helper start failure stages
  and Root recovery interpreter failures in diagnostic reports (#572, #571,
  #570). The underlying reported installation failures remain open.
- Align the console guide with the Root Home naming control (#569).

## Versions

| Component | v1.19.0 | v1.20.0 |
| --- | --- | --- |
| Home FHD/HD | 1.17.0 | 1.18.0 |
| Helper | 0.8.3 | 0.8.3 |
| cytv | 0.19.0 | 0.20.0 |
| Android / versionCode | 0.18.0 / 36 | 0.19.0 / 37 |
| Root / infrastructure | 0.18.0 | 0.19.0 |
| Both edition Updaters | 0.5.11 | 0.5.12 |
| Fresh System / protocol | 1.2.9 / 1 | 1.2.9 / 1 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/568)
and [verification ledger](history/2026-11-12-release-1.20.0-candidate.md)
for artifact verification and device acceptance.
