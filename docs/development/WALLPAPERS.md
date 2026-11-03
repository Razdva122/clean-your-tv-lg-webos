# Video wallpapers and settings (next-release development)

This feature is isolated from the frozen candidate until its release coordinator
admits it. Existing published image-only themes continue to use their ordinary
fallback. Do not interpret this source document or desktop playback as shipping
or universal hardware acceptance.

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
It exposes no author-supplied URL or script. The edition's existing service adds
`wallpaperCacheStart`, `Write`, `Commit`, `KeepAlive`, and `Stop` methods (all with
the `wallpaperCache` prefix). Every call checks the exact owning application ID.

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
stalled UHD stream falls back to FHD, then to the image. Hidden documents,
Settings/library suspension, Image mode, theme replacement and reset detach the
decoder before releasing the lease/URLs. Reacquisition recreates the local stream
from cached bytes. Late callbacks cannot take ownership after cancellation.

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
Changing themes updates layout and styling without replacing the selected
personal background. Preview and Apply on the TV are separate from receipt;
HTTP 202 confirms receipt only. A cancelled transfer, invalid image/video or
failed storage transaction preserves the accepted wallpaper. Removing the
personal wallpaper returns to the current theme. Personal image/video bytes are
not included in legacy profile wire formats and are never added to the theme
catalogue.

Desktop CYTV adds Wallpapers on its start screen, separate from installation.
It accepts JPG/PNG, shows the source and cropped resolution, provides a 16:9
crop and runs local preparation/transfer outside the UI thread with cancellation.
Only a crop with at least 3840×2160 source pixels produces a UHD variant;
at least 1920×1080 is needed for FHD. Smaller sources use an ordinary image.
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
