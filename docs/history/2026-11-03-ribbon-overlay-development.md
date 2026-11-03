# Ribbon overlay development checks, 2026-11-03

Feature branch: `codex/ribbon-overlay-mode`, PR [#265](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/265), targeting `release/next` after the frozen 1.7.0 cycle. Product/test revision: `2a5c9dcdc427b4ce18b9c045e42887289301faeb`. This is host/source evidence, not a release acceptance record.

## Scope and expected behavior

Root Ribbon opens over positively identified active content and dismisses on Back or a subsequent Home. Startup, unknown context and settings use the opaque presentation. No-root keeps its native fullscreen host. Both demos expose simulated startup and over-application states; all preview images use synthetic browser content.

Root uses an overlay host across themes, so visually opaque themes may also preserve underlying application/audio lifecycle. Signed-package physical acceptance remains required. No new routing writes, preferences, permissions or listener were added. The fixed Root compositor query uses the established root `luna-send` broker, a 1500 ms deadline and a 65536-byte output limit; only a normalized content fact leaves the service.

## Verified host checks

- `scripts/test.sh ui tv preview` passed before the final bounded-query transport correction: TV web/theme compatibility, actual renderer/controller/demo integration, native safety regressions, 926 Root Python tests, 132 system-updater Python tests and preview checks.
- After the transport correction: presentation context, service handlers, startup payload and audio recovery tests passed; eight Root build tests and TV web compatibility passed again.
- Generated Root package closure/HTTPS/Python binding checks passed on current Node. Exact Node 0.12.2 was unavailable locally and is not claimed as tested here.
- Fourteen TV developer staging/safety tests passed after updating the DOM event stub. The initial Ubuntu CI failure was an incomplete test DOM (`addEventListener` absent), not a device result.
- Independent reviews found and verified correction of visibility/relaunch ordering. A 500 ms activation coalescing bound remains a physical acceptance assumption. A separate scoped review found no actionable issue in the bounded Root transport correction.

The full browser regression and latest GitHub checks are recorded in the PR once complete. Earlier completed browser groups covered both editions, theme switching/isolation, layouts, Inputs, focus/motion, render budget and looping Ribbon. The old selection test's pink accent expectation was updated to the authored warm Ribbon accent.

## Remaining acceptance

No signed product build from this branch was installed or accepted on a TV. Model, firmware/webOS, remote, installer platform and device results are untested for this implementation. Video/audio, HDMI, no-content startup, standby, cold boot, input ownership, emergency behavior and updater/rollback remain pending on an exact selected candidate. Earlier private prototype observations are neither published here nor counted as release evidence.
