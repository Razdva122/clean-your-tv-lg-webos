# v1.20.7

- On older LG TVs, No-root removal can use LG's installed-package catalog
  when the SDK directory layout prevents direct cleanup. The installer verifies
  removal through the catalog before cleaning up known project files (#634, #626).
- When Developer Mode removal gets an incomplete LG Home launch reply, the
  installer can continue if an authenticated check confirms LG Home is in the
  foreground (#636, #472).
- No-root Helper recovers after a software restart on affected TVs. The Home
  Helper panel can read status after Developer Mode resets directory permissions,
  and **Start Helper** resumes Home control without reopening the panel. Explicit
  Stop and triple Home still return control to LG Home (#637, #505).
- **Review recovery options** can check a pending No-root removal without
  starting cancellation. If the local recovery capsule is missing but the
  original saved receipt matches the TV plan, confirmed removal can continue.
  The installer blocks removal when it cannot verify ownership (#638, #635).

| Component | v1.20.6 | v1.20.7 |
| --- | --- | --- |
| cytv | 0.20.6 | 0.20.7 |
| Android / versionCode | 0.19.6 / 43 | 0.19.7 / 44 |
| Home FHD/HD | 1.18.5 | 1.18.6 |
| Home Helper | 0.8.4 | 0.8.5 |
| Root edition | 0.19.6 | 0.19.7 |
| Independent updater | 0.5.16 | 0.5.16 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/633)
for build and device verification.
