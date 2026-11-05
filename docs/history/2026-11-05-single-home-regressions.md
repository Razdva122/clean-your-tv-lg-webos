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

## Initial full candidate failures

Full run 42074859425 at c4827c43 exposed a Homebrew-only packaging limit: the
complete embedded Root IPK is approximately 28 MiB, above the ordinary 16 MiB
member cap. Commit f46a7a30 permits up to 64 MiB only for the fixed Root payload
path and versioned identity, retaining ordinary and aggregate limits. Eighteen
Homebrew tests, a real nested Root IPK byte comparison and independent review
passed. The Homebrew Installer remains unapproved and unpublished.

The same run exposed stale No-root packaging assertions requiring the superseded
OVERLAY contract; Root preview had the same stale assertions. These tests now
verify opaque CARD metadata without transient relaunch handling, retain package
identity/grant/protocol checks, and verify canonical Home no longer loads or
requests the old overlay context. Focused real package and preview tests passed. Root Settings browser coverage also
retained an obsolete positive overlay-context request assertion; it now requires
zero such requests. The entire browser scenario passed locally, retaining explicit
Off/enable and delayed/stale LG-launch checks.
The initial full run is failed evidence, not the selected final candidate.

Homebrew run 42076103862 exposed a second large member: the same Root IPK in
`payload/baseline/cache/<sha256>`. The first fix covered only the direct component.
A complete local build reproduced the failure and enumerated all large members:
normalized Python runtime (51,462,118 bytes), Root IPK (28,288,532 bytes), and its
baseline cache copy (28,288,532 bytes). The bounded exception now also covers the
exact baseline cache path with a 64-character lowercase hexadecimal name.
Nineteen Homebrew Python tests and independent review passed. The complete offline
installer (113,991,816 bytes), manifest generation and repeat manifest verification
passed locally. This development installer is not approved for publication or
physical installation. A separate Homebrew CI verification follows; the active
main candidate run is retained as evidence for its original source.

## Ribbon geometry regression

Run 42076103862 passed the full browser job and all platform builds, but the
runtime preview section stopped in `ribbon-reference-ui.cjs`: the shortcut group
was 68 pixels high at x=28/y=984 rather than the intended continuous 180-pixel lane
at x=0/y=900. The trusted renderer gated this appearance on `layout.presentation`
and lost it when the built-in theme correctly stopped requesting overlay mode.
The renderer now preserves the continuous lane for the built-in Ribbon identity
without changing CARD lifecycle. Existing external theme geometry remains scoped
to its previous opt-in behavior; the browser fixture now uses an actual external
identity for that check. Home advances to 1.9.4 and Root/infrastructure to 0.9.3;
preliminary 1.9.3 observations above remain tied to their original packages.

The separate Homebrew run 42077320700 completed successfully after the baseline
cache correction. It is focused evidence, not the full frozen candidate.

After the geometry correction, the complete `scripts/test.sh preview` group passed
locally, including both CARD editions, compiled Root media routing, Ribbon geometry
and editing, showcase, bridge and preview isolation checks. Theme runtime unit and
README/version checks passed. Independent review found no actionable issues. A new
full candidate is required for this changed Home/Root source; no failed earlier run
is selected as release evidence.
