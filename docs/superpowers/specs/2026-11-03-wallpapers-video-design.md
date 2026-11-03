# Wallpapers and video backgrounds

User-authorized scope: ship a real wallpaper video layer in the next release, automatic compatible quality selection, and a Wallpapers settings category with the active theme image and controls. Work remains isolated from the existing frozen release candidate; no feature merge or release publication before its coordinator admits it.

## Contract

- Existing Theme API 1 image-only packages remain valid and unchanged. Optional `wallpaperVideo` is gated by `requires.capabilities: ["video-wallpaper-v1"]` and always requires an ordinary `defaults.wallpaperAssetId` fallback.
- `wallpaperVideo.variants` has one or two bounded file records: `quality` (`4k` or `1080p`), `path`, `mediaType: video/mp4`, `size`, `sha256`, `width`, `height`. Dimensions are exactly 3840x2160 or 1920x1080. H.264 MP4 only, one video track, no audio, finite 1–60 second duration. Image/CSS budgets stay unchanged; video limits are 12 MiB UHD, 4 MiB FHD, 16 MiB combined. Whole package at most 24 MiB; app-owned cache at most 64 MiB and eight versions.
- Hash, size, bounded MP4 header and dimension validation precede any playback. Both bounded variants are retained for offline fallback. This deliberately spends extra download bytes to avoid networking when 4K fails.
- ThemeData.prepare returns existing image `assetHandles` plus separate `videoHandles` keyed by quality. No video can be referenced by author CSS or arbitrary network URL. The C3 Blob probe rejected playback with NotSupportedError. Native transport therefore uses owner-authenticated Luna upload and a tokenized 127.0.0.1 HTTP range server. Lazy leases materialize verified cached bytes; release on hide/suspend closes the server/activity and removes temporary files; reacquire restores offline bytes. Do not claim package-file evidence proves downloaded-media compatibility.
- New trusted `HomeWallpaper` owns one untransformed, viewport-sized, silent looping video outside the scaled Home surface. Static theme CSS remains until successful playback. Actual playback failure/stall descends UHD -> FHD -> image, without changing Home control, emergency handling or silently dropping the selected theme.
- Detect supported resolution using official TV metadata, with unknown preserved. Auto selects UHD only with affirmative support; otherwise FHD or image. HDR is not added. A selected quality is not proof of physical panel detail.
- Hide, exit, suspension, reset and replacement pause/detach media and release owned handles. Guard every async operation with generation identity. Settings/library remain trusted UI.
- Wallpapers pane: actual wallpaper preview (not catalog screenshot), current theme, detected capability/current path, Auto/4K/1080p/Image, dim minus/plus, reset to theme defaults. No false enabled controls for unavailable variants. Image-only/Classic states are explicit. Persist bounded per-theme quality/dim preferences; include in existing profile backup semantics where applicable.
- Preserve existing remote navigation and visible focus. Shared panel in Root and No-root, twelve localized user-guide updates. No new dependencies, external tracking endpoints or Apple asset redistribution.

## Acceptance

Node boundary/policy tests, real-browser media lifecycle/navigation tests, ES5/CSS compatibility, packaging allowlists, profile behavior and affected UI checks. Physical owner-supervised QA must exercise downloaded/cache video, focus/control/audio return and release/resume behavior. Static package installation and desktop decode alone do not satisfy release acceptance. Record blockers honestly and do not merge into a frozen candidate.
