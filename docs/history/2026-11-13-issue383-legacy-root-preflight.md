# LG 43UK6450PLC legacy Root preflight

[Issue #383](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/383)
reports a Windows CYTV 0.11.0 Root installation on LG 43UK6450PLC, firmware
05.50.70, webOS/SDK 4.4.0, ARMv7. The remote was unspecified.

## Factory evidence

[LG's 43UK6450PLC support page](https://www.lg.com/ru/support/product/lg-43UK6450PLC.ADGZ)
lists both this model and the 43UK6200PLA from
[#592](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/592) for the
[same 05.50.70 archive](https://gscs-b2c.lge.com/downloadFile?fileId=TIX0GNxVoCbplTZFyXvA).
The download metadata and first 64 KiB matched the local copy used for #592.
`unzip -t` passed. SHA-256 of the local ZIP:

```text
3bd867fc7306b65280777edd0b8fd65d965add5260ce5c4e06de8d92a3a7fc69
```

The EPK reports platform `HE_DTV_W18A_AFADABAA` and build `05.50.70.01`.
The existing epk2extract-based extraction log records successful RSA
verification of the header and package table. The factory root filesystem
contains a 32-bit ARM Node executable and the Surface Manager base KeyFilters
chain, including `systemUi.js / handleSystemKeys`. It lacks
`/usr/bin/python3` and `/usr/bin/com.webos.app.home`. The installer's
native Home file check returned exit 42 against the factory-derived layout.

The factory ARM Node returned `v0.12.2` in QEMU 7.2.22 using its own loader and
libraries, in a network-disabled container with the firmware files mounted
read-only. The ordinary Root version expression exited 1 and the exact Beta
version expression exited 0. Both vendor bootstrap scripts were readable and
the Beta probe's `require` calls for `webos-service`, `palmbus` and
`pmloglib` succeeded in an unprivileged run. This checked module loading.
The live service launcher and Luna permissions remain device checks.

## Installer replay

- CYTV 0.11.0 (`v1.11.0`, `407b21e3`) and CYTV 0.20.1
  (`release/next`, `37fbb4dc`) both reproduced `root-requirements` in
  `inspect-installation`. The fixture supplied the observed Python and Node
  results and the successful SSH-side checks from the report. Home settings,
  Home profiles and inventory remained unchecked.
- [#388](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/388), shipped in
  v1.12.0, offers No-root over the existing authenticated root SSH connection
  and, with the exact Node and the embedded Beta payload, offers Root Beta
  with a second confirmation. Cancel is the default. The model replay now
  checks that a noninteractive install with `--yes` exports the model, Node
  and failed checks before staging packages or starting SSAP pairing.
- A separate Home preflight replay modeled a missing System Profile service
  and a readable `configd` reply using the actual factory KeyFilters chain.
  On `37fbb4dc` this reaches `root-home-interfaces / native-home-unavailable`.
  [#575](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/575) handles
  the branch where KeyFilters are absent and the LG ribbon responds.
  [#592](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/592)
  (`d784276`) offers explicit No-root for this other branch, with readable
  KeyFilters and missing native Home. Its simulated install passed the
  ordinary No-root checks and submitted Home Helper and Home.

The original report never reached Home preflight, so the live System Profile
and KeyFilters responses on the 43UK6450PLC are still unknown. Installation of
the exact package, physical Home and emergency controls, audio, power,
recovery and removal remain unverified on that TV.
