# Ribbon presentation design

Approved scope (2026-11-03): Root native overlay, shared Ribbon redesign and browser demo in both editions. No-root remains a fullscreen app. Target release/next; do not merge into the frozen release.

## Behavior
Keep existing Root IDs, updater, routing and emergency ownership. Root uses an overlay window; themes remain visually fullscreen unless their validated layout opts into `presentation: overlay` with `overlay-presentation-v1`. Ribbon opts in. Opaque fallback is the default until rendering and a fresh read-only compositor observation confirm underlying content. Empty/unknown context and power-on activation show wallpaper. Settings, theme trials and recovery are opaque. Back dismisses only unobstructed Ribbon navigation. A visible overlay's ordinary repeated Home dismisses; reopening hidden Home refreshes context instead. Late queries/launch callbacks cannot change a newer presentation. Successful content launch dismisses the existing overlay; failure preserves it.

The Root manifest change also means an opaque non-Ribbon Home preserves underlying app/audio lifecycle. This is intentional Root window behavior and must be disclosed and separately accepted; visual opacity is not equivalent to card lifecycle. No-root package metadata/helper stays unchanged.

## Boundaries
One shared presentation state controller, with normalized content facts via the existing Root service status payload. The context branch is read-only, bounded and independent of recovery busy/locks. No new listener, ACG, persistent preference or route write. Theme authors supply bounded data, never executable behavior. Keep the native startup observer as owner of remembered inputs; explicitly avoid interpreting the primary app beneath a Root overlay as a source-selection request.

## Visual direction
Keep Ribbon's skew and bottom alignment. Use quiet dark neutral card surfaces, native logos at consistent scale, a white focus outline/lift, readable labels, restrained warm accent and a bottom-local scrim. The same design must work on the supplied wallpaper and over bright moving content. Do not darken the entire video. No new font/library.

## Demo and documentation
Expose startup/over-application states and Home/Back in the browser demo, clearly labeled simulated. No-root overlay preview is a simulation of Root behavior, not a compatibility claim. Update bundled thumbnails, README Ribbon preview and relevant English/localized controls guidance.

## Verification
Tests cover absent/unknown context, startup, hidden/visible relaunch, stale callbacks, modal opacity, Back precedence, launch success/failure, No-root fallback and startup observer preservation. Browser tests exercise actual Ribbon, bright backgrounds, both demo editions, transparency and theme switching. Use normal compatibility build, affected UI/TV/preview checks and code review. Historical prototype observations are private; do not publish owner/device details without exact report consent. Product package cold boot, standby, emergency, OTA and rollback acceptance remain pending a signed candidate; do not claim those from a browser or the prototype.
