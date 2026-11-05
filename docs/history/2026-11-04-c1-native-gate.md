# Common-installer C1 Beta — 2026-11-04

Unreleased implementation for [#298](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298).
The maintainer requested a native backend with independent recovery, then
confirmed automatic selection in the common installer and integration into the
next release candidate. No separate beta installer or user backend flag ships.
The current [backend contract](../development/C1-NATIVE-GATE.md) describes its
commands and limitations.

## Result and boundaries

The common Root flow selects native C1 Beta only after the exact missing-service
reply, verified C1/webOS 6 identity and actual ARM32 Home/userspace evidence.
Positive profile interfaces keep the existing backend. Denial, timeout and
malformed replies do not trigger native fallback. Both graphics variants are
embedded in the common payload; normal Root bundle inventories exclude the C1
adapter and executable.

The native guardian owns temporary mounts, bounded input protection, inverse
journaling and durable stop. It does not depend on Python or the UI to restore
stock Home. The updated reporter probe was reviewed: `preload:"full"`, delayed
stock exit and SAM idle relaunch have corresponding handling/tests. Activation
verifies the exact attempt before launch, avoids a competing foreground launch
and retains uncertain host/device receipts.

C1 Beta accepts fresh installations only. Normal updater/OTA paths reject it;
the installer does not deploy Root Updater on this path. Open LG Home and long
Back leave routing off. Shutdown/power-loss ambiguity conservatively leaves
stock Home and requires explicit enable. Cross-process-namespace propagation is
refused; owned same-namespace aliases are supported. Full removal refuses before
effects if another project component is present, rather than claiming to remove
unchecked components.

## Host evidence

Implementation revision before this record: `862ebfb5`.

- 32 native tests passed, including ASan/UBSan parser sequences, lease/input
  failures, interrupted mount publication, exact owned aliases and foreign
  overlays. Independent review reproduced a stopped-but-live guardian race;
  corrected retirement now refuses success and retains its journal. A resumed
  old attempt cannot overwrite a newer token's recovery authority.
- 749 common-installer tests passed, with 27 environment/platform skips. This
  includes automatic selection, real bundle personalization, activation and
  receipt recovery, native-only removal, Qt paths and all installer languages.
- 132 system-updater tests passed. Ordinary Root/System update entry points,
  supplied baseline/resume and orphan backend evidence retain their guards.
- The broad Root run checked 953 tests: three sandbox-sensitive cases initially
  failed. Their affected groups subsequently passed with required process,
  local-socket and file-mode permissions: lifecycle 12, permission repair 6 and
  private service 9. The native suite was checked separately.
- All Root UI tests, including the actual launcher/Settings browser tests, passed
  against a temporary local preview. Generated Root Node closure/TLS/binding
  checks passed on host Node 23.11.0; that local check did not run exact Node 8
  or legacy Node 0.12.2.
- The actual common payload build passed integrity/release-version checks with
  305 files, both ordinary Root variants and both C1 variants. The real helper
  is a stripped, static ARM EABI5 executable, 84,904 bytes, SHA256
  `fcee0e3d147aa3c3893e9e3dac391bb487a2910d1af025be6770c10902a6daa6`.

Reproduce using repository build dependencies and the existing pinned Zig:

```sh
python -m unittest discover -s root-edition/tests -p test_native_gate.py
python -m unittest discover -s tests/cytv
python -m unittest discover -s tests/system_updates
python scripts/build-cytv.py --payload-only
```

Technical/developer references, all thirteen TV guides and installer translations
were updated. Component versions remain the published baseline until candidate
freeze. This host build is not the selected, signed or accepted release build.

## Physical acceptance remains open

No TV was contacted or changed by this implementation. Target model/firmware
evidence in #298 belongs to the reporter's temporary probes, not this binary.
Installer host: macOS. Actual target model, firmware/webOS, remote and installed
component versions for our build are untested. Home/Back/emergency/key-up, SAM
roles, real bind propagation/CRIU/jails, sound/media/HDMI, standby, AC-off boot,
firmware changes, update rejection and removal still require exact-build C1
acceptance. Neither successful cross-compilation nor a package install would
establish those results.

## Final integration evidence

PR [#300](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/300) merged into
`release/next` as `6b676981b752837522a47ff8ee3867369c60088b`. Its final tested
source is `be64989e8baf21186955afeb071c40c6799afe98`.

The combined-source follow-up caught two integration problems. Preview CI used
cached Node 22.23.3 despite Astro's declared >=22.23.4 requirement; its job now
uses the declared patch. A separate presentation module initially expanded the
immutable supervisor's private inventory; it is now bundled into existing
`service.js`, preserving all eight historical private paths. Neither legacy
fixture nor protocol guard was weakened. The isolated actual-IPK/private-service
checks (10), immutable-supervisor acceptance checks (7), final removal regressions
and 79 normal operations checks passed. The complete final local Root suite
passed **994 tests**. The corrected common payload also built and verified both
normal and C1 graphics variants with 305 files.

Final-source [Linux/macOS runtime, browser, ARM Python and required summaries](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41828530872),
[frozen Windows/macOS Intel installer checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41828530992),
[preview build and browser checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41828530871)
and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41828525964)
all passed. Stable Pages deployment and full-release jobs were intentionally
unselected. These are implementation/combined-source checks, not a versioned,
signed full-candidate build or physical C1 acceptance. Release preparation must
select versions and run the complete frozen-candidate workflow separately.
