<a id="video-wallpapers-and-settings-next-release-development"></a>

# Video wallpapers and settings

This feature is included in published v1.8.2 (#281). Existing image-only themes continue to use their ordinary
fallback. This source contract and desktop playback do not establish universal hardware acceptance.

## Theme contract

Keep the existing `defaults.wallpaperAssetId` image. Add
`video-wallpaper-v1` to `requires.capabilities` and an optional descriptor field:

```json
"wallpaperVideo": {
  "variants": [
    {"quality":"4k", "path":"assets/wallpaper-4k.mp4", "mediaType":"video/mp4", "size":123456, "sha256":"<64 lowercase hex digits>", "width":3840, "height":2160},
    {"quality":"1080p", "path":"assets/wallpaper-1080p.mp4", "mediaType":"video/mp4", "size":45678, "sha256":"<64 lowercase hex digits>", "width":1920, "height":1080}
  ]
}
```

Use actual sizes and hashes. One or two unique qualities are allowed. The bounded
MP4 parser requires one H.264 video track, no audio, matching dimensions and a
finite 1–60 second duration. Use a silent, seamless still-image loop or appropriate
video. Codec/container validation does not establish the quality of the source
photograph or its rights. Include asset provenance and rights in CREDITS/LICENSE.

Limits: UHD video 12 MiB, FHD video 4 MiB, both 16 MiB combined; existing image
limits remain 2 MiB per asset/6 MiB total, with UHD reserved for the fallback
wallpaper slot. The complete verified package is at most 24 MiB; local transfer
envelopes at most 33 MiB; IndexedDB retains at most 64 MiB/eight versions. Both
bounded video qualities are retained to allow offline fallback without network
requests. Old engines reject the unknown capability instead of silently accepting
video data. Themes with no video field remain unchanged.

## Settings and automatic selection

Root and No-root add a localized Wallpapers category. It previews the active
theme's actual wallpaper image and provides Auto, 4K, 1080p, Image, dim adjustment
and reset. Missing wallpapers and unavailable qualities are explicit. Hardware
capability and current selected/playing mode are separate; unknown metadata stays
unknown. A video wallpaper suspended by settings is labeled "Paused while settings
are open"; image-only themes retain Image, and Classic shows No wallpaper. Auto
selects UHD only after affirmative TV capability data, otherwise FHD or the image. HDR is outside this feature.

Settings use `tvhome.wallpaper.preferences.v1`, bounded per theme, in the existing
app origin. They follow theme state rather than adding fields to legacy profile
wire formats. Normal same-origin updates retain preferences; legacy Root and
No-root profile restores that reset theme selection also clear wallpaper
preferences. System profile restore does not erase the existing same-origin theme state.

## Native cache and ownership

Native browser preparation uses `WallpaperMediaCache` so that playback does not
depend on native support for arbitrary Blob URLs.
The single full-screen Home can select the catalog-pinned built-in Black Hole
4K MSE stream before requesting a native cache lease. That packaged stream
independently verifies its full fragment hash and keeps a bounded buffer; it
needs no native-cache capability. Unsupported MSE retains the normal validated
cache route. Corrupt or failed packaged playback uses the static image rather
than an unchecked alternate URL. Personal/other media keep the cache protocol.

It exposes no author-supplied URL or script. The edition's existing service adds
`wallpaperCacheStart`, `Write`, `Commit`, `KeepAlive`, and `Stop` methods (all with
the `wallpaperCache` prefix). Every call checks the exact owning application ID.

Fresh Root packages advertise the explicit capability pair
`["theme-receiver-v1", "wallpaper-media-v1"]`. Only that fresh provisioning
contract grants the owning Home application the five cache APIs. Empty and
receiver-only saved registrations retain their original permission bytes during
repair, cancellation and updates, even if newer package metadata advertises the
pair. Updating Home alone or replaying an old registration does not grant native
media access; existing preserved registrations need supported fresh provisioning
or reinstallation before that path is available. The separate legacy receiver
permission attachment remains limited to its four APIs. No-root uses its paired
app/service package ownership and the cache's exact application-ID checks.

Upload uses at most 48 KiB byte chunks, ordered offsets, fixed quality names,
bounded declared sizes and actual SHA-256 verification before exposure. At most
two leases and 32 MiB temporary media are allowed. Service-private directories,
random URL tokens, only GET/HEAD, strict Range handling and loopback-only binding
limit access. The HTTP listener binds `127.0.0.1` on an ephemeral port; it never
listens on the LAN. A live acquired lease holds an activity and renews every
20 seconds; the server expires after 90 seconds without renewal. Temporary bytes
are distinct from the durable, verified IndexedDB theme package.

The renderer shows the static fallback until video is actually playing. It uses
one untransformed viewport video outside the logical Home surface. A failed or
stalled UHD stream falls back to FHD, then to the image. Hidden documents, lost window focus,
Settings/library suspension, Image mode, theme replacement and reset detach the
decoder before releasing the lease/URLs. Reacquisition recreates the local stream
from cached bytes. Late callbacks cannot take ownership after cancellation.
Input previews suspend the wallpaper before allocating input media and resume it
only after releasing that media (also on timeout/failure). Window-focus, settings
and input ownership compose, so returning focus cannot bypass another suspension.

## Verification and release admission

Focused tests cover trust boundaries, malformed MP4, caller identity, byte limits,
hashes/ranges, resource cleanup, stale async work, fallback and both settings
editions. Run `npm run test:themes`, `npm run lint:compat`, the new browser tests
and affected packaging/development tests. Exact legacy service runtimes and
physical TV acceptance must be identified explicitly when exercised.

Physical QA must verify the actual downloaded/cached-media path, offline replay,
settings focus and preview, hide/resume, switching to another media app and normal
audio/control return. Record model, firmware/webOS, remote if known, exact build,
expected/actual outcomes and untested cases under repository privacy/consent rules.
Desktop decode and a native package install do not satisfy final release gates.

## Personal wallpapers (next-release development)

Personal media is one independent wallpaper slot, not an installed theme. Both
editions offer a source switch between the current theme and My wallpaper.
Confirming a different theme restores its wallpaper. Personal uploads and built-in
choices remain available for explicit reselection. The selected wallpaper restores
on app relaunch until the user accepts a different theme. Preview and Apply on the TV are separate from receipt;
HTTP 202 confirms receipt only. A cancelled transfer, invalid image/video or
failed storage transaction preserves the accepted wallpaper. Removing the
personal wallpaper returns to the current theme. Personal image/video bytes are
not included in legacy profile wire formats and are never added to the theme
catalogue.

Desktop CYTV adds Wallpapers on its start screen, separate from installation.
It accepts JPG/PNG and local MP4/MOV/MKV/WebM video. Photos retain their adjustable
16:9 crop. Video uses a centered 16:9 crop after normalizing sample aspect ratio, preserves motion and duration, removes
all audio/subtitle/data tracks and encodes silent H.264 MP4 at 25 fps. Videos must
be 1–60 seconds, at most 512 MiB, with a declared source frame no larger than
3840×2160. Invalid/unknown duration, unreadable media, network/playlist inputs and
larger sources are rejected without replacing the accepted TV wallpaper.

Video preparation and transfer run outside the UI thread and can be cancelled.
The first decoded frame becomes the fallback/confirmation poster. A video crop
with at least 3840×2160 source pixels produces UHD plus FHD; smaller video sources
produce a compatible 1920×1080 variant (including upscaling, without added detail).
Photos still require a crop of at least 1920×1080 for FHD and 3840×2160 for UHD;
smaller photos stay image-only. Output retains the existing 12 MiB UHD/4 MiB FHD
limits. The bitrate budget follows clip duration; complex/long clips can lose
detail or be rejected if encoding exceeds a limit. Clips are not silently shortened.
FFmpeg uses the bundled executable, forced local container demuxers and a file-only
protocol whitelist. No FFprobe, download, new endpoint or wire-format change is needed.

Frozen desktop distributions include a pinned FFmpeg executable and its
attribution/source notices; no Node runtime or runtime binary download is needed.
The user opens receiving in TV Wallpapers and enters its private IPv4/PIN in
CYTV. The TV validates the received bytes before offering Apply.

Phone upload opens a temporary, self-contained page on the TV through its QR
code or manual address. Both devices must be on the same reachable private
network. The page accepts JPG/PNG, previews a 16:9 crop and creates a JPEG up to
1920×1080/2 MiB locally. Sending requires acknowledging that this is an ordinary
image, with sharpness limited by TV UI resolution, and not the native 4K video
layer. The TV retains the phone-source warning and does not offer 4K for that
image. The page, QR generation and photo preparation require no cloud service.
Video and HEIC input are outside this first phone uploader.

The four existing receiver Luna methods keep their owning-app authorization.
`themeReceiverStart({kind:"wallpaper"})` opts into personal media; old theme
sessions retain their original route and browser-Origin rejection. Personal
sessions serve GET `/wallpaper`, authenticated GET `/v1/wallpaper-capabilities`
and PIN-authenticated POST `/v1/wallpaper` on the existing temporary TCP 8879
listener. Only exact same-origin browser POSTs to the personal route are allowed,
and browser uploads must be phone images. No CORS wildcard is introduced. QR
PIN data is in a URL fragment; foreign Host/Origin, expired sessions and invalid
PINs are rejected. Closing the receiving view or hiding the app stops it.
A matching next-release Home/service is required; an older theme-only receiver
must not be represented as personal-media compatible.

The wire payload is versioned `kind:"wallpaper"`, with `source`, one hashed
image and zero to two hashed video variants. Image limits are 2 MiB and
3840×2160 for CYTV, 1920×1080 for phone. Phone variants are forbidden; CYTV video
retains the 12 MiB UHD/4 MiB FHD/16 MiB combined bounds. Base64, hashes, actual
headers and decoded dimensions are independently checked before persistence.
See the [approved personal wallpaper design](../superpowers/specs/2026-11-03-personal-wallpapers-design.md)
for the full field contract and separate release acceptance requirements.

## Authoring embedded media

The main compiler accepts `wallpaperVideo.variants` in author theme.json with
`quality` and safe local `path` fields. Pass the matching bytes in `input.videos`.
It derives media type, dimensions, byte lengths and SHA-256 from actual silent
H.264 MP4 files, validates the existing duration/budget rules, and emits the
`video-wallpaper-v1` capability automatically. Supplied dimensions must agree
with every compressed SPS; a 1080p stream cannot be labelled 4K. Ordinary
image-only source themes produce the same manifest bytes as before.

Prepare author media offline with the desktop encoder dependency:

```sh
python3 -m pip install imageio-ffmpeg==0.6.0
python3 scripts/prepare-theme-wallpaper.py original.jpg build/my-wallpaper
# Optional 20-second periodic editorial camera orbit:
python3 scripts/prepare-theme-wallpaper.py cosmos.jpg build/my-cosmos --motion
```

Use a new output directory. Preparation rejects originals whose 16:9 crop
cannot supply 3840×2160 actual pixels (4032×2268 for the moving margin).
It writes a UHD JPEG poster, UHD/FHD silent MP4s, and preparation.json with the
original hash/dimensions and crop/encoding settings. Existing output is never
overwritten; incomplete encoding remains private temporary output. Copy the
three media assets into the theme, retain the preparation record, add the two
paths under wallpaperVideo, and retain the image as defaults.wallpaperAssetId.
A declared pixel count cannot establish photographic detail or provenance;
authors must retain the source link, credit, license and edit description.

Use the matching toolkit branch/runtime for build, live preview, send and
submission. All those paths retain the videos; local send is bounded at 33 MiB.
New compiler exports include launcher/theme-data.js for shared MP4 validation.
Existing published runtime snapshots do not gain the feature automatically.
For a committed built-in source upgrade use
`node scripts/build-builtin-theme.cjs themes/ribbon --update-source`, followed
by the normal `--check`; the new bundle pins the source commit. This does not
admit the feature to the frozen release candidate.

## Built-in Black Hole and continuous playback

Video author: **Xecutioner**. Non-commercial use with explicit attribution is permitted as confirmed by the maintainer; see `themes/ribbon/LICENSE.txt` and `CREDITS.txt`. The artwork is not MIT. `wallpaper-library.js` reuses the verified bundled Ribbon media without applying its layout/CSS or duplicating its ordinary MP4s. `PersonalWallpaper` stores the selected built-in ID separately from the retained personal envelope in the same transactional slot. On a different accepted theme, selection returns to that theme; saved personal media remains intact.

`wallpaper-stream.js` recognizes only the pinned Black Hole UHD digest, checks the packaged fragment bytes against their SHA256, and appends them in MSE sequence mode on an infinite timeline. It retains a complete previous cycle before removing old GOPs, buffers future cycles, and disposes requests, timers and object URLs before detach. Unsupported MSE uses the ordinary MP4; streaming/decode failure uses the existing FHD/image cascade. External themes cannot supply executable streaming code or a new streaming URL. Ordinary MP4 validation is unchanged.

### First-frame handoff

The poster remains opaque above the decoding plane after `playing`. Where available, `requestVideoFrameCallback` and the following animation frame confirm a presented video frame before the Home surface becomes transparent. The video also uses the same poster URL. Hardware engines may expose but suppress the presented-frame callback while the poster occludes video. After dimensions have been validated, two advancing media-time samples with decoded-frame readiness provide a separate presentation path. Both paths cross two animation frames and retain the native poster. Progress without decoded frames does not renew the startup deadline. Older engines retain the native poster plus animation-frame fallback. Detach cancels the pending video-frame callback; generation checks reject queued stale presentation work. The existing startup/stall watchdog and FHD/image cascade remain bounded.
