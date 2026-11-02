# Optional date placement, 2026-11-02

Partial #69 follow-up, based on release/next da748e26. The only new option is
`layout.datePlacement` (`inline` or `below-clock`), paired with
`date-placement-v1`, restricted to dock-grid. The compiler infers the capability;
policy rejects invalid values, unpaired capability and unsupported layouts.
Trusted runtime CSS wraps the date and hides its divider. Existing stylesheet
suspension, replacement and reset own its lifecycle. Existing theme defaults
and distributed Retro 1.0.0 bytes remain unchanged.

Verified locally: npm ci; npm run test:themes; npm run lint:compat;
node tests/themes/date-placement-ui.cjs. Browser fixtures cover Root and No-root
at 1280x720 and 1920x1080, date geometry, focus, suspension/resume and reset.
Regression checks cover compiler inference/default preservation, strict values,
capability pairing and atomic invalid-candidate rejection.

No device was used: TV model, firmware, webOS, remote, standby/cold boot, OTA,
rollback and full twelve-locale device rendering are untested. Browser fixtures
are not physical acceptance. No new controls, translations, permissions,
endpoints, persistent state, assets or licenses are introduced.

The date option is separate from #241's Classic motion. Coordinator integration
must union optional fields and capability names/counts in theme policy/contract
and retain both compiler inference paths. This task does not merge #239/#241.
#69 remains partial; no local-font infrastructure is added here.
