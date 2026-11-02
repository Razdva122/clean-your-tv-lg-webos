# Retro decoration capability, 2026-11-02

Partial follow-up to #69, based on release/next da748e26. Existing Retro 1.0.0
source, catalogue pins and package bytes are unchanged.

Policy previously rejected date placement and stepped easing. Add the paired,
optional `retro-decoration-v1` capability for dock-grid only: datePlacement,
heroCursor and steppedTransitions. Trusted CSS owns wrapping and cursor keyframes.
Only existing bounded visual transition properties accept steps(1..8,end).
No input, helper, permission, endpoint, persistent-state or asset/license changes.
No arbitrary author CSS, at-rules or pseudo-elements are admitted.

Verified locally: npm ci; npm run test:themes; npm run lint:compat;
node tests/themes/retro-options-ui.cjs. Browser fixtures exercise both editions
at 1280x720 and 1920x1080, reduced motion, suspension/resume/reset and focus.
Policy/compiler/runtime regressions cover invalid fields, bounds, property scope,
missing capability, atomic rejection and prefixed-only WebKit CSS emission.
A regression failed before implementation (api-unsupported capability).
A review found missing prefixed keyframes; fixed with a regression assertion.

No physical device was used. TV model, firmware, webOS and remote: untested.
Font loading, CJK fallback, old-engine actual rendering/memory, full 12-locale
layout acceptance, standby/cold boot, OTA and rollback are untested. Browser
preview is not device acceptance. Initial sandbox receiver failure was resolved
by allowing loopback test fixtures; preview required declared build dependencies
in a temporary Python environment.

Local font transport/validation/loading/lifetime and the toolkit companion remain
unimplemented. This PR does not complete #69 and must not close it. Existing
released Retro is not silently opted into these new fields.

Integration with #239/#241 must union optional fields/capabilities and preserve
classic-motion reserved-transition guards. This branch neither merges nor changes
those PRs. No candidate version, signing or release publication is performed.
