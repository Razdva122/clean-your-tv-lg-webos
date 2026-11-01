# Retro API 1 integration review — 2026-11-01

The maintainer accepted Retro 1.0.0 in its current API 1 form for the unfrozen
release candidate. Related issue: #69; submission PR: #215; candidate: #210.
This is candidate/browser review, not public delivery or physical-TV acceptance.

## Identity and source

- Theme ID: `github:xandymelo/clean-your-tv-lg-retro-theme:retro`.
- Author source: `d7aa64515f867167de862c46a67fa7fa8bf39f82`.
- Distribution: `bf6f647888dd305e317e7d594bf29bac70c0b7a7`.
- Descriptor SHA-256: `e03a9455f59067d4c79da719e6b2113615f31b7790e66585d5fcea97db12f2c6`.

The submitted distribution SHA was a typo naming a nonexistent commit and
returned HTTP 404. Only the registry URL was corrected; descriptor, rules,
preview, license and credits bytes are unchanged. The complete remote-byte
validator passed after correction. Curated order appends Retro after Minimal;
generated TV catalogue, preview/notice files and inventory are synchronized.

## Verification

Reviewed against integration base `510cb35bd00e044fbabd45f3202e2244942e5df2`.
`npm ci --ignore-scripts`, registry/security/remote tests, `scripts/test.sh preview`,
`node scripts/check-theme-submissions.cjs --remote`, catalogue freshness and diff
whitespace passed. The inline selector regression includes Retro in both editions
with external HTTPS blocked and checks that app order survives theme selection.

A local HTTP preview of the actual exported Home 1.6.1 runtime used the validated
Retro envelope, synthetic reference apps, a hidden Browser library entry and a
simulated HDMI input. Existing `tests/themes/browser.cjs` states were exercised
and captured in both editions: dock, grid, focus, reorder, Add app, library,
Inputs, standard Settings and confirmation. All 18 captures completed without
page errors. Home, library, Inputs and Settings captures were visually inspected.
Independent source review found no actionable issue; independent remote fetches
were unavailable in that reviewer environment, so remote provenance uses the
successful maintainer validator rather than an invented second result.

No TV was contacted. TV model, firmware/webOS, physical remote and installer
platform are not applicable to this browser-only run. Device installation,
physical controls/emergency, sound, standby, cold boot, OTA and rollback remain
untested. Browser screenshots contain synthetic data only and are retained as
local build artifacts.

## Scope and documentation

Current colors, square cards, hard shadows and yellow/magenta focus are accepted.
Press Start 2P/local fonts, steps/blinking effects and custom date positioning
remain outside this version. Invite the author to open a toolkit issue for any
missing capability; evaluate feasibility separately without promising delivery.

No runtime permission, endpoint, persistent state, component version or release
version changes. Existing Home/Root catalogue and embedding installer rebuild
scope carries this data at freeze. Reviewed the contribution/registry guidance;
ordinary setup/controls and all twelve localized guide boundaries are unchanged.
Do not add standalone web Showcase output; the current preview uses its inline
theme switcher. Original #69 requirements not delivered by this adaptation remain
follow-up rather than a claim of full original-design/device compatibility.
