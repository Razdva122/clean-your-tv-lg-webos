# Ribbon (bundled theme source)

Original blue-violet nebula on black space with a subtle 20-second camera drift, compact native app logos and a skewed bottom ribbon. This theme uses bounded `layout.ribbon` data and ordinary appearance CSS. No theme-specific navigation code, uploaded author scripts or replacement app logos are included. Classic remains Home’s default.

The runtime bundle is `launcher/themes/ribbon`; `launcher/builtin-themes.json` registers packaged built-ins for both editions. Run `node scripts/build-builtin-theme.cjs themes/ribbon` after committing source (use `--update-source` for an intentional committed source upgrade), then run it with `--check` to verify reproducibility. Preview/provenance documents use simulated services and reference icons, not physical-TV acceptance. The separate toolkit keeps a development author example for matching future runtime exports.

`previews/community-preview.png` is the exact earlier prototype image approved by the user for the Reddit announcement. It is not a new device acceptance capture. The author thumbnail is rendered from the source theme; a final bundled-selection screenshot is checked separately.

The new source is next-release development: native 3840×2160 H.264, 1920×1080 fallback and a static UHD JPEG are embedded offline. The original 4096×2304 procedural artwork is downsampled without upscaling; motion is a periodic camera drift. See CREDITS/LICENSE and wallpaper-preparation.json. Physical webOS playback acceptance remains separate.

See ARTWORK.md for the reproducible render/encode commands and concept-image provenance.
