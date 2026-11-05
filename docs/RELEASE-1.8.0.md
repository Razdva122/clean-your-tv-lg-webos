# v1.8.0 — Wallpapers, Ribbon and installer improvements

Unpublished release candidate. The release PR remains draft until the exact frozen
build and affected hardware gates pass. Published downloads remain on v1.7.1.

## Changes

- Native video wallpapers, quality/dimming controls, personal desktop video/image
  transfer, phone image upload and reusable Black Hole by Xecutioner (#264/#267/#299).
  Desktop accepts MP4/MOV/MKV/WebM, 1–60 seconds, up to 4K/512 MiB; phone upload is
  image-only, up to 1080p. Media stays silent. Theme changes restore theme backgrounds;
  saved personal uploads can be selected again. Input previews coordinate decoder use.
  Artwork has separate attribution/non-commercial terms; see THIRD_PARTY_NOTICES.md.
- Root Ribbon can appear over positively identified active content, with Back and
  repeated Home dismissal; startup/unknown context uses an opaque fallback.
  No-root keeps fullscreen native Home. Updated compact Ribbon styling, editing and previews (#265).
- Native Root activation now follows prepared appearance and precedes foreground
  readiness frames; asynchronous appearance is awaited before updater health is
  acknowledged (#303). Verified off/emergency recovery closes the restored overlay
  and fences stale close replies (#305). Final packaged-TV timing and lifecycle
  acceptance remain pending.
- Root wallpaper video and input previews wait for a current context that explicitly
  reports no underlying content, including opaque themes and startup (#316).
  Refresh/hide invalidate the previous permission; unknown/active content retains
  a static poster. This is an opening/refresh snapshot, not a continuous decoder
  lease. The earlier C3 static-video/receiver-exit causes remain unestablished;
  final packaged-TV media and lifecycle acceptance are still required.
- Wallpaper wording now distinguishes a selected wallpaper without a video version
  from the capabilities of its theme, in English and all twelve translations (#313).
  This changes no playback capability.
- Installed Live TV tuner discovery includes the canonical hidden/missing launch
  point without exposing unrelated hidden apps (#293, #290).
- Typed Root activation diagnostics (#287, #282/#288), original-profile passive
  Android inspection (#289, #240), and macOS native CA trust for Python downloads
  (#297, #200). These improvements do not establish recovery of the original reports.
- No-root installer admits host-tested Node 0.10.15 (#291, #283/#284). Actual old TV
  WebKit/native ABI and reporter firmware compatibility remain unverified.
- After successful No-root installation, catalog readback waits for one matching
  Home/Helper snapshot (#302). IPKs explicitly retain required SDK parent directories
  through personalization (#312). These changes do not recover uncertain installs
  or establish resolution of the original reports #295/#201/#307.
- Passive IR diagnostics can run through their guarded stdin entrypoint over an
  existing trusted SSH connection (#306); package failure diagnostics retain
  allowlisted status/reason fields (#309). Original IR routing reports #207/#304
  and installation/recovery reports #201/#307 remain unresolved.
- Common installer automatically selects **C1 Beta** only after definite missing
  System Profile and verified C1/webOS 6/ARM32/stock ELF admission (#300, #298).
  Supported firmware retains profile routing; permission errors and timeouts never
  select the fallback. The independent native guardian preserves conservative recovery.
- CI scope maintenance (#294) and offline legacy Root research (#292, #160).
  The latter adds no supported Node 0.12.2 installation path. #279 is deferred.

## Versions and packaging

| Component | Published 1.7.1 | Candidate 1.8.0 |
| --- | --- | --- |
| Home | 1.8.1 | 1.9.0 |
| Home Helper | 0.6.22 | 0.7.0 |
| cytv | 0.8.1 | 0.9.0 |
| Android / versionCode | 0.7.1 / 19 | 0.8.0 / 20 |
| Root / infrastructure | 0.8.4 | 0.9.0 |
| Independent updaters | 0.4.2 | 0.4.3 |
| System Updater / protocol | 1.2.0 / 1 | 1.2.1 / 1 |

All installers and changed TV packages rebuild. Helper must be packaged from new
source, including media APIs/grants and tuner discovery; the old published Helper
cannot deliver them. Updater changes exclude C1 from ordinary setup/OTA. Existing
supervisors remain immutable; no general supervisor replacement path is introduced.
Helper rollback compatibility must be verified against the new exact archive;
previous approval for 0.6.22 does not approve 0.7.0.

## Installation, recovery and limits

Use the common desktop/console/Android installer. C1 Beta is fresh-install only:
no separate Beta installer, backend flag, Root Updater or ordinary OTA. Open LG Home,
long Back and ambiguous power recovery leave routing off; explicitly enable again
in TV Settings. Real interprocess mount namespaces are unsupported and refused;
same-namespace owned aliases have bounded recovery. No physical C1 compatibility
is claimed. See [C1 contract](development/C1-NATIVE-GATE.md).

Historical Root registrations retain their original media permissions. Use supported
fresh provisioning where new grants are required; never replace private receipts,
keys or LS2 rules to force acceptance. Existing Root QA requires coherent signed
System packages, preserved recovery, and no pending/ambiguous operation. Retain signed
rollback packages. No-root Helper transition and rollback need separate exact-byte
acceptance. The Homebrew Installer remains unreleased and is not promoted here.
The proposed No-root overlay integration (#310) is incomplete and is not included.
Helper runtime/startup and its exact rollback transition remain unaccepted; a
successful package installation alone does not establish working Home control.

## Verification

[Release PR #281](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/281)
tracks the final build/run:attempt, hashes, documentation pass and device gates.
Focused PR checks and isolated preview observations are historical evidence only.
The [ready-fix integration record](history/2026-11-05-ready-fix-integration.md)
lists the eight focused merges and combined-source checks. They do not select a
new full candidate or replace affected device acceptance.
Full frozen Linux/macOS/browser/ARM Python, Android and four desktop builds must
pass before selection. Exact signed artifacts still need affected installation,
controls/emergency, native media grants, sound/HDMI, standby, AC-off boot, supported
update and rollback checks. SSH/SAM launch does not verify physical Home or power.
Original reporter confirmation remains outstanding where recorded; no issue is
closed or public delivery announced by candidate preparation.
