# Liquid Glass (bundled theme source)

Clear frosted glass over an original aurora wallpaper, on the Classic dock with the Inputs shelf. Theme API 1 has no blur, inset shadows or radial gradients, so the glass is made from translucent white gradients, bright rims and soft outer shadows, over a wallpaper that is already soft. It declares `layout.motion: "classic"` (capability `classic-motion-v1`), so it keeps unthemed Classic's glide, bump, zoom, edge fades and baked glow, and it sets no transitions of its own. No theme-specific navigation code, author scripts or replacement app logos are included. Classic remains Home’s default.

The wallpaper (`assets/aurora.jpg`, 1920×1080) is procedural: a `#070a1a` base with four blurred colour areas (violet, teal, magenta, blue), a light vignette and ±2 noise against banding on OLED panels.

The runtime bundle is `launcher/themes/liquid-glass`; `launcher/builtin-themes.json` registers packaged built-ins for both editions. Run `node scripts/build-builtin-theme.cjs themes/liquid-glass` after committing source, then run it with `--check` to verify reproducibility. `assets/preview.jpg` is a browser capture with the reference icons, not a physical-TV acceptance capture.
