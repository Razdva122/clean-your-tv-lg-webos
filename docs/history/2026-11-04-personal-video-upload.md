# Personal moving-video upload — 2026-11-04

## Scope

The owner requested local moving video backgrounds, up to 4K, in the next
unfrozen release candidate, with supervised TV acceptance later. The current
`release/next` already includes #264/#267 video rendering and photo upload;
those paths generated static video loops from photos, but did not accept a
user's moving video. This change extends desktop CYTV's existing Wallpapers
flow and retains the existing receiver, personal slot, renderer and permissions.

MP4/MOV/MKV/WebM inputs are bounded at 512 MiB, 1–60 seconds and 3840×2160.
The desktop encoder normalizes sample aspect ratio, takes a centered 16:9 crop,
keeps motion/duration, removes sound and creates H.264 at 25 fps plus a first-frame
JPEG fallback. Actual UHD crops receive UHD and FHD variants. Smaller videos
receive compatible 1080p output, which does not add source detail. Existing
12 MiB UHD/4 MiB FHD limits remain; bitrate follows duration. Phone upload is
still image-only. There is no new dependency, network endpoint or wire format.

Input preview claims now detach the background decoder before allocating
HDMI/tuner media. Release/failure returns ownership. The static personal poster
remains behind the input; settings retain their standard background. Lost
window focus releases the background, and owners compose across focus, input,
visibility and settings. Remote actions and emergency behavior are unchanged.

## Checks and corrections

- Failing-before/passing-after tests cover moving video preparation, source and
  duration limits, sound removal through the TV's actual MP4 validator, cancellation,
  Qt video/photo selection and decoder handoff.
- Real 640×360 moving H.264 with audio retained distinct decoded frame hashes,
  retained 1.2 seconds and produced an accepted silent 1080p variant. A real
  native 3840×2160 MOV produced accepted UHD and FHD variants.
- Review reproduced filename/metadata spoofing of FFmpeg diagnostic facts.
  Anchored actual input/stream records and CR/LF filename rejection fix it;
  a crafted filename/comment no longer shortens or rejects a valid clip.
- Review reproduced disappearance of the personal poster during input ownership.
  Input-only suspension now retains it, including after another owner exits.
- Review reproduced incorrect framing of 720×576 SAR 64:45 video. Display geometry
  is normalized before crop/scale. The regression preserves the top/bottom color
  bands in both the 1024×576 poster and the encoded video.
- Full CYTV regression suite passed 711 tests (two environment skips) before the
  final review corrections. Final affected wallpaper/Qt/packaging tests passed
  32 tests after those corrections. The complete local UI group and TV web
  compatibility passed; focused input-preview and wallpaper lifecycle tests passed.
- Real-browser wallpaper decode/loop/detach/fallback passed. Both-edition personal
  settings, wallpaper controls/navigation, input overlay ownership and input
  presentation regressions passed. Qt English/Russian/German screenshots were
  inspected for layout; no personal content was used.
- Updated the runtime contract, all twelve maintained language guides and the
  affected Czech supplement. Existing CI exercises wallpaper tests and bundled
  FFmpeg in frozen Windows/macOS desktop builds.

## Candidate integration

[PR #299](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/299) merged
into the unfrozen `release/next` as `e2ff546cf3ebc5b07ed13677786273f57abb8375`.
The checked product source is `123bd928ba0b685b4b3a045fed434a0d582a5bed`.
[CI 41817781319](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41817781319)
passed Linux/macOS runtime and aggregate tests, browser and optional Python;
full-release was unselected. [Frozen desktop CI 41817781433](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41817781433)
passed the actual Windows and macOS Intel bundles, including wallpaper preparation,
Qt actions and bundled encoder/runtime checks. Preview build and integration policy
also passed. Final independent review had no blocking findings.

The existing personal transfer regression also passed both editions through
actual local HTTP receipt, chunked reading, service-private cache, explicit Apply,
real decode, reload and theme-owned background restoration. Deferred restore/source
ordering passed. These checks use synthetic media and do not contact a TV.
No component versions, selected build or acceptance decision were changed.

## Remaining acceptance

This is source/host/browser evidence. No TV was contacted or modified in this
work. TV model, firmware/webOS and remote for the planned session are not yet
recorded. Package installation, effective Root media grants, Home routing,
application/audio return, standby, cold boot, OTA and rollback are untested for
this change. A final versioned Home/service/desktop candidate and its full
release checks are required; this record does not select a version/build or
claim publication. Rebuild the desktop installer and affected Home/Root packages
at freeze. Keep the supervised TV acceptance tied to the exact resulting bytes.
