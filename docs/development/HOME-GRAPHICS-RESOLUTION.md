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
with its exact manifest/hash and coherent component set. Never patch a signed
payload, substitute equal-version bytes or bypass a baseline/rollback refusal.

## Automatic selection and OTA

The candidate desktop/console and Android installers embed both Home packages
and both complete Root bundles. Before pairing/provisioning/install effects on a
fresh installation, query only `getSystemInfo` with `keys: ["UHD"]` on
`com.webos.service.tv.systemproperty`. LG documents this property since webOS 1.2:
[TV Device Information](https://webostv.developer.lge.com/develop/references/tv-device-information).
A successful reply with boolean true or exact string `true` selects 1920×1080;
false or exact `false` selects 1280×720. Missing, denied or malformed capability
stops the operation without guessing. Model names, current application viewport
and HDMI/video dimensions are not detection inputs. Status and retained recovery
remain available without a new capability query.

Selection is from a fixed, hashed payload catalogue; the selected package must
have the expected ID, version and `appinfo.json` resolution before personalization.
Root selection uses a complete coherent bundle, not an IPK swap inside an existing
bundle. Personalization preserves the selected resolution and rehashes its data.
Android uses this shared installer logic and verifies the same payload entries.

New OTA clients select independent signed schema-1 HD feeds:
`system-update-root-720p.json`, `system-update-no-root-720p.json` and
`root-update-720p.json`. Existing default feed names retain FHD and their original
schema for published clients. HD public packages have `_720p_all.ipk` names;
this does not change application identity or package architecture. The client
checks the selected signed launcher URL and actual package resolution, so a valid
FHD signature cannot substitute for an HD offer. URL/hash/proof fields are never
rewritten after verification.

The first HD release must increase Home and Root component versions relative to
the published FHD baseline. An HD legacy Home feed (`update-720p.json`) is emitted
only after a genuinely published compatible prior HD rollback package exists;
until then this legacy updater refuses the unavailable feed. The complete System
Updater can use its authenticated actual installed baseline for exact rollback.
Recovery/resume/rollback retain original bytes and proofs, even when those bytes
are FHD; they do not reselect a preferred variant during recovery. Existing
same-version, downgrade, signature, Helper and baseline restrictions stay intact.

Existing independently provisioned Root/System updater code does not acquire the
selector merely through application OTA. Use the supported computer setup or
explicit verified supervisor replacement workflow after publication, preserving
its recovery state and original rollback baseline. Do not edit retained code,
receipts or keys. Old clients keep their old channel behavior until migrated;
new installer builds provision the selector. See [System updates](../UPDATES.md)
for setup and migration prerequisites. No migration or TV test was performed here.

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
