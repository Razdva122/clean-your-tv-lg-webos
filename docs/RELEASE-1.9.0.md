# v1.9.0 — C1 routing, recovery and storage feedback

[Release downloads](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.9.0) · [Exact package hashes and acceptance](history/2026-11-06-root-wake-key-release.md#signed-candidate-c3-observations).

The maintainer accepted the scoped C3 and original-signer Android emulator results
below. Historical evidence retains its original model/version/artifact scope.

## Changes

- Root personal receiver/media APIs are prepared before LS2 registration, with a protected private-worker grant for five media-cache methods (#341/#337). Source/host checks pass; retained-device image/video transfer acceptance remains unverified. Browser demo video resumes after theme selection restores iframe focus (#345).

- Root startup allows a bounded 750 ms interval for an initially held key to be
  released before enabling the emergency observer (#90). Initial historical events
  are discarded; fresh Home input cancels pending activation. Held/error cases
  still restore LG Home under the
  unchanged watchdog. This addresses the transient held-key branch, not a proven
  device-wide standby fix. Scoped signed-package C3 standby/cold-start and retained rollback checks passed; see the acceptance record below.
- Root activation and restoration preserve the complete AOD/vendor category map,
  changing only Home (#323, #282). This is a host-tested preservation correction;
  original C4 recovery and exact-package B4/C4 Settings/SAM/cache acceptance remain
  unverified. Existing historical observations are not acceptance of these bytes.
- Eligible **fresh C1 Beta** installations use a private compositor Home filter,
  lifecycle return and independent native leases (#331, #298). They do not change
  checkpoint permissions or use CRIU/bind mounts. Existing schema1 installations
  retain their original guardian/recovery and need verified removal before a fresh
  installation; no in-place backend migration or ordinary OTA is provided.
  Legacy schema1 preflight/stock-handoff corrections remain (#327/#330).
  See [C1 routing and limits](development/C1-NATIVE-GATE.md).
- Installation, downloaded themes and personal wallpaper/video flows show required,
  available and missing storage, including temporary copies and reserve (#329).
  Unknown values remain unknown. Device free space, app quota, the 64 MiB theme
  cache and video limits are separate; nothing is automatically deleted.
- Failed Root activation can offer a separate default-No recovery confirmation
  after proving disabled/restored routing, stock Home, bound installed files,
  updater/baseline and completed product state (#338, #334). The operation archives
  its original receipt, revalidates and activates without reinstalling packages.
  Uncertain/failsafe states remain blocked. Health refusal diagnostics do not grant
  authority or prevent recovery if logging fails. The original device cause and
  successful reporter recovery remain unconfirmed.
- Partial-Helper recovery errors now retain capability-specific guidance (#324).
  This does not implement recovery of #307 or bypass vendor operation/cleanup
  authority. Source installer emergency-stop/restart wording is corrected (#326);
  original #96 standby/control failures remain unresolved.
- Catalogue additions: **Atmosphere 1.0.0** (#325/#314) and **Crăciun la Brașov
  1.1.0** (#336/#279). Crăciun's 3840×2160 wallpaper is an AI-generated image
  upscaled from 1672×941, not native4K detail. It is image-only; no Christmas video
  or animation is included. Existing attribution/licenses are retained.
- CI retention/caching and shard allocation maintenance (#335) keeps complete
  candidate validation and required summaries. A generated-bundle HTTP regression
  prevents a missing cache import in the Root receiver; Ribbon editing tests wait
  for observed edit mode without weakening their assertions or changing UI timing.

Ribbon remains a theme of the **single permanent full-screen CARD Home** in both
editions, with its own background and normal application switching. HDMI/video is
not displayed beneath its cards. Alpine1.5.0 and its genuine Bachalpsee4K image
and 4K/1080p videos remain in the published catalogue; Liquid Glass remains built in.

## Versions and packaging

| Component | Published1.8.2 | Release1.9.0 |
| --- | --- | --- |
| Home (FHD/HD) | 1.9.4 | 1.10.0 |
| Home Helper | 0.7.4 | 0.7.4 |
| cytv | 0.9.2 | 0.10.0 |
| Android / versionCode | 0.8.2 /22 | 0.9.0 /23 |
| Root / infrastructure | 0.9.3 | 0.10.0 |
| Both edition Updaters | 0.4.4 | 0.4.5 |
| System Updater target / protocol | 1.2.1 /1 | 1.2.2 /1 |

All platform installers, signed Android and TV payloads were rebuilt and verified
in selected full build42176689817:1. Helper0.7.4 raw/canonical bytes match the
authenticated1.8.2 baseline, retaining its existing compatibility approval.
System1.2.2 adds experimental-state exclusions; retained installed1.1.2 remains
pinned. This release adds no general supervisor replacement path. Homebrew
Installer promotion remains disabled without independent hardware/human evidence.

## Tested scope and known limitations

On OLED55C3RLA / firmware43.21.71 / SDK11.2.0, the supported signed update from
1.8.2, actual component versions/runtime hashes, ordinary Home health, Home/video/
audio/volume, standby routing, physical AC-off cold start, triple-Home emergency Off
and exact retained rollback passed. After rollback, the owner confirmed Home,
audio/volume and preserved settings; final state is LG Home on1.8.2 with Root off.
Android0.9.0/code23 passed exact original-certificate upgrade from published code22
on an isolated API35 ARM64 emulator, four-file synthetic retention, real Store
refusal/no-replay and native OperationChecks. This is not physical phone-to-TV or
universal TV compatibility evidence.

- [#347](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/347): Settings can remain at Changing Home control with a disabled switch after wake even while Home routing is active. Close and reopen Settings to refresh it. Deferred to next release.
- [#348](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/348): old updater packages and installer staging can accumulate. This release does not automatically prune them. Preserve current/rollback/pending records; the observed low-space update aborted safely before component changes and succeeded after owner-authorized stale-package cleanup. The future retention MR is not included.
- [#337](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/337): receiver/media source fixes are included, but retained Root image/video receive, Apply, playback and reload remain unverified. Built-in media is a separate path.
- C1 Beta remains fresh-install only and experimental, with no ordinary OTA or in-place schema1 migration. C1 physical lease/emergency/startup/audio and B4/C4 Home/AOD/Settings/SAM/cache acceptance remain unverified.
- Original #96/#282/#298/#307/#334 reports remain open according to unresolved outcomes. Guidance, guard/diagnostic improvements and package delivery do not prove those devices recovered.
- Physical Android phones, the oldest Android/WebView floor, real phone-to-TV interruption/recovery and broader No-root device acceptance remain untested. No automatic uninstall, ownership change or journal cleanup is authorized by a recovery message.

[Full dated observations, attempted resolutions and limits](history/2026-11-06-root-wake-key-release.md#final-cold-start-retained-rollback-and-android-upgrade) · [Wallpaper source checks](history/2026-11-06-root-wallpaper-ls2.md).
