# v1.21.0

- In No-root and Root, open **Home settings → Appearance → Edit tiles** to
  rearrange apps using short OK presses and the arrow keys. Back cancels the
  current move or exits the editor. The Magic Remote hold behavior reported on
  one C2 remains under investigation (#649, #646).
- No-root updates in Developer Mode can proceed when the TV leaves the packaged
  Helper state directory at mode 0777. If setup cannot establish that automatic
  activation is safe, the installer verifies the packages and asks you to choose
  **Start Helper** on the TV when ready (#655, #653).
- On Windows, the installer retries temporarily locked operation files and
  resumes the same removal once the file becomes readable. Persistent access
  failures report a local storage error before recovery connects to the TV
  (#656, #643).

| Component | v1.20.8 | v1.21.0 |
| --- | --- | --- |
| cytv | 0.20.8 | 0.20.9 |
| Android / versionCode | 0.19.8 / 45 | 0.19.9 / 46 |
| Home FHD/HD | 1.18.7 | 1.19.0 |
| Home Helper | 0.8.6 | 0.8.7 |
| Root edition | 0.19.8 | 0.20.0 |
| Both edition Updaters | 0.5.16 | 0.5.17 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/651)
for build and device verification.
