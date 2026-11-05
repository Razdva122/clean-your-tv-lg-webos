# v1.9.0 — C1 routing, recovery and storage feedback

**Unpublished candidate.** Stable downloads remain on [v1.8.2](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.8.2).
This cycle is preparing artifacts for owner-supervised acceptance. No new TV
installation, controls, audio, power or rollback result is claimed.

[Build, preflight evidence and remaining acceptance](history/2026-11-06-release-1.9.0-candidate.md).

## Changes

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

| Component | Published1.8.2 | Candidate1.9.0 |
| --- | --- | --- |
| Home (FHD/HD) | 1.9.4 | 1.10.0 |
| Home Helper | 0.7.4 | 0.7.4 |
| cytv | 0.9.2 | 0.10.0 |
| Android / versionCode | 0.8.2 /22 | 0.9.0 /23 |
| Root / infrastructure | 0.9.3 | 0.10.0 |
| Both edition Updaters | 0.4.4 | 0.4.5 |
| System Updater target / protocol | 1.2.1 /1 | 1.2.2 /1 |

Home/receiver/catalogue, Root/runtime/infrastructure, updaters and shared
computer/Android payloads need rebuilding. Helper has no source change; exact
package equivalence must be verified before full dispatch. Its already accepted
compatibility scenario is reusable only for identical bytes and preconditions.
System1.2.2 adds experimental-state exclusions; retained installed1.1.2 remains
pinned. This candidate adds no general supervisor replacement path. Homebrew
Installer promotion remains disabled without its independent hardware/human record.

## Known limits and acceptance

The retained C3 Root personal-image/video LS2 receiver refusal **#337 is deferred**;
this candidate does not fix or silently waive it. No new receiver permission is
introduced to bypass it. Built-in video and personal transfer remain separate paths.
Original #96/#282/#298/#307/#334 reports remain open according to their unresolved
work; host tests and package installation are not compatibility evidence.

After complete CI, select the exact successful run/attempt and verify ordinary
signed Root QA provenance and package hashes. The bounded morning session needs:

1. Supported signed System worker update on the existing Root installation,
   preserved state and retained rollback, with Home/controls/audio after transition.
2. Short/repeated Home, Back cancel/exit, arrows/OK/pointer/wheel/volume, explicit
   Root Off and physical emergency return with Helper stopped.
3. Ribbon editing/hide/undo and theme/storage feedback; distinguish built-in media
   from the known refused personal receiver path. Do not modify TV storage to fill
   a report or manufacture a low-space condition.
4. Standby and cold boot recorded separately, including actual routing and audio.
5. Suitable B4/C4 Home/AOD/Settings/SAM/cache and update/rollback checks, plus separate
   physical C1 lease/control/recovery acceptance where that hardware is available.
6. Exact signed Android upgrade and synthetic-data retention checks; physical
   phone-to-TV paths stay untested until actually exercised.

Run `python3 scripts/release-flow.py acceptance-report` and add scenarios selected
by the complete diff. Existing C3 observations cannot certify C1/C4, and changed
artifacts cannot inherit prior physical passes. The release PR stays draft until
its actual acceptance is recorded. No publication is authorized by this preparation.
