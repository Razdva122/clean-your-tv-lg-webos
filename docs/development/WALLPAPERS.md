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
