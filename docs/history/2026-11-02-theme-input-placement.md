# Theme-owned Inputs and Alpine migration — 2026-11-02

Unreleased source/host work, stacked on held Inputs #239 and Liquid Glass #241.
The maintainer requested theme-owned placement and a smaller built-in theme set.
Neither underlying PR nor this follow-up is accepted into `release/next` by this
record. No TV was contacted or changed; no physical compatibility is claimed.

## Result

- Optional `layout.inputs` selects `menu` or `shelf`; omission/Classic uses the
  existing header menu. The shelf requires `dock-grid`. The source compiler
  infers paired `input-placement-v1`; unknown values, unsupported layouts and
  mismatched capability declarations reject before application. Placement writes
  no user preference. The unpublished global shelf-visibility switch was removed.
- Themes style existing shelf/tile/status/preview parts and states through the
  ordinary typed CSS compiler. No new CSS syntax, arbitrary positioning or video
  control is exposed. Geometry, launch, hitboxes and media lifecycle stay trusted.
  The optional live-preview preference remains available only for shelf themes.
- Liquid Glass declares the shelf and occupies Alpine's former built-in position.
  Classic and Ribbon remain. All Alpine package bytes leave the TV payload.
- Alpine 1.4.4 becomes a downloadable Showcase package under the main repository's
  identity, with source `4bcc0975a6951118c26b2cb7dff665d6d1c9ea5f` and distribution
  `323c7bb3` (the registry contains the full immutable commit). Rules, all eight
  assets and both license documents match the previous 1.4.4 appearance. The old
  external 1.4.2 listing remains archived. Remote bytes/hash verification passes.
- A saved `builtin:alpine` choice follows the existing visible Classic recovery
  path; it neither downloads a theme nor substitutes Liquid Glass. Unrelated
  preferences remain. Ordinary Showcase installation is available afterward.
- Input media now yields to visible owned dialogs, including Helper relaunches
  and theme trials, and resumes only an eligible preserved shelf selection.

## Verification

Focused regressions cover strict capability pairing, all four simultaneous
modern-icon/motion/date/input capabilities, default menu, atomic rejection,
no placement writes, actual compiled shelf CSS, and theme/reset transitions while
video is active. Both editions pass at 720p and 1080p with simulated TV APIs.
Overlay, input-shelf, packaged Liquid Glass, motion and rendering-cost browser
suites pass in both editions. Theme units, compatibility and the UI test group
pass. Independent core and migration reviews have no remaining actionable finding.

Website builds verify all 72 localized routes; Astro check, complete website
browser checks and real development-server smoke pass. The website uses Liquid
Glass in its cards, copy and offline built-in theme checks. All twelve guides
and the author CSS reference describe unreleased behavior separately from history.

These are source/browser/host results. Actual HDMI signal/CEC, controls, sound,
standby/cold boot, OTA/rollback, full locale/device compatibility and exact signed
packages are untested here. Versions, candidate freeze, complete candidate build,
signing and release publication remain separate. Publish a matching author-toolkit
runtime before offering this new capability to external theme authors.
