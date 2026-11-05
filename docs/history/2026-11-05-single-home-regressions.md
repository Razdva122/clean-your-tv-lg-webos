# Single Home regression QA — 2026-11-05

## Scope and provenance

Maintainer-authorized QA on a maintainer-owned OLED55C3RLA, firmware 43.21.71,
webOS SDK 11.2.0, Magic Remote; installer host macOS. This is preliminary No-root
acceptance, not final release acceptance or universal compatibility evidence.
Published baseline is 1.7.1. Candidate target is 1.8.2.

The maintainer chose Ribbon as an ordinary theme of the single Home, with its own
background. External video/HDMI under Ribbon and a second application are outside
this release. Reviewed direct follow-up commits are 3c1ea4b6, 5ef5d14c, 81973179,
95cb3578, 1737ce17 and 0b10daaf; direct release/next integration was explicitly
requested instead of a second feature-PR full test run.

## Observations and resolutions

The earlier full-application OVERLAY disappeared approximately 120 seconds after
becoming visible. The exact platform lifecycle reason was not captured. Restoring
ordinary CARD window semantics removed that observed disappearance in this run.
Theme and personal-background restoration now run concurrently with both readiness
barriers retained. Known packaged UHD media is selected before cache acquisition.

Preliminary Home 1.9.3 / Helper 0.7.3 showed a moving Ribbon background and retained
the same visible navigation for more than four minutes. Native playback advanced
at 3840×2160 with increasing decoded frames and no observed error; this does not
measure physical panel pixel presentation. Switching to HDMI released Home media;
returning resumed it. The maintainer reported immediate Home opening from PS5.

Helper 0.7.3 emergency stopped routing but did not return to LG because it required
a successful cross-application close. Helper 0.7.4 retains bounded cleanup and
known-launch drain, then launches LG without requiring the resident CARD to close.
The maintainer confirmed triple Home returned to LG. Final readback showed Helper
stopped with its emergency latch retained, Home hidden with media released, Root
routing and guardian off, and recovery available. Pairing metadata was preserved.
Installed System Updater 1.1.2 was unchanged. Older Root 0.9.1 was not accepted as
the new Root candidate.

Generic preliminary Home SHA-256:
`e82e3af9da93c56f7ae7e27ac526d780166d19d49633232b9c1ba0d4f27a60f5`.
Helper 0.7.4 preliminary raw IPK SHA-256:
`5c27a000b35ccbfeb0689dbd80ff8f2d0f4f70094794f64b101cadb91733501f`.
Personalized package data and raw device diagnostics remain private.

## Verification and remaining gates

Focused unit, compiled UI, readiness, media lifecycle, preview and emergency
regressions passed, with independent source review. The full browser invocation
initially failed an obsolete corrupt-stream fallback expectation; the corrected
stream fixture and remaining Root route fixture passed separately. This is not
reported as a successful single full-suite invocation.

One full frozen candidate workflow is required. Final artifact selection, signed
Root package/device acceptance, exact Helper compatibility with published Home,
sound, standby, cold boot, normal OTA and rollback remain untested for this pair.
A rooted QA transport does not establish a fresh unrooted installation. No public
release delivery or original reporter issue resolution is claimed by this record.
