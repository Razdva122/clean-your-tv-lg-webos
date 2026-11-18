# Root Beta recovery in place on the B9

[Issue #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160)
reports an OLED65B9PLA with firmware 05.50.00, webOS 4.10.2-31 and SDK 4.10.0.
The original desktop installer was CYTV 0.20.9 from v1.21.0 (Root 0.20.0).
The remote model is unknown. The Root Beta package opened manually, while the
device deployment remained at `provision-finalize-starting`. The explicit Beta
status showed no local pending receipt. CYTV 0.21.0 stopped at the existing
installation check before it could run the v1.22.0 recovery service.

The separate recovery action uses `cytv recover --edition root --root-variant
node012-beta` on the saved Root SSH connection. The installer checks the
original deploy reservation, recorded timeout, installed package, compositor
selection, LS2 snapshot and pending manifest. After confirmation it updates
the private runner and its manifest digest, finishes recovery provisioning and
requires a successful status reply with verified integrity. The action leaves
the installed package and Home routing in place. A retry checks every other
manifest hash and can complete a deploy lease after the final stage was written.

## Offline evidence

Used the official W19H image `05.50.00.01-HE_DTV_W19H_AFADABAA` extracted
after ZIP integrity and EPK signature verification. ZIP SHA-256
`59ef18516657a7a058d4a8cf86dab14020eb25d40f794e328506bbc999a1b976`.
The Linux x64 v1.21.0 installer matched the published SHA256SUMS. The replay
verified 48 entries of its embedded 1080p Root Beta compositor bundle and used
the 148 installed package files from its IPK.

In isolated QEMU 7.2.22, the B9's 32-bit ARM Node 0.12.2, original service
bootstrap, palmbus, webos-service, LS2 hub and luna-send ran the existing
package's service. A fixture supplied the saved deployment and LS2 records,
the Python child result and stock Home observations. A test Activity Manager
accepted the per-request activity call without replying. The original runner
exited with code 0 without serving status. The recovery action changed its
private runner and pending proof. The same packaged JS service then served
the status requests before and after publication of the readiness proof.
The resulting stage was `installed-recovery-only`. Installed package hashes,
LS2 registration bytes and the original failure record matched before and after.

The replay used a lab LS2 policy, modeled the separately registered persistent
recovery activity and startup hook, and did not boot a retail B9. The device
owner's matching failure cause, real Python and compositor readback, startup
hook, persistent activity, recovery after real reboot, and Home activation
remain to be verified on hardware. No TV was contacted or changed.

The [final-status envelope investigation](2026-11-18-issue160-final-status-envelope.md)
corrects the simplified Python child fixture used above. The earlier replay
did not validate the actual nested CLI status envelope.
