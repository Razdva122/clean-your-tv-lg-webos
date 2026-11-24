# v1.28.0

- On No-root, **Stay on HDMI or Live TV when the TV wakes** can keep HDMI, Live TV or another
  external input visible after standby. The switch is off by default (#809).
- No-root Home can recover its app catalog during startup. The installer now
  preserves restart evidence and explains what still prevents removal (#803, #805).
- Root can start a fresh installation after verified removal by a previous
  installer and can stage packages on verified internal storage on TVs that
  use ramfs for `/tmp`. Removal checks available RAM before staging its
  support files on those TVs (#806, #811, #819).
- Root's C1 backend handles stale controller identity and absent-Root close
  replies, reconnects after a short broker interruption, removes its own
  persistent filter override when restoring Home, and can restore stock routing
  after boot without opening Home over HDMI (#807, #812, #816, #817, #819).
- Opening Root Settings with OK keeps that press from changing Home control
  when the remote sends duplicate keydown events (#824).
- The theme showcase adds Neon ’86 and Vice (#808, #815).

| Component | v1.27.0 | v1.28.0 |
| --- | --- | --- |
| cytv installer | 0.24.1 | 0.24.2 |
| Home FHD/HD | 1.20.7 | 1.21.0 |
| Home Helper | 0.9.4 | 0.10.0 |
| Root edition | 0.24.1 | 0.24.2 |
| Both edition Updaters | 0.6.6 | 0.6.7 |
| Android installer / versionCode | 0.23.1 / 54 | 0.23.2 / 55 |

Checks on C1 firmware 03.53.45 and on TVs with ramfs still need matching
owner evidence. The [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/804)
tracks tested models and package verification.
