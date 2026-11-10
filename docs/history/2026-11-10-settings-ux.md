# Root and No-root Settings UX follow-up, 2026-11-10

## Scope

The requested audit reproduced spatial-navigation and error-recovery gaps in
the real launcher browser preview. This follow-up keeps the existing category
structure and service contracts, with no new persistent preference, permission,
network endpoint or component version.

- Column-picker arrows follow the visible three-column grid and stop at its
  horizontal/top boundaries. Compact Root Home rows use spatial navigation.
- Returning from categories restores the last available control for this Settings
  session. First entry targets the selected language or primary weather toggle.
- Unknown No-root Home status keeps a disabled, explicitly unavailable action and
  a retry button. It does not expose an invented `aria-checked` value. Successful
  retry restores the verified switch and usable focus.
- HDMI audio status checks announce loading separately from unavailable/error
  results and suppress duplicate checks while a response is pending.
- Installed theme cards wrap within the reading area. A category overflow arrow
  makes lower entries discoverable without covering their labels.
- Appearance separates columns from applications. Shared labels are consistent
  across editions, including the result-oriented Home-button switch name.
- Wallpaper uploads precede the library and quality controls. Parameters without
  an available wallpaper stay hidden. Personal wallpaper deletion uses the
  existing confirmation dialog, with Cancel preserving the saved image.
- Developer Mode presents session status before the explanations, keeps history
  below the primary actions, and retains a visible Back footer. Beta limitations
  and manual timer instructions remain explicit.

The initial audit used an older checkout. Compact weather preview clipping is
already fixed in the current integration base; this change verifies that behavior
without replacing the existing fix. It does not claim to fix any existing
device-specific Home, Helper, standby or installation issue.

## Verification

Host platform: macOS, local Chrome/Playwright preview with synthetic LS2 and
blocked external HTTP requests in the focused browser cases. Both editions were
reviewed at 1920×1080 and 1280×720. The localized Settings matrix covers 13
languages. Screenshots and local logs remain under `build/tests/settings-ux/` and
`build/settings-ux-*.log`; they are not device installation reports.

The new browser regression first reproduced the missing focus memory, incorrect
column directions, unselected language entry, secondary weather entry target,
horizontal theme overflow, missing Home retry and misleading audio-loading state.
The personal-wallpaper test first failed on deletion without confirmation. The
corrected behaviors pass the focused regressions. Review also corrected first-row
Up movement and unavailable-switch accessibility semantics.

Checks:

- `scripts/test.sh ui`
- `node tests/settings-ui.cjs`, including `tests/settings-ux-ui.cjs`
- `PREVIEW_URL=http://127.0.0.1:8876 node root-edition/ui/test-settings-browser.cjs`
- `PYTHON=.venv-cytv/bin/python node tests/themes/personal-wallpaper-ui.cjs`
- `PYTHON=.venv-cytv/bin/python node tests/themes/selection-ui.cjs`
- `npm run lint:compat`, `npm run format:check`
- `.venv-cytv/bin/python scripts/tv_web_build.py --input launcher --output build/settings-ux-compiled`
- All `tests/updates/*.cjs` and `tests/system_updates/*.cjs` checks.

The initial GitHub run exposed an older update-badge DOM double without
`removeAttribute` and assertions requiring a hidden Home switch. The harness now
models attribute removal and asserts that unavailable status exposes no boolean
choice. The final [Tests run](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42772444277)
passed all Linux/macOS runtime shards, browser and HEIC browser checks on
`6b13cd80d483faebc4c12d52e483774b7399b09f`. Integration policy passed before
[PR #483](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/483) merged into
`release/next` as `f421b8ee39d3a22a2a932088d2643b970239fdf0`.

All 13 practical localized guides were updated with current navigation, retry
and wallpaper-deletion instructions. Existing inbound anchors were retained.

## Acceptance boundary

No physical TV was operated. Model, firmware/webOS and remote are untested;
installer execution was not part of this task. Real Home routing, HDMI sound,
standby, cold boot, OTA installation and rollback remain untested here. This is
focused development evidence, not a frozen candidate acceptance record. The
release coordinator must build/pin the final candidate and complete the applicable
release gates before publication.
