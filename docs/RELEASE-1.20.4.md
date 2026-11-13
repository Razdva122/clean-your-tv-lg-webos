# v1.20.4

- Root and No-root Home have a separate clock-format setting. Automatic follows
  the TV locale, and 12-hour and 24-hour formats can be selected explicitly
  (#609, #608).
- Removal waits for current package operations and project processes. No-root
  removal checks exact project service registrations, identifies access failures
  in diagnostics, and reports temporary archives left on the TV when the removal
  itself succeeds (#607, #613, #529, #152).
- No-root recovery checks the existing package staging before offering to resume
  an unfinished package installation. Configuration-only recovery can still
  proceed without the temporary archives (#614, #529).
- Root setup can offer to restore LG Home when it verifies a removable file
  mount over the stock executable. On C1, setup can restore active GlassHouse
  routing before installation and verify a previous cleanup before reinstalling
  (#611, #613, #519, #389).
- No-root Debloat reports pairing, write and readback failures separately. On
  the affected LG 55UK7500PSA firmware, results explain when the TV rejects
  a write due to its firmware settings policy (#612, #610).
- Browser demos and theme previews feature PlxNative (#605).

| Component | v1.20.3 | v1.20.4 |
| --- | --- | --- |
| cytv | 0.20.3 | 0.20.4 |
| Android / versionCode | 0.19.3 / 40 | 0.19.4 / 41 |
| Home FHD/HD | 1.18.2 | 1.18.3 |
| Home Helper | 0.8.4 | 0.8.4 |
| Root / infrastructure | 0.19.3 | 0.19.4 |
| Both edition Updaters | 0.5.14 | 0.5.15 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/606)
for build verification and physical TV acceptance.
