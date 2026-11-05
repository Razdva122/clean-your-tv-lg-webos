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

## Sharded candidate validation

At the maintainer's explicit request, CI-only PR #332 was integrated at 230ef888f.
The runtime matrix partitions the large Root, setup and installer Python suites
into four isolated shards per OS; other runtime checks execute on shard 1. Required
Linux/macOS summaries still require the complete runtime matrix, and full candidates
retain browser, ARM Python and full-release gates without success-cache reuse.
The prior unsharded candidate run 42080674432 is superseded; it is not the selected
release build. Product scope and component versions are unchanged by sharding.

## Selected full build and signed Root delivery

Full build [42081316264, attempt 3](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42081316264)
at `40f6f84ab9002cfdfe51dbf34e675e1adbdf7364` completed successfully, including
all eight runtime shards, browser, ARM Python, platform builds, Homebrew and final
summaries. Earlier attempts were cancelled while one macOS shard waited for a
runner; only that shard and dependent checks were rerun. Completed artifacts were
retained by GitHub and verified through the normal candidate admission.

Normal Root-only signing [42088467852, attempt 1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42088467852)
completed without publishing a release. Signed artifact SHA-256:
`576302bae9c2d7f7326162d989108c018ab5e0dfc3071db81c23f30c79b49bbc`.
Local verification checked the trusted public key, signature, exact build/attempt,
source provenance, three component identities, package sizes and hashes:

- Root 0.9.3: `5b0a4cb494248db05b1543bedd59e22feaec53f7c311d38de0cd7c92ff88aa21`.
- Root Updater 0.4.4: `21b58f0f6ba7b4ebef930ad93768575f5199af6120870523c2387cb5c26bfa11`.
- Root infrastructure 0.9.3: `8f6352b33599d17938f1fd70a255301f5c1b19eb913e84083db707dbafcba9be`.

C3 pre-install readback confirmed Helper stopped, Root and guardian off, recovery
integrity verified, and stock LG SAM/default/idle destinations. Final package/device
acceptance is in progress; no physical test result is implied by signing.

## Focused final Root device acceptance

The maintainer requested a short run limited to physical Home latency, background
playback/persistence, return to LG, and loading personal images/videos. Device and
host remain the maintainer-owned C3 / firmware 43.21.71 / SDK 11.2.0 / Magic Remote
and macOS recorded above. Exact signed packages from build 42081316264:3 were used.
System Updater 1.1.2 was retained; no role, receipt, key or permission was replaced.

The ordinary signed System worker completed Root 0.9.3, Root Updater 0.4.4 and
infrastructure 0.9.3, with all three install results successful, complete Home
resume and no recorded worker error. An initial UI profile export was attempted
before readiness; export from the ready UI succeeded before installation began.
Current UI-captured settings were preserved. A direct LS2 status request was
rejected; protected transaction data was read without modifying it to confirm the
worker outcome. Package installation is recorded separately from physical tests.

| Focused check | Expected | Observed |
| --- | --- | --- |
| Physical Home from HDMI3/PS5 | Promptly open our Home | Maintainer: appeared immediately, with Root enabled through its normal Settings switch and Helper stopped |
| Ribbon own video wallpaper | Visible moving background | Maintainer confirmed motion; native video advanced from 103.17 to 108.20 seconds at 3840×2160, unpaused and without an error |
| Earlier 120-second disappearance | Home remains open | Same ready visible CARD observed at 176.6 seconds without disappearance |
| Explicit Home Off / LG exit | Restore LG and routing baseline | Maintainer confirmed LG Home; Root and guardian off, recovery verified, stock SAM/default/idle LG destinations and Helper stopped |
| Receive personal image and video | Start PIN receiver, receive and apply fixtures | **Failed before transfer:** receiver did not open; a real Root UI method call returned `errorCode: -1`, `Denied method call "themeReceiverStart" for category "/"` |

The upload failure is a release blocker for claiming this retained Root setup can
load personal wallpapers/videos. It does not establish a failure in decoding
received media: no file transfer began. The transfer attempt used ordinary UI
controls; no existing personal wallpaper was present or overwritten. Temporary
receiver/pending controls were cancelled and the original theme source restored.
No permissions were changed to force the test through. The LS2 denial needs a
supported installation/update diagnosis; its exact role provenance is not yet
established by this run.

Sound, standby, cold boot, actual normal OTA/rollback and published-Home/new-Helper
compatibility were not tested in this short run. This record is partial acceptance,
not approval to publish the candidate. Final TV state is LG Home with routing off.
