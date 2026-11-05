# v1.8.2 — Wallpapers, Ribbon and installer improvements

Release 1.8.2 ships with the maintainer-approved scope and known limitations
recorded below. See the dated QA record for exact package evidence.

**Known Root limitation:** on the retained C3 registration, loading personal
images/videos is denied by LS2 before transfer. Built-in video wallpaper works.
This is deferred to [#337](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/337).

## Changes

- Alpine 1.5.0 is available through the theme catalog with a true 3840×2160
  Bachalpsee photograph and 4K/1080p video variants. Liquid Glass remains built in.

- Native video wallpapers, quality/dimming controls, personal desktop video/image
  transfer, phone image upload and reusable Black Hole by Xecutioner (#264/#267/#299).
  Desktop accepts MP4/MOV/MKV/WebM, 1–60 seconds, up to 4K/512 MiB; phone upload is
  image-only, up to 1080p. Media stays silent. Theme changes restore theme backgrounds;
  saved personal uploads can be selected again. Input previews coordinate decoder use.
  Artwork has separate attribution/non-commercial terms; see THIRD_PARTY_NOTICES.md.
- Ribbon remains a theme of the single full-screen Home in both editions, with
  its own background. Updated compact styling and editing are retained (#265).
  The native overlay experiment and second-application proposal are not shipped.
- Theme and personal-wallpaper restoration run concurrently; rendered readiness
  and updater health still wait for both validated appearances and frames (#303).
  Home uses ordinary CARD foreground and app-switching behavior. Helper does not
  wait for unused underlay context or close Home on passive foreground changes.
  Explicit Stop/emergency keeps bounded teardown and stale-reply fencing (#305).
- The catalog-pinned built-in Black Hole 4K stream is selected before native-cache
  acquisition. Its packaged fragment remains hash-verified, with first-frame,
  suspension and disposal guards. Unsupported MSE uses the validated cache path;
  failed playback keeps the static image. Other media retain normal transport.
  Wallpaper and input previews belong to foreground Home and release resources
  when hidden or unfocused; they do not display an external app beneath Ribbon.
  Focused C3 results and untested scenarios are recorded below.
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

- Helper startup after TV restart is corrected (#321). Relay cleanup and stalled
  output handling preserve bounded release and retain blocked recovery on cleanup
  failure (#318/#320). These changes require final input/audio/full-boot acceptance.
- Unused Helper research JavaScript modules are excluded from production packages
  (#322); the separate research foundations remain unconnected to live consumers.

## Versions and packaging

| Component | Published 1.7.1 | 1.8.2 |
| --- | --- | --- |
| Home | 1.8.1 | 1.9.4 |
| Home Helper | 0.6.22 | 0.7.4 |
| cytv | 0.8.1 | 0.9.2 |
| Android / versionCode | 0.7.1 / 19 | 0.8.2 / 22 |
| Root / infrastructure | 0.8.4 | 0.9.3 |
| Independent updaters | 0.4.2 | 0.4.4 |
| System Updater / protocol | 1.2.0 / 1 | 1.2.1 / 1 |

Component versions advance beyond the already-used preliminary packages; this
candidate never overwrites changed bytes at an equal version. All installers and
changed TV packages rebuild. Helper must be packaged from new
source, including media APIs/grants and tuner discovery; the old published Helper
cannot deliver them. Updater changes exclude C1 from ordinary setup/OTA. Existing
supervisors remain immutable; no general supervisor replacement path is introduced.
Helper rollback compatibility must be verified against the new exact archive;
the exact new 0.7.4 archive passed published-Home compatibility as recorded below.

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
No-root uses the same full-screen Home with its running Helper. Ribbon does not
expose another app or HDMI behind its cards, and repeated Home is not a transient
bar toggle. Menus/editors retain normal Back priority. No companion, extra
component or new installer protocol is required. Focused hardware results and remaining limitations are recorded below.
Focused Helper startup, old-Home compatibility and physical emergency release
passed on the recorded C3. A real automatic OTA/rollback transaction remains
untested; successful package installation alone is not broader acceptance.

## Verification

[Release PR #281](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/281)
tracks the final build/run:attempt, hashes, documentation pass and device gates.
Focused PR checks and isolated preview observations are historical evidence only.
The [ready-fix integration record](history/2026-11-05-ready-fix-integration.md)
lists focused merges and their source checks. They do not select a
new full candidate or replace affected device acceptance.
The selected full Linux/macOS/browser/ARM Python, Android and four desktop build
results are linked in the release record. Focused signed Root installation,
physical Home, video persistence, LG return and exact Helper compatibility were
checked as recorded below. Sound, standby, AC-off boot and normal automatic OTA/
rollback remain untested in the maintainer-selected short run. SSH/SAM launch
alone is not physical Home or power acceptance.
Original reporter confirmation remains outstanding where recorded; no issue is
closed or public delivery announced by candidate preparation.

Preliminary single-Home observations and remaining gates are recorded in
[the dated C3 QA report](history/2026-11-05-single-home-regressions.md).

## Known issue accepted for this release

On the retained maintainer C3 Root registration, personal wallpaper image/video
receiving is denied by LS2 before transfer (`themeReceiverStart`). Built-in Ribbon
video wallpaper works. The maintainer explicitly moved the receiver failure to
[follow-up #337](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/337) and
authorized shipping with this limitation. No role/receipt/key replacement or forced
permission workaround is offered. Fresh Root provisioning and other firmware
behavior are unverified by that observation.

Focused final Root Home invocation, moving UHD background, persistence beyond
120 seconds and return to LG passed. Published Home 1.8.1 with the exact new Helper
0.7.4 passed its same-package broker/non-root-controller compatibility probe;
final Home 1.9.4 and the original portable profile/appearance were restored.
Sound, standby, cold boot and a real normal OTA/rollback transaction were outside
the maintainer-selected short run. These are untested limits, not passing claims.
