# Wallpaper UI source verification — 2026-11-06

Implementation: [PR #358](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/358).
This is source/browser verification, not signed-package or physical-device acceptance.

## Behavior

Settings retain the independent video wallpaper while theme styles are isolated.
A theme trial temporarily uses the candidate's own wallpaper without persisting a
personal-wallpaper source change. Cancel, timeout and interrupted-trial recovery
retain the saved source; Keep uses the existing transactional confirmation path.
Reselecting the accepted theme preserves its independent wallpaper selection.

For a theme with enabled HDMI input previews, selected/active UHD wallpaper shows
the temporary static 1080p fallback warning. The action changes the existing input
preview preference and keeps remote focus on an operable control. Themes without
previews, disabled previews and non-UHD selection do not show this warning. The UI
and all 13 guides include translations; candidate guidance remains unpublished.

The Black Hole poster is a 3840x2160 JPEG derived from the first decoded RGB frame
of the shipped video, converted explicitly to full-range BT.601 JPEG 4:4:4. Ribbon
1.3.1 records the source and packaging hashes. The H264 variants and fragmented
stream bytes are unchanged. App-colour ambient glow is suppressed for selected
wallpapers, including poster preparation and static fallback. Classic without a
wallpaper retains its original colour-following glow.

## Host validation

Combined source after updating from `release/next`:
`ef5e8cfb88fefb69e37ba3914ab00aeef12c3b0e`.

Final-head CI [42205482928](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42205482928) passed all eight Linux/macOS runtime shards, browser and ARM Python; preview and integration policy also passed. Merge `a4f981ee7` retains the checked tree.

Passed locally with the declared build dependencies on macOS:

- `npm run test:themes`: complete theme runtime, source, ownership, cache,
  startup/readiness, policy, transport, receiver and wallpaper checks.
- `node tests/wallpaper-settings-ui.cjs`: both real edition bootstraps with
  simulated native services; continuous settings playback, preview warning and
  shared preference, theme trial cancel/timeout/Keep/reload and Classic recovery.
- `node tests/themes/wallpaper-ui.cjs`: actual H264 decoding, full-viewport silent
  looping, ambient suppression for poster/video/suspension/static image and
  restoration of Classic glow after wallpaper removal.
- `node scripts/build-builtin-theme.cjs themes/ribbon --check` and
  `node scripts/build-tv-theme-catalog.cjs --check`: reproducible package,
  registry/catalog digests and exact source provenance.

Implementation-stage checks also covered both editions' personal/built-in media,
full theme selection/cache/recovery, Classic rendering budget, first presented
frames, Root packaged stream selection, 14 dev-tool cases and compiled dev-UI
storage/native-bridge isolation. Independent scoped and combined-source reviews
found no actionable issue. The final integration preserves the simplified guides
and their legacy anchors from #356 and the Root health startup fix from #357.

## Delivery limits

Shared Home and Root UI packages and installer bundles need rebuilding with final
component versions at candidate freeze. No overall release version, final build or
acceptance pin is selected by this implementation. Helper bytes are unchanged.

There is no new persistent setting, permission or network endpoint. Trial state
and the active-wallpaper CSS flag are volatile. HDMI previews retain the existing
wallpaper decoder release/reacquisition; simultaneous physical video output is not
promised. The normal dev entrypoint retains its same-origin-only network policy.

Final signed-package controls, sound, standby, cold boot, public-feed update and
rollback acceptance remain pending. Browser/native-service simulation and a
compiled dev UI cannot establish those results or universal TV compatibility.
