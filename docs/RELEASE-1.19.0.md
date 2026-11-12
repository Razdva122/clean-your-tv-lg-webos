# v1.19.0

## Home

- Rename the Root Home screen without changing the name of LG Home (#474).
- Open the TV's native LG Notifications panel from Advanced settings in either
  Home edition (#562).

## Installer and recovery

- Keep installer errors, checks and recovery actions usable on smaller desktop
  displays (#555).
- Include the observed native Home permission mode when Root preflight rejects
  it and use the verified installer payload for the Root doctor Home checks
  (#556, #561).
- Offer confirmed clean removal when a pending legacy No-root installation's
  package status is denied. Require a verified restart before changing packages
  or removing files from that partial installation (#557, #564).
- Retire an exact orphaned CYTV Home filter during explicit Root removal when
  the rest of the chain matches stock (#559).
- Verify a changed Root SSH identity against a separately obtained fingerprint
  while preserving the original pin and pending uninstall for recovery (#563).

## Website and maintenance

- Keep homepage launcher previews large across languages and use English
  recordings for Classic, Liquid Glass and Ribbon (#565).
- Document offline reproduction of firmware-specific behavior (#560).

## Versions

| Component | v1.18.1 | v1.19.0 |
| --- | --- | --- |
| Home FHD/HD | 1.16.1 | 1.17.0 |
| Helper | 0.8.3 | 0.8.3 |
| cytv | 0.18.1 | 0.19.0 |
| Android / versionCode | 0.17.1 / 35 | 0.18.0 / 36 |
| Root / infrastructure | 0.17.1 | 0.18.0 |
| Both edition Updaters | 0.5.10 | 0.5.11 |
| Fresh System / protocol | 1.2.9 / 1 | 1.2.9 / 1 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/558)
for package verification and device acceptance.
