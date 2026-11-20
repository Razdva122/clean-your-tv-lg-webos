# Issue #133: recovery confirmed and offline compatibility investigation

## Public recovery evidence

The [owner's result](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-7035596176)
confirms removal on OLED55C37LA, firmware 23.20.54, webOS 24 / SDK 9.2.1,
using the Linux x86_64 desktop installer cytv 0.22.0 from v1.25.0 and the
original saved Root SSH connection. The original v1.4.0 / cytv 0.5.0 / Root
0.5.0 installation had stopped during stock-Home provisioning. Remote model
is unknown; Homebrew Channel 0.7.3 was reported at original setup.

The first removal attempt lost SSH without an exit status; the owner observed
an unexpected TV restart and the app disappearing. Its cause is unproven.
After the advised Try again, the standard report records `removed`,
`verified_clean` and `private_cleanup_verified` as true, no error, no pending
operation, and idle recovery with no required action. The owner confirmed LG
Home, arrows, OK, Back and Options, opening Homebrew Channel and intact root.
No additional power restart was requested for that continuation.

This establishes recovery of the partial installation, not successful Root
Home installation on this firmware. CYTV Home activation, emergency Stop,
audio, standby, true AC-off cold boot, OTA and rollback are untested in this
recovered state. No TV was accessed during this maintainer task. Only the
technical facts of the voluntary public reports are reused, without personal
identifiers or raw diagnostics.

## Presentation correction

The completed screen used the generic unknown-stock-controls fallback even
when cleanup was verified. Omit that fallback on a completed removal; retain
actual stock observations and every unknown on incomplete/failed results.
This does not claim physical controls were automatically tested.

The diagnostic exporter also passed the retained removal record through the
deliberately conservative saved-receipt projection. That projection correctly
requires rechecking an old success but contradicted the fresh successful
result in the same report. The export now records verified-clean only with
no pending operation/error, an eligible saved completion and strict current
removed/verified-clean/private-cleanup flags with no restart requested.
Saved records, failed observations and pending work keep their old behavior.
No cleanup effect, permission, persistent schema or release version changes.

The two regressions failed before the fix and passed afterward. The 59 focused
diagnostic/recovery/presentation cases passed. Independent read-only review
found no actionable issues. Website build and verification passed, including
the recovery-only partial catalog entry and regenerated README. Existing user
recovery instructions/localized guides need no change: no action or label was
added. Full installer validation is recorded in the implementation PR.

## Exact-build archive discovery

The [official C3 support page](https://www.lg.com/uk/support/product-support/cs-OLED55C34LA.AEK/)
still lists the 23.20.54 changelog, but its currently offered ZIPs do not include
that version. The [public archive index](https://tv.slada.sk/processed_fw.json)
provides this matching C3 build candidate:

- Archive: `mirror2/LG_DTV/C/C3(Version 23.20.54).zip`, 1,688,841,146 bytes.
- Expected archive SHA-256 from that index:
  `201b26375d1542166009c4e0171b9d5016ce715054e72c2a528abe28689d9e3b`.
- EPK: `lib32-starfish-global-secured-o22n-okapi.pine-2604-23.20.54_prodkey_usb_V3_SECURED.epk`,
  1,696,465,445 bytes; expected SHA-256:
  `8e33807d6e8dd55c07185f100dbe71cd7d6b694fb6605488967ad22231bf2619`.
- Indexed identity: `HE_DTV_W23O_AFABATAA`, firmware 23.20.54.01,
  Rockhopper 9.2.1-2604 (ombre-okapi), build 20241126073045, kernel
  5.4.268-320, Node 16.19.1, Python 3.10.9 and Chromium 108.0.5359.211.

These are expected index values, not a claim that the whole archive has been
downloaded or authenticated. Acquisition was started outside Git. The ZIP's
local entry identifies the expected EPK; the available decompressed prefix
reports SDK/platform 9.2.1 and the matching firmware/OTA identity through
epk2extract revision `a0ccd8a4b4f48d05675a4cddd233f8780ee36767`.
The rootfs superblock identifies a 1,526,590,916-byte LZO SquashFS.

Whole ZIP CRC/hash, complete EPK hash/signature verification and factory-file
inspection remain outstanding. A prefix-only extraction verified available
segment signatures but ended on truncated input; it cannot establish complete
image validity or the presence/absence of a factory service. Vendor files and
raw extraction logs stay outside Git. No vendor daemon has been run.

Acquisition blocker on this pass: the mirror returned HTTP 429 when resuming
one of the two bounded range transfers. Existing partial ranges were preserved
outside Git and transfers stopped; no complete archive hash is claimed.
`unsquashfs -l` cannot read the directory/ID tables from the available prefix.
That is expected for incomplete input, not evidence of a defective LG image.
Resume and authenticate the complete input before interpreting factory files.

## Comparable factory-handler replay

While exact-image acquisition was blocked, reused the complete cached W20H
04.64.00 / webOS 5.6.2 image from the earlier #710 investigation. This is a
different hardware generation and SDK; it can validate a replay method and a
real LG absent-key fallback, not establish C3/9.2.1 behavior.

The [LG archive URL](https://gscs-b2c.lge.com/downloadFile?fileId=D5Fg2suBWGy3YfylwHNNrg)
is recorded by the archive index. The cached ZIP was rehashed as
`5f380e6e4e31e9a4ecd5588c28cf5597c99146b300b7ff208cc3c835953706eb`,
matching the index; the indexed EPK SHA-256 is
`ba03818a33a7fda0a547a2f98b75332a4e8636c9e8fe9bca8c875ee0243ca574`.
No new EPK signature claim is made for this reused extraction.
Extracted `usr/lib/qml/KeyFilters/systemUi.js` hashes to
`c61f1a202c8237eeb9ad51fa49b26f23d21d39af9aa5639a69e5a1c504585e67`.

Executed that unmodified script with Node 23.11.0 `vm`, supplying modeled
ribbon permission, disabled first-use/power-only/disable-Home conditions and
recording application-manager calls. Called `launchHomeApp(773, true)` with
three `settingsService.getLaunchDefaultApp` values:

| Modeled Home setting | Observed factory request |
| --- | --- |
| Absent | `launchDefaultApp(com.webos.app.home, {category: home})` |
| `com.webos.app.home` | `launch(com.webos.app.home, {launchType: homeKey})` |
| `com.webos.app.fullhome` | `launch(com.webos.app.fullhome, {launchType: homeKey})` |

All three assertions passed. These are calls into a modeled application
manager, not real app launches, live Settings Service results or physical key
acceptance. They show why an absent setting cannot by itself be treated as
broken stock Home. The exact C3 handler, its application-manager implementation
and the compositor integration still need the matching complete image.

## Source boundary and next offline checks

The original failure is explained by v1.4.0 `prepare_stock_home`: with an absent
Settings Home override it reads System Profile before recording initialization
intent or submitting a Home write. The earlier offline simulated missing-service
reply reproduced the reported stock-home/service-missing failure without a Home
write. It establishes that code path, not factory service availability.

Current schema-3 compositor admission is capability based and already accepts
well-formed C3 identities; it is not proof of this firmware's support. Before
any new reporter run, inspect the matching image's configd filter-chain defaults,
`KeyFilters/systemUi.js` and its Home handler, Settings defaults, native Home
ELF/manifest, service registration and bootstrap/ActivityManager code. Replay
the actual Home handler with controlled absent/explicit Home settings and the
current CYTV filter. If the vendor binaries need execution, use their own ARM
loader/libraries under network-disabled QEMU as in the TV development workflow.

In particular, do not infer that an absent override means broken stock Home or
seed it just to satisfy an adapter. Current reboot-resume checks require an
independently verified LG destination; generic same-session activation and
restart authorization are separate. Factory files/replay must determine what
the real firmware does before selecting a compatibility change.

The remaining live-only questions are current configd/mount/input admission,
physical Home/emergency behavior and later power-transition acceptance. They
are not requested from the recovered owner now. The original issue stays open
for firmware compatibility; successful removal does not resolve that question.
