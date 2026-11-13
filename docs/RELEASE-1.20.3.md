# v1.20.3

- No-root setup can finish recovery after both packages have installed, even if
  temporary installation files are no longer accessible (#598, #529).
- No-root removal can resume on the same boot after a transient Helper Stop
  failure once current package and process checks confirm it is safe (#604).
- Root removal resumes from the saved operation, clears private state in the
  dedicated component directories, and runs one full final verification. A
  secondary cleanup failure preserves the original package error. Physical
  confirmation of reinstallation on the reported G5 and C1 is pending
  (#601, #602, #603, #588, #389).
- The desktop installer can run an explicitly confirmed SSH command over a
  saved connection and copy its output and exit status for support
  (#600, #519, #101).

The Home packages include expanded Chinese font coverage for the shared
installer strings.

| Component | v1.20.2 | v1.20.3 |
| --- | --- | --- |
| cytv | 0.20.2 | 0.20.3 |
| Android / versionCode | 0.19.2 / 39 | 0.19.3 / 40 |
| Home FHD/HD | 1.18.1 | 1.18.2 |
| Home Helper | 0.8.4 | 0.8.4 |
| Root / infrastructure | 0.19.2 | 0.19.3 |
| Both edition Updaters | 0.5.13 | 0.5.14 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/597)
for artifact verification and device acceptance.
