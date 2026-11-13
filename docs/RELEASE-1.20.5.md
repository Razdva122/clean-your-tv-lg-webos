# v1.20.5

- Interactive desktop and command-line removal can restore saved LG Debloat
  settings. The installer shows current and saved values before confirmation,
  defaults to skipping restoration, and keeps records when it cannot verify a
  restored setting (#617, #392).
- Desktop and Android removal guide users through recovery when a result cannot
  be verified. The desktop installer and CLI also offer standalone LG Debloat
  maintenance without installing or removing packages (#618).
- Root and No-root Home can finish starting when optional Weather initialization
  fails. Required readiness checks still apply (#618).
- No-root setup over Root SSH can read effective user and group IDs on older LG
  Node.js runtimes without the corresponding Node APIs (#620, #587).

- Home settings show a preview for each clock format and distinguish the saved
  selection from remote focus (#621, #608).
- No-root removal waits for Clean Your TV processes to stop, then continues the
  same removal. If a confirmed process remains, the installer keeps the removal
  record and reports the timeout (#622, #529).

| Component | v1.20.4 | v1.20.5 |
| --- | --- | --- |
| cytv | 0.20.4 | 0.20.5 |
| Android / versionCode | 0.19.4 / 41 | 0.19.5 / 42 |
| Home FHD/HD | 1.18.3 | 1.18.4 |
| Home Helper | 0.8.4 | 0.8.4 |
| Root edition | 0.19.4 | 0.19.5 |
| Independent updater | 0.5.15 | 0.5.15 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/619)
for build verification and physical TV acceptance.
