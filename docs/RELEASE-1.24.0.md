# v1.24.0

- Root and No-root Home can sort apps by successful launches from the app grid.
  The setting is opt-in. The dock and the saved manual order stay in place.
  Editing, hiding tiles and undo still use the manual order (#700).
- Developer Mode auto-renewal remains opt-in. Its panel and the installer
  explain how to check the official Developer Mode timer and show the current
  renewal status (#699).
- Root removal can resume when the private Python runtime contains generated
  bytecode for its recorded sources. Unrecognized files still block cleanup
  (#689, #389).
- Root compositor recovery keeps a verified active route during the same boot.
  The installer can use its bundled Restore for an eligible retained activation
  and preserve the original failure record (#690, #693, #615, #418).
- Root Beta reports where repair stops and can inspect an interrupted deployment
  without staging support. The legacy Node 0.12 compositor lease uses the
  registration expected by the affected webOS LS2 release (#695, #696, #160,
  #615).
- Root package verification accepts firmware-specific ownership of known shared
  SDK directories when the expected package content matches. For the current
  compositor, stock Home verification can also recognize read-only firmware
  paths with a different owner (#697, #101).
- An eligible retained No-root Helper removal can resume after the installer
  verifies a new boot. The original Helper startup report is still open
  (#698, #152).
- No-root Debloat distinguishes an explicit TV rejection from other failures.
  Home button diagnostics can continue one capture after a temporary SSH
  interruption and save partial evidence when reconnect fails (#691, #694,
  #687, #686).

| Component | v1.23.0 | v1.24.0 |
| --- | --- | --- |
| cytv | 0.21.1 | 0.21.2 |
| Android / versionCode | 0.20.1 / 48 | 0.20.2 / 49 |
| Home FHD/HD | 1.20.1 | 1.20.2 |
| Home Helper | 0.9.0 | 0.9.0 |
| Root edition | 0.21.1 | 0.21.2 |
| Both edition Updaters | 0.6.1 | 0.6.2 |
| System Updater IPK | 1.2.11 | 1.2.11 |
| System Updater engine | 1.2.11 | 1.2.12 |

See the [release record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/688)
for build and device verification.
