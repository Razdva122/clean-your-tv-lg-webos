# Ribbon blue nebula artwork

The final wallpaper is original code-rendered artwork at 4096×2304. No reference
site asset, scientific image or AI bitmap is used as an input texture. The render
is evaluated directly at native pixel coordinates, then the existing author
encoder downscales to UHD/FHD with a slow 20-second periodic camera orbit. TV
packages contain only verified image/video bytes, never the WebGL shader.

From the project root, with the existing npm build dependencies and pinned
imageio-ffmpeg==0.6.0 author dependency:

```sh
BROWSER_CHANNEL=chrome node scripts/render-ribbon-nebula.cjs
python3 scripts/prepare-theme-wallpaper.py build/ribbon-blue-nebula-original.png build/ribbon-blue-nebula-media --motion
```

Use a new encoder output directory for each iteration. GPU floating-point
implementations can change render bytes; the accepted image/video assets and
source digest are recorded in Git and wallpaper-preparation.json. Exact package
reproducibility uses the committed asset bytes, not a claim of cross-GPU bitwise
shader determinism. Both aspect ratio and source pixel count exceed UHD.

## Concept generation

The built-in OpenAI image-generation tool was used for two visual concepts.
Both returned 1672×941 PNGs despite a 4K request. They served only as composition
references; they were not enlarged or included in the final video. The production
render is the procedural source above. No separate API/CLI image service was used.

First prompt:

> Create one original cinematic dark-space wallpaper bitmap for a television launcher, landscape 16:9, render at native 3840 x 2160 pixels (4K), maximum available quality. A restrained, exquisite deep blue and indigo nebula, small hints of violet and icy cyan filaments, luminous wisps and subtle three-dimensional gas structures concentrated around the upper-middle center, surrounded by genuinely near-black empty space. Sparse tiny pinpoint stars with subtle varied luminosity, no large diffraction spikes or lens flares. The nebula should occupy roughly the central 45% of the image width and 40% of height, with generous almost-black space extending all the way around it. Dark corners and edges, and especially the lower quarter mostly black and quiet, because application cards will occupy the bottom of the screen. Elegant high-end OLED space ambience, cinematic volumetric CGI artwork, refined delicate detail and smooth gradients, deep blacks with locally beautiful highlights; restrained exposure, not a bright colorful NASA nebula filling the whole frame. No planets, no sun, no black hole, no spacecraft, no horizon, no text, no logos, no borders, no watermark, no UI. Original composition, not a copy of any specific artwork. This image will become a subtle animated wallpaper; keep all outer edges visually black so the frame can gently drift a few pixels without a visible border.

Second prompt, using the first generated concept as its reference:

> Regenerate the preceding original blue-nebula wallpaper as a full-resolution landscape production asset. REQUIRED OUTPUT FILE DIMENSIONS: 3840 pixels wide by 2160 pixels high (native 4K UHD, 16:9). Do not return a preview-size 1672x941 bitmap. Use the highest output resolution available. Preserve its almost-black background, restrained elegant blue/cyan/violet nebula centered in the upper-middle and empty black lower quarter, sparse tiny stars. Re-render nebula filaments with fine original detail at the target resolution rather than sharpening or enlarging a small image. Dark corners and edges, no text, logos, spacecraft, planets or large flares. This is original cinematic CGI concept art for an OLED TV wallpaper.
