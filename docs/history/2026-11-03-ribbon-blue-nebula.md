# Ribbon blue-nebula replacement — 2026-11-03

Next-release source update requested by the maintainer, outside the frozen release
inventory. Supersedes the Ribbon 1.1.0 Webb artwork in the earlier
[embedded wallpaper evidence](2026-11-03-embedded-uhd-wallpapers/README.md).
No TV was changed; model, firmware/webOS, remote and physical acceptance are not
exercised by this run.

Ribbon 1.2.0 replaces the bright scientific image with original fictional
blue/violet nebula artwork against near-black space, sparse stars and a quiet
lower area behind the app cards. The source is evaluated directly at4096×2304 by
`scripts/render-ribbon-nebula.cjs`; it is not an enlarged image-generation preview.
The two initial built-in image-generation concepts returned1672×941 despite UHD
requests and were used only as composition references. No source-site artwork,
texture or code is included. Prompts, rights and reproduction are recorded in
`themes/ribbon/ARTWORK.md`, CREDITS and LICENSE.

The existing author encoder downscales the original to a4032×2268 master and
crops a periodic camera orbit into20-second,24fps silent H.264 variants. Source
SHA-256:4862c70d73983c73868ec3e762fefa17e9b951e679ebee1f2c11c37b542deb79.
The UHD3840×2160 file is8,433,743 bytes; FHD1920×1080 is2,666,464 bytes. Both are
within existing media budgets. A static UHD JPEG is retained. At320×180 RGB
sample resolution the first/last-frame mean absolute difference is0.272 versus
6.084 at half the orbit; this bounds the loop seam against intended movement,
not physical-TV smoothness.

Verified on macOS with real Chrome and simulated services/public reference apps:

- Shared compiler and full package byte/hash/SPS verification of the new source.
- Actual3840×2160 video decoding and Image fallback/decoder release in both Home
  editions, with new Home captures and bounded960×540 thumbnail.
- Entire theme suite and reproducible built-in Ribbon/catalogue generation.
- Packaged Ribbon offline picker, persistence after reload, controls and Classic
  reset in both editions.
- Five focused toolkit example/build/transfer-envelope/real-browser tests, zero
  skips. This is fresh artwork coverage; the earlier64-test toolkit result
  remains a separate historical observation.
- Independent read-only review found no actionable issues in the renderer,
  provenance, encoding contract or updated artwork.

The original runtime permission/capability contracts are unchanged. No production
release, native webOS decoder acceptance, sound/other-app contention, standby,
cold boot, OTA or rollback is claimed for these new assets.
