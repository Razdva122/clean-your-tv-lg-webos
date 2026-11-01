# Home graphics resolution (candidate)

Issue #207 separates graphics layout, standard-remote routing and Helper status.
These changes add a 720p layout/build path; they do not establish physical TV or
IR compatibility. The installed Home source is never patched by the new code.

LG's [app resolution specification](https://webostv.developer.lge.com/develop/specifications/app-resolution)
distinguishes 1280×720 app graphics on FHD models from 1920×1080 graphics on UHD
models. App resolution is reported by `window.innerWidth/innerHeight`; video
screen dimensions are not a substitute. `appinfo.json` supports one graphics
resolution per package, not an automatic list of both.

## Runtime layout

Both Home editions retain the same 1920×1080 logical scene. `viewport.js` fits
only `#homeSurface` to the actual viewport, with no enlargement above logical
size. Inputs and upward shortcut navigation convert DOM rectangles back into
scene coordinates. Native browser hit-testing handles the transformed cards.
No routing, saved layout, theme package, input key or recovery state is changed.

Standard Settings, confirmation and recovery panels remain outside this scene
and use the physical viewport and their existing responsive CSS. Scaling the
whole body would shrink their `vh`/`vw` constraints twice. Do not reintroduce the
old installed-body scaling workaround on top of this implementation.

## Explicit HD source builds

Existing default source/release manifests remain 1920×1080. Builders now admit
only the two documented resolutions and leave original source manifests intact.
A compiled Home HD staging directory can be prepared without contacting a TV:

```sh
python3 scripts/tv_web_build.py --input launcher --output build/home-hd --resolution 1280x720
```

The full manual No-root package build accepts the same explicit selection:

```sh
CYTV_GRAPHICS_RESOLUTION=1280x720 scripts/build.sh
```

Root's isolated builder accepts `--resolution 1280x720`; for example:

```sh
python3 root-edition/build.py --output work/root-hd-candidate --version 0.0.1 --resolution 1280x720
```

These are build commands, not installation instructions. Keep the output paired
with its exact manifest/hash and coherent component set. This task does not add
automatic model detection, choose a different signed feed artifact, or substitute
HD bytes for an unchanged-version package. Normal desktop/Android release builds
still use the selected default manifest. Before claiming normal-channel HD
delivery, select and verify the appropriate final artifacts/update path; do not
patch a signed payload or bypass a version, baseline or rollback refusal.

Actual 720p graphics/package behavior on the reported LJ550T remains pending a
separately agreed owner session. Browser geometry is implementation evidence,
not confirmation of package installation, Home routing, sound, power or OTA.

## Helper status and remote evidence

In the candidate Home Helper panel, **Show diagnostics** displays only the
results of that panel's existing status calls. It does not start Helper, issue
another request or clear an emergency stop. A rejected public SSH request and a
panel request have different caller contexts; neither proves the other result.

The JSON exposes fixed outcomes (`pending`, `success`, `rejected`, `timeout`,
`invalid-json`, `invalid-response`, `transport-error`), a bounded numeric error
code and typed status booleans. `success` means an object reply with boolean
`returnValue: true`, not verified Home interception. Unknown values remain null;
error text, private IDs, logs and request contents are excluded. Share only this
small JSON when requested, with model/firmware, and review it first.

The [passive remote probe](PASSIVE-REMOTE-DIAGNOSTICS.md) is a separate preparation
for a future owner-agreed observation. It cannot validate an IR mapping or repair
routing. Current M-RCU relay selection, key-up, watchdog and triple-Home behavior
are unchanged. Do not enable an arbitrary IR device from a guessed name/code.
