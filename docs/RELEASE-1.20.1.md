# v1.20.1

- Ordinary Developer Mode removal now verifies cleanup in one operation when
  Home Helper stops and the TV confirms the expected state. Unfinished setup
  and unverified process state still require the existing recovery checks
  (#580, #472).
- A Root activation retry refused during preflight preserves the original
  recovery receipt. The separately confirmed return to LG Home remains
  available when its checks pass (#583, #334).
- Root diagnostics now distinguish a missing default-app setting from a
  missing System Profile service. Both still block incompatible setup
  (#584, #315).

The reporting TVs still need device verification for the original cases.

| Component | v1.20.0 | v1.20.1 |
| --- | --- | --- |
| cytv | 0.20.0 | 0.20.1 |
| Android / versionCode | 0.19.0 / 37 | 0.19.1 / 38 |
| Home FHD/HD | 1.18.0 | 1.18.0 |
| Home Helper | 0.8.3 | 0.8.3 |
| Root / infrastructure | 0.19.0 | 0.19.0 |
| Both edition Updaters | 0.5.12 | 0.5.12 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/585)
for artifact verification and device acceptance.
