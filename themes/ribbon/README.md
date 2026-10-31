# Ribbon (bundled theme source)

Original galaxy wallpaper, compact native app logos and a skewed bottom ribbon. This theme uses bounded `layout.ribbon` data and ordinary appearance CSS. No theme-specific navigation code, uploaded author scripts or replacement app logos are included. Classic remains Home’s default.

The runtime bundle is `launcher/themes/ribbon`; `launcher/builtin-themes.json` registers packaged built-ins for both editions. Run `node scripts/build-builtin-theme.cjs themes/ribbon` after committing source, then run it with `--check` to verify reproducibility. Preview/provenance documents use simulated services and reference icons, not physical-TV acceptance. The separate toolkit keeps a development author example for matching future runtime exports.

`previews/community-preview.png` is the exact earlier prototype image approved by the user for the Reddit announcement. It is not a new device acceptance capture. The author thumbnail is rendered from the source theme; a final bundled-selection screenshot is checked separately.
