# v1.20.8

- Verified Root removal can continue when the LG screensaver appears over
  stock LG Home and the installer can still verify that Root routing stopped
  (#640, #615).
- No-root removal reports can identify which project app is still blocked
  during final cleanup. The installer still requires a clean verification
  before it reports removal complete (#642, #152).
- A pending No-root removal over root SSH can continue without a SAM Home
  entry when both system profiles select LG Home and the installer verifies
  that no Root Edition state remains (#644, #643).
- Diagnostic reports say which recovery step failed after an unsuccessful
  Root activation, so the report can distinguish a failed connection or
  status check from an unverified restore (#645, #418).
- A pending No-root update in Developer Mode can resume when the Helper has
  an outdated pairing key and the TV accepts the saved key for the same
  operation. A prior Stop remains in effect (#648, #647).

| Component | v1.20.7 | v1.20.8 |
| --- | --- | --- |
| cytv | 0.20.7 | 0.20.8 |
| Android / versionCode | 0.19.7 / 44 | 0.19.8 / 45 |
| Home FHD/HD | 1.18.6 | 1.18.7 |
| Home Helper | 0.8.5 | 0.8.6 |
| Root edition | 0.19.7 | 0.19.8 |
| Independent updater | 0.5.16 | 0.5.16 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/641)
for build and device verification.
