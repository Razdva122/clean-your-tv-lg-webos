# Preliminary No-root C3 acceptance — 2026-11-05

This is authorized maintainer QA on a maintainer-owned TV. It records observed
preliminary packages, not final release acceptance or universal compatibility.

| Field | Observed value |
| --- | --- |
| TV | LG OLED55C3RLA |
| Firmware / SDK | 43.21.71 / 11.2.0; marketing webOS version not independently recorded |
| Remote | Magic Remote with pointer; exact remote model unknown |
| Host | macOS, Python 3.14.2; macOS version not recorded |
| Edition and transport | No-root runtime on an already rooted C3, using existing Root SSH while Root routing remained off |
| Preliminary source | `8e6ca65aacce56acfbf2efa05b8222e033ee5001` |
| Installed test components | Home 1.9.1, Helper 0.7.1 |
| Retained components | Root 0.9.0, Root Updater 0.4.3, immutable System Updater 1.1.2 |

## Actual tests and outcomes

- Both packages reached installed terminals; versions and installed public-file
  hashes matched the prepared packages. An initial close request was rejected;
  read-only reconciliation established Home was absent before completing only
  its not-yet-attempted update. Root recovery remained intact.
- Manual Start from the actual Home panel worked. Restart after emergency Stop
  reused the saved pairing without another pairing prompt. Arrows and the Magic
  Remote pointer worked. Back returned to the video app and HDMI 3 with PS5.
- Expected: physical Home presents transparent Ribbon over active content.
  Actual: opening took approximately five seconds and the opaque wallpaper
  obscured both app video and PS5. App audio continued. HDMI audio was **not
  checked** and is not counted as passing.
- Expected: selected video wallpaper plays when decoder ownership is safe.
  Actual: Auto remained a static image with unknown decoder context. The safety
  fallback was retained; no decoder guard was disabled to force playback.
- Triple Home reached the relay and stopped the controller with a persistent
  emergency latch. The owned Home window could remain visible; one subsequent
  ordinary Home displayed LG. One earlier attempt had no immediate visible
  result, so clean first-attempt recovery is not claimed.
- Ordinary Installer Stop over the selected Root SSH path returned a refusal
  while the controller remained running. A later observation found startup
  disabled. The precise partial-operation cause was not established; guarded
  fallback was not forced. The first AC test therefore lacked an enabled-startup
  precondition and is not a clean startup-failure result.
- Remote power off/on returned Home after approximately 5–10 seconds without a
  system restart. After explicit manual Start and verification of current enabled
  startup state, a repeated 30-second AC disconnect changed the composite boot
  identity and reset uptime. Helper started automatically, reached READY and Home
  appeared after approximately 30 seconds. This is delayed successful startup.

At the end of this series the original appearance was restored, Helper was
stopped, Root remained off, stock Home routes were verified and recovery was
intact. No raw profiles, screenshots, inventories or device logs are included.

## Fixes and remaining gates

The follow-up changes prepare validated appearance before optional video media
and wait for bounded terminal UI teardown after emergency/Stop. Host regressions
and independent reviews cover these changes; corrected packages have **not** been
accepted on the TV. Deferred video remains unusable until its full integrity and
media checks pass. Unknown native context still does not prove a free decoder.

Physical watchdog fault handling, exact new Helper/published-baseline rollback
compatibility, pristine unrooted Developer Mode installation and final coherent
signed-artifact acceptance remain untested. The ordinary Stop refusal and safe
manual video-wallpaper capability remain open. Shared UI changes require fresh
affected Root acceptance. Release publication and release-PR readiness stay held.
