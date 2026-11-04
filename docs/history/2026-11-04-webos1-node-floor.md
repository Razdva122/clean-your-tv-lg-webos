# webOS 1.x No-root Node floor — 2026-11-04

## Reports, primary sources and limits

Related issues: [#283](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/283)
and [#284](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/284).
The first author has already resolved pairing; the current blocker is Node.js.

- #283: LG 32LB650V-ZN, firmware 05.05.90 / webOS 1.4.0, Windows installer,
  No-root; actual installer/component versions and remote model unknown.
- #284: LG 49UB8500-UA, firmware 05.06.10 / SDK 1.4.0, macOS ARM64 cytv 0.8.1,
  No-root. SSH, ARM32, pairing and inventory pass; helper-node fails before package
  verification/launch. Pending is null. Remote model unknown.
- Neither report measures the actual TV Node version. Do not claim that a host
  test establishes the installed version or physical compatibility on either TV.

LG's [JS service runtime table](https://webostv.developer.lge.com/develop/guides/js-service-basics#supported-nodejs-version)
lists Node 0.10.15 for webOS 1.x and 0.10.25 for 2.x. This supports a specific
explanation for both reports: the old installer rejected the documented 1.x
runtime. It is still an inference about those two physical TVs until confirmed.
LG's [web-engine table](https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine#web-engine)
separately identifies WebKit 537.41 for packaged webOS 1.x apps; passing Node
checks does not establish launcher rendering, native ABI or remote controls.

## Exact runtime and package evidence

Official [Node 0.10.15 checksums](https://nodejs.org/dist/v0.10.15/SHASUMS256.txt):

| Archive | SHA-256 |
| --- | --- |
| node-v0.10.15-darwin-x64.tar.gz | `f4ea534e6ca6326a8bf823b6c44ae50f5d968c105a18c6372a8bde2d50518489` |
| node-v0.10.15-linux-x64.tar.gz | `0b5191748a91b1c49947fef6b143f3e5e5633c9381a31aaa467e7c80efafb6e9` |

The downloaded Darwin archive matched the official SHA and executed as v0.10.15
on the maintainer's computer. No runtime was copied to a TV.

`NODE010=/path/to/verified-0.10.15/bin/node node tests/helper-compat.cjs`
passed with unchanged compiled app/service sources: controller startup/errors,
service status/listApps, polyfills, WSS registration/subscription, fragmented UTF-8,
ping/pong/close, invalid frame limits and sanitized paired input status. The
compiled watchdog recovery/stop regression also passed on current host Node.

The unchanged published Helper 0.6.22 from v1.7.1 matched its release SHA256SUMS:
`0e8477113fd8afc57b5f3bfc7271a3b7de99dcce2fb2516d7e386eff06ec00cf`.
Its actual app/service JS and JSON were extracted as test data, then exercised by
`tests/helper-runtime.js` under exact 0.10.15 with temporary local TLS fixtures.
The same runtime assertions passed. An initial fixture under a wheel-group
parent was correctly rejected by shared-state ownership checks; moving the
fixture into the user's normal temporary directory fixed the precondition,
without changing product code or weakening permissions.

No ARM relay, vendor LS2 module, packaged web engine or physical input device was
executed by this host test. Existing published Helper bytes remain unchanged.

## Correction and regression

Both source install.sh and the shared desktop/console/Android installer rejected
0.10.15 before installation because their minimum was 0.10.25. Existing Helper
compilation already targets Node 0.10 syntax and needs no product-byte change.
Lower only No-root installer admission to 0.10.15, synchronize checklist/error
translations and retain Root's separate Node 8+ requirement.

Regression tests failed on 0.10.15 in both entry points before the correction.
Afterward the shared gate accepts 0.10.15/0.10.24 and newer; 0.10.14/0.8 remain
blocked before a durable receipt/upload. The shell installer covers the new
minimum with CLI banners and continues rejecting malformed or older output.
No pairing, input ownership, emergency, watchdog or package verification gate
is removed. No TV runtime installation, permission or endpoint is added.

CI and direct-TV safety validation now pin exact Linux 0.10.15 as NODE010, retain
0.10.25 as NODE01025 and retain 0.12.2 as NODE012. Runtime/package dependency tests
exercise all supplied runtimes. Source and published-Helper JS evidence supports
this Node gate correction, not a general webOS 1.x compatibility claim.

## Delivery, documentation and remaining acceptance

Published v1.7.1 installers still enforce 0.10.25. Rebuild shared installers,
Android and source distribution at candidate freeze; no Helper/Root TV package,
component version, selected build or release acceptance is changed here.
Exact published Helper JS evidence supports leaving that package unchanged for
this host-only correction. Final candidate package/input verification remains
required; do not silently switch a pinned Helper baseline.

The source full installer does not offer a Helper-free first-install mode with
Home-button replacement. A standalone Home IPK/historical Home-only updater does
not supply Helper interception and does not fix an unverified old web engine.
Do not suggest bypassing the gate or replacing the system Node as a workaround.

Both authors still need to confirm the actual TV Node version through their
already working SSH connection; no reinstall, reboot or runtime change is needed
for that read. Physical installation, Home routing, arrows/OK/Back, emergency,
audio, standby, cold boot, OTA and rollback remain untested for these models.
Any later agent-published owner installation result requires that owner's
approval of its redacted text and destination.

Reviewed/updated documentation: compatibility requirements, TV build contract,
CONTRIBUTING, this record/history index and all twelve maintained localized guides.
Historical release evidence retains its original 0.10.25 scope. The separate Czech
TV UI supplement has no affected installer text. Final checks and integration are
recorded below; no TV was contacted during source work.

## Local verification and review

`NODE010=/path/to/verified-0.10.15/bin/node PATH="$PWD/.venv/bin:$PATH" bash scripts/test.sh tv installer setup android`
completed with exit 0 on macOS. This includes Helper runtime v0.10.15, TV/browser
compatibility, Root (924 tests), system updates (132), setup (224), installer
payload/continuation groups (8/4/5), cytv (671, 40 expected desktop/PySide skips)
and Android (35). The Linux-only real multi-UID case was skipped locally and
remains covered by Linux CI. These are host checks, not physical acceptance.

An independent read-only review found one stale negative test fixture (0.10.24
had become accepted). It was corrected to 0.10.14; the focused two Node tests and
subsequent complete affected run passed. Re-review found no remaining findings.
`git diff --check` passed. No public release or device acceptance is implied.
