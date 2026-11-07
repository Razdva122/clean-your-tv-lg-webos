# Experimental compositor Home: source and local verification, 2026-11-07

Related issue: #364. This is a development record, not a device installation or
release acceptance report. No TV was contacted or changed, no reporter action was
requested, and no private Reddit conversation or diagnostic was published.

## Delivered source scope

Capability-based admission for Qt SDK 6–9, without a model allowlist, reuses the
existing `c1-native-gate` / `compositor-keyfilter-v1` package and wire identifiers.
Schema3 requires stock native Home, ARM32/input compatibility, advertised Home
and Back, an explicitly absent System Profile and a protected vendor Qt filter
chain. Foreign Home state, mounts and Home input bindings refuse admission.

Schema3 writes configd only with `volatile:true`, requires exact readback and
retains interrupted transaction evidence. Native stop precedes controller
retirement and owned-filter removal. Previous-boot PIDs are never followed.
Changed Home identity permits owned-filter release but retains recovering state
without claiming full stock proof. Lost volatile filters cancel lifecycle return
and retire the control lease rather than being automatically reinstalled.

Schemas1/2 retain their C1-only selection and recovery semantics. Recovery manifest
verification now requires the actual selected guardian and the compositor filter
hash, rather than looking for the legacy mount helper in a compositor package.
Ordinary OTA and automatic rearm remain unavailable. No network endpoint, LS2
permission, daemon restart, Home/checkpoint mount or input injection was added.

## Verification and actual outcomes

- `npm ci`: passed.
- `scripts/test.sh tv-runtime installer setup` initially reached the complete
  Root suite: 1,241 tests, 3 skips, 2 environment errors because `fontTools` was
  missing. The preceding helper/service/native checks passed. This initial run
  is **not** recorded as a green full suite.
- Installed the declared build/font and installer dependencies in a temporary
  Python environment. Repeated the failed Root groups `test_update_lab.py`
  (3 tests) and `test_update_setup.py` (5 tests): passed.
- `scripts/test.sh installer setup` in that environment: setup 257 tests passed;
  installer 979 tests completed with 92 optional skips and one environment error
  because the declared Zig compiler was missing. Its Homebrew runtime/UI checks
  passed. Installed pinned `ziglang==0.14.1` and repeated the failing static-ARM
  support build test: passed.
- Final current-source checks: 184 Python tests passed, comprising static ARM
  installer support (1), all `test_c1*.py` (79), real native guardian process tests
  (40), recovery manifest verification (4), bounded transport (2), and installer
  admission/package/proof/localization checks (58).
- `test-c1-lease.cjs` and `test-c1-filter.cjs`: passed, including schema3 authority,
  schema2 refusal, malformed/expired leases, paired releases and unrelated keys.
- Remaining update/System Updater JS checks and 132 Python System Updater tests:
  passed. Updater JS syntax and shared user-data byte comparison passed.
- Actual static ARM32 guardian cross-compilation with Zig 0.14.1 and an offline
  Root compositor bundle build passed. The local unsigned test package uses the
  builder's default `0.0.1` version; it is not a published or install-accepted
  release. No release version or candidate inventory was changed.
- Independent source review found and corrected cold-import and recovery-helper
  selection gaps, plus filter-chain race and previous-boot PID handling. Final
  review found no remaining concrete blockers. `git diff --check` passed.

Focused checks were repeated after code changes. Successful unchanged test units
were retained; no second unchanged full Root run was performed merely to replace
the initial environment-failure record.

## Remaining limits

Physical Home/Back/triple-Home, application return, pointer behavior, audio/volume,
HDMI/CEC, standby, true cold boot, removal and rollback on a target Qt TV are
untested. Device model, firmware, remote and installer platform acceptance are
therefore unestablished. These local results do not resolve the original hardware
compatibility report. Support remains experimental; no new reporter testing is
requested by this record.
