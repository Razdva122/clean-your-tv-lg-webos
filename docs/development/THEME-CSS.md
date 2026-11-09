# Home CSS styling surface

This is the source-development contract for the Home theme engine.
TV theme controls require a compatible installed Home package; copying this
reference or a theme URL does not upgrade the engine. See the [design](../superpowers/specs/2026-10-28-theme-ecosystem-design.md)
and [runtime plan](../superpowers/plans/2026-10-28-themes-a-runtime.md) for the
remaining work and device acceptance gates. Browser preview results are not TV
compatibility evidence.

## Stylesheet ownership

| File | Responsibility |
| --- | --- |
| `launcher/style.css` | Trusted document structure, positioning, scrolling, hit areas, focus geometry and stacking; packaged Outfit font faces |
| `launcher/theme-defaults.css` | Classic Home appearance, organized by background, header, dock, cards, library and Inputs |
| `launcher/i18n.css` | Packaged language fallbacks, localized header adjustments and standard language/confirmation dialogs |
| `launcher/renewal-panel.css` | Standard No-root settings, renewal and update dialogs |
| `root-edition/ui/root-settings.css` | Standard Root settings, firmware, audio and update dialogs |
| `launcher/layout-panel.css` | Standard shared Columns control |

Load structure before Classic appearance, then trusted dialog and localization
styles. Keep cascade order, media-query order and existing specificity when
moving declarations. The build transforms supported source syntax for Chromium
38; the compatibility check examines emitted CSS. Runtime CSS custom properties
are not a prerequisite.

## Parts and states

`#homeSurface.ctv-home` contains Home, the application library and Inputs. The
following hooks are present in the actual renderer. A hook is not permission to
set every CSS property: the canonical author whitelist in
`launcher/theme-policy.js` decides accepted part/property/state combinations.
Internal IDs, tag names, application metadata, incidental classes and DOM nesting
are not an author API. All visual parts in the table are accepted by the initial
policy except `.ctv-tile`, which remains an engine-reserved interaction hook.

| Part class | Surface and ownership |
| --- | --- |
| `.ctv-home` | Theme root and bounded stacking context; root dimensions and containment are engine-owned |
| `.ctv-ambient` | Two app-color glow layers; crossfade and opacity are engine-owned, while an author background image may replace the default gradient |
| `.ctv-hero` | Focused dock app title; content, placement and enter/swap visibility are engine-owned |
| `.ctv-header` | Header appearance; placement and shortcut layout are engine-owned |
| `.ctv-greeting` | Localized greeting text |
| `.ctv-clock`, `.ctv-period`, `.ctv-date` | Localized time, period and date text |
| `.ctv-divider` | Decorative time/date separator |
| `.ctv-shortcut` | Inputs, network and Settings shortcut appearance; actions and hit areas are engine-owned |
| `.ctv-input-icon`, `.ctv-network-icon`, `.ctv-settings-icon` | Decorative header SVG artwork; use a listed raster `background-image` and `color: transparent` to replace its inherited fill. Bounds, actions and labels remain engine-owned. |
| `.ctv-dock` | Dock band appearance; bounds and visibility follow the grid engine |
| `.ctv-tile` | App and Add app interaction wrapper; position, width, hit area and ordering are engine-owned |
| `.ctv-card` | Visual child of an app/Add app tile; height and focus/moving transforms remain engine-owned |
| `.ctv-icon` | Packaged/app image or Add app SVG; source, error fallback and icon bounds are engine-owned |
| `.ctv-label` | App, Add app and library-row label text |
| `.ctv-focus` | Focus frame appearance; bounds, motion and visibility remain engine-owned |
| `.ctv-library` | Add app library overlay inside Home; modal layout, scrolling and controls remain trusted |
| `.ctv-library-panel` | Library inner panel appearance; modal size, position and scroll bounds remain engine-owned |
| `.ctv-library-close` | Library close-button appearance; action and focus behavior remain engine-owned |
| `.ctv-library-row` | Available app row in the library; native button focus is mirrored |
| `.ctv-inputs` | Inputs dropdown; anchoring, width and visibility are engine-owned |
| `.ctv-input-row` | Selectable input/source row; selection action and navigation remain trusted |
| `.ctv-input-shelf` | Theme-selected Inputs shelf on `dock-grid`, including its caption; geometry, clipping, scrolling and visibility are engine-owned |
| `.ctv-input-tile` | Selectable source tile in the shelf; position, size, launch action and navigation remain trusted |
| `.ctv-input-status` | Device name or "Not connected" text inside a shelf tile |
| `.ctv-input-preview` | Live picture frame inside the focused shelf tile; the frame inherits tile rounding, while native video clipping depends on renderer/firmware (earlier webOS 6 hardware ignored rounded clipping, masks and opacity). Starting, stopping, size and placement are engine-owned |

`.is-focused` mirrors remote/pointer focus on tiles, their visual cards and labels,
header shortcuts, library rows, the library close button, input rows and shelf
tiles. `.is-connected` and `.is-disconnected` mirror live TV input status on shelf
tiles and input rows only when the TV reports it; neither is present when status
is unknown, so do not style an absent state as disconnected. `.is-previewing` marks
the shelf tile whose live picture is playing; it appears only once the picture
plays and is removed as soon as it stops. Older Home versions
reject rules that use these shelf parts or states. `.is-moving` mirrors reorder state on a
tile and its card. `.is-selected` is a policy vocabulary token reserved for
selection states; do not assume that every part receives it or that focus means
selection. Existing `.focused` and `.moving` classes remain internal compatibility
hooks. Theme authors must not add state classes or manipulate focus.

The engine also exposes the library's inner panel and close control so a theme
can make the whole app library visually consistent. These are appearance hooks
inside Home, not access to standard Settings or recovery. They accept the same
validated visual properties; hiding, positioning, sizing and modal behavior
remain unavailable to author CSS.

## Initial validated CSS subset

The following table describes the current policy, not the full future design.
Each typed declaration has exactly the fields expected by its value family;
there is no raw CSS value escape hatch.

| Properties | Accepted values |
| --- | --- |
| `color`, `background-color`, `border-color`, `outline-color` | Typed RGBA; integer RGB channels 0–255 and alpha 0–1 |
| `background-image` | Verified local asset ID, or a linear gradient with angle 0–360 and 2–8 ordered color stops at 0–100% |
| `border-radius`, `border-width`, `letter-spacing` | Typed pixel length 0–32 |
| `border-style` | `solid`, `none` |
| `box-shadow`, `text-shadow` | 1–3 typed shadows; offsets −24–24 px, blur 0–40 px, spread 0–8 px and RGBA color |
| `font-family` | `sans-serif`, `serif`, `monospace`; named packaged-font selection is deferred |
| `font-weight` | `400`, `500`, `600`, `700` |
| `font-style` | `normal`, `italic` |
| `text-transform` | `none`, `uppercase`, `lowercase`, `capitalize` |
| `text-decoration` | `none`, `underline` |
| `transition` | One of `color`, `background-color`, `border-color`, `box-shadow`; duration 0–500 ms; `ease`, `linear`, `ease-in`, `ease-out`, `ease-in-out` |

Selectors contain 1–3 descendant part tokens and up to three unique approved
states per token. A rule has at most 64 declarations with no duplicate properties.
The bundle ceiling is 128 KiB, 512 rules and 4096 declarations. The final emitted
stylesheet, including every repeated asset handle and trusted wallpaper/accent
rule, is limited to 256 KiB. Prefer short verified blob handles for larger images;
small data-image handles remain supported within that total. Source CSS is limited
to 128 KiB. Author-variable expansion is memoized and cumulatively limited to
128 KiB of expanded text and 256 KiB of scanned input across the compilation.
The host compatibility pass uses small trusted image placeholders rather than
embedding asset bytes. These are parser and resource limits, not a promise of
device performance. Ordinary source
shorthands such as `background` are not accepted typed properties. The compiler
must reject unsupported source declarations or normalize only documented forms.

Theme focus-frame appearance can use `.ctv-focus`, but a focused app card also
receives an engine-owned solid border in the effective accent color: 2 px
for standard layouts and 3 px for the scenic ribbon. This
narrow trusted fallback uses `!important` so higher-specificity author states
cannot remove it. Authors still cannot emit `!important`. The runtime marks a
successfully applied surface with `ctv-theme-active`; reset removes that marker.
It is an engine lifecycle marker, not an author selector. While a theme is active,
the Classic glass specular decoration is removed so flat focus designs do not
inherit its highlight.

## Geometry, precedence and inline appearance

The renderer calculates card dimensions, row/column positions, dock size,
scroll offsets, focus-frame bounds and input anchoring. Its inline assignments
are intentional. Author CSS must not replace position, display, visibility,
width/height, margins/padding, transforms, pointer behavior or stacking. Altering
visual geometry independently would make arrow navigation and pointer hit areas
disagree with the rendered cards. New layout presets require engine changes and
navigation checks; a stylesheet cannot introduce one.

The engine accepts five trusted `layout.preset` values: `dock-grid`,
`icon-grid`, `side-grid`, `channel-list`, and `scenic-grid`. These select renderer-owned
compositions rather than injecting layout CSS. `dock-grid` remains the default
for Classic and existing themes. Unknown values fail validation. A renderer
without the full-layout application method rejects the new presets before
changing styles or column defaults; it never silently draws them as Classic.
Spacing, text and focus scales still require the Classic values `1`, `1`, and
`1.1`; wider schema bounds do not imply implemented scale combinations.

| Preset | Composition |
| --- | --- |
| `dock-grid` | Classic wide app cards, dock band near the bottom and selected app title above it |
| `icon-grid` | Compact square icon grid with labels and a smaller header |
| `side-grid` | Fixed clock/menu sidebar on the left and labelled app grid on the right |
| `scenic-grid` | Large light clock over wallpaper, one looping horizontal ribbon of square icons; Left/Right wraps, Up opens shortcuts, Down returns |
| `channel-list` | Numbered app rows on the left and selected app title on the right; narrow multi-column overrides use compact labelled cells |

In `side-grid`, the sidebar menu uses Up/Down to select a shortcut, Right enters
the apps, and Left from the first app column returns to the menu. Other grids
retain the horizontal top-menu navigation. These controls are available in
theme-enabled Home versions; the selected theme determines the layout.

The shared Columns control is available in 1.7.0 through
**Home settings → Appearance → Columns** in both editions. Values are integer 1–8 or **By
theme**. Precedence is explicit saved user number, then accepted theme
`layout.columns`, then Classic's 5. Selecting By theme clears the explicit
number; it does not change app IDs, hidden apps, input choices or ordering.
Column preference is stored separately at `tvhome.columns.v1`; existing profile
schema 1 remains unchanged. The displayed effective count is recalculated through
the existing renderer geometry.

App icon sampling currently sets each app card's inline `background` and caches
an accent color for the ambient glow. Glyph icons use the validated inventory
color fallback. An ordinary author `background-color` declaration does not
override that inline value; `!important` is forbidden. The ambient gradient is
emitted into a trusted default stylesheet instead of inline CSS, so a scoped
`.ctv-ambient` background image can override it, including a transparent gradient
for a flat background. Crossfade timing and opacity remain engine-owned. Themes keep
both glow layers and immediate remote focus unless they opt into
[Classic motion](#classic-motion-opt-in-unreleased). The engine fades `background` and
`color` on shortcuts and input tiles, but gradients cannot interpolate: change a
`background-color` under a constant `background-image` for focus fills that fade. Broken tile icons are hidden and replaced with the app initial;
broken library images are hidden without hiding their actionable row.

Outfit weights 300/400/500/700 and packaged Noto Sans fallbacks provide offline
text. `i18n.css` selects Devanagari, Korean, Simplified Chinese and Traditional
Chinese fallbacks, and adjusts localized date wrapping. Never fetch fonts from
a theme stylesheet or replace trusted dialog fonts. Supported author font names
and styles are enumerated by the policy; packaged files alone do not add a name
to that whitelist. Check all twelve locales, long labels and missing glyphs when
changing typography.

## Trust and containment

Authors supply data, never executable code. The intended path is source CSS →
host AST/compiler → typed rules → TV revalidation → trusted serializer → scoped
CSS. Only the canonical policy may serialize external typed values. A compiler
success flag or a selector prefix does not authorize arbitrary CSS on the TV.
Keep selector/value parsing and limits shared with the host compiler; do not
paste source CSS into a style element.

Author selectors are approved part/state tokens with bounded descendant depth.
The serializer supplies the `.ctv-home` scope. Global, sibling and arbitrary
attribute selectors, unknown pseudo-classes, imports, external URLs/fonts,
`!important`, fixed overlays, arbitrary z-index, hiding focusable elements,
pointer overrides, structural transforms and unbounded effects are rejected.
Only verified local asset handles may become image URLs. The policy is the
executable source of truth for exact properties, value families and budgets;
unsupported declarations fail rather than passing through as raw strings.

Home uses a bounded stacking context. The library is inside it; standard
Settings, Columns, Language, update, confirmation and recovery panels are outside.
Home's focus/reorder/library stacking is engine-owned. Trusted settings use
z-index 10000, Language 20000 and confirmation 30000; these numbers are not
available to theme authors. Toasts and recovery controls are trusted surfaces.

Both edition settings entry points use `ThemeRuntime.suspend(owner)` before
opening a standard panel and `resume(owner)` when that owner closes it. Nested
owners keep the theme sheet suspended until the last panel closes. The initial
hook suspends the dedicated `ctv-theme-style` sheet; it is not an installer,
asset store, trial confirmation or crash-recovery implementation. Those lifecycle
features still require their planned implementation and acceptance. Never let a
theme counterfeit update health or alter Home interception, triple-Home emergency
release, watchdog behavior, key-up delivery or unrelated buttons.

## Checking changes

Run from the maintained repository root after `npm ci`:

```sh
node tests/i18n/catalogs.cjs
npm run lint:compat
npm run test:geometry
npm run test:legacy-ui
scripts/test.sh
```

Run the focused theme policy/compiler/isolation checks added by the current
implementation as well. Use the real launcher with synthetic app data for visual
checks: dock, scrolled rows, focused tile, reorder, Add app, library, Inputs and
standard dialogs at 1/4/5/8 columns. Compare the Classic baseline, wait for fonts,
and keep screenshot time fixed. Record actual browser/package checks separately
from model/firmware/remote-specific hardware tests. Installation alone verifies
none of Home routing, audio, standby, cold boot, OTA or rollback.

The `channel-list` preset uses readable full-width cells when the user selects
multiple columns, and a separate selected-app image/title for its single-column
view. The header clips scrolling rows below its controls. Brand background
colors are retained separately and restored for Classic; list themes can paint
the selected row so labels stay readable during reorder when the glass is hidden.

Channel navigation uses the selected row itself as the stable focus surface;
the enlarged travelling glass is hidden in `channel-list`. Its row/stage
transitions are immediate. Remote keys suppress hover-driven focus until actual
pointer movement or a click; layout-generated mouseover at a stationary cursor
cannot override the selected row. This input ownership is transient, not stored.
`tests/themes/channel-navigation.cjs` keeps animations enabled and parks the
pointer over row eight while moving Up through the scrolling boundary.

The Channel selection title also updates synchronously in place. Pending title
swap timers are cancelled; fade/slide transitions remain disabled for this preset.

The `scenic-grid` preset defaults to eight columns in the Glasshouse-inspired
example. User overrides remain authoritative. The ribbon loops horizontally without title motion;
reorder temporarily lifts the row above its trusted Hide/Place controls.
The reference is https://github.com/rorygallagher2024/glasshouse; no third-party
application code is loaded. Settings and emergency UI remain trusted.

## Author-controlled column availability

`layout.allowColumnOverride` is an optional boolean, defaulting to `true` when
omitted. Set it to `false` for a composition whose column count must stay fixed:

```json
"layout": {
  "preset": "scenic-grid",
  "columns": 8,
  "allowColumnOverride": false,
  "spacingScale": 1,
  "textScale": 1,
  "focusScale": 1.1
}
```

The renderer uses the author's `columns`, hides the Columns settings entry in
both editions and rejects direct attempts to change it. An open Columns dialog
closes if a fixed theme is applied. The existing user preference is retained,
including in storage, and resumes for an adjustable theme or built-in Classic.
Existing themes remain adjustable without changes. A renderer without explicit
column-policy support rejects a fixed theme before applying its CSS or geometry.
There is no new preference key, permission or network endpoint.

This flag protects a composition from user reflow; it does not permit untrusted
positioning CSS or arbitrary HTML. Card coordinates and remote hit areas still
belong to the trusted preset. The looping horizontal ribbon is implemented by `scenic-grid`; other new
compositions still require renderer implementation and navigation verification.

### Scenic ribbon navigation

`scenic-grid` is the candidate preset name retained for compatibility, but now
renders every app on one horizontal row. Left/Right wraps at either end. The
window shifts horizontally when selection reaches an edge; recycled off-screen
nodes reposition without flying across the screen. There are no duplicate app
nodes, including in short lists. Up opens the shortcuts and Down returns to the
same app; Down within the ribbon never pages vertically. Rearrangement wraps
through real apps only; Add app remains a single terminal library action, and
Down during rearrangement selects Hide. Clock and wallpaper remain fixed.

### Scenic readability and pointer input

The scenic ribbon shows a static full selected name above the icons. Captions
use 28px text with a wider area than the icon; Add app can wrap to two lines.
Very long selected names use a smaller trusted size to retain the full detail.
There is one renderer-owned 3px focus border, with no second wrapper outline.
AM/PM in Latin 12-hour time is rendered as a smaller period label; other locale
formats are preserved. The geometry leaves room for captions above the bottom
safe area and lifts the row for rearrangement.

Wheel/touchpad input over the ribbon steps in either direction, throttled with
the event's monotonic timestamp. It is ignored during editing, app selection,
undo and trusted modal/visibility suspension. Reduced-motion overrides remain
honored. Ordinary selection updates do not detach/reinsert the app DOM nodes.
No new permission, endpoint or persistent preference is introduced.

The clipped next-card preview is noninteractive until revealed; this prevents
stationary-pointer hover from repeatedly dragging the ribbon under the cursor.

## Optional CSS icon effects

`modern-icon-css-v1` is a separately gated capability, not a change to
the normal Chromium 38 floor. The compiler infers it from icon `filter` or
`mix-blend-mode`; runtime requires browser support for both filter and screen
blending and rejects an unsupported browser before mutation. Older Home rejects
the unknown capability. Only typed `mix-blend-mode` and card-only `isolation` declarations are excluded
from the legacy compiler's compatibility probe; all other typed CSS still passes
through the unchanged compatibility checker.

Effects are restricted to selectors ending in `.ctv-icon`: `filter` accepts at
most four `grayscale(0..1)`, `invert(0..1)` or `brightness(0..2)` / `contrast(0..10)` functions (or
`none`); `mix-blend-mode` accepts `normal`/`screen`. Card-only `isolation` accepts `auto`/`isolate` to bound the blend backdrop; runtime gates isolate support too. URLs, SVG filter uploads, blur,
raw values and arbitrary properties remain rejected. Original image `src`, pixel
bytes and dimensions are never modified. `is-glyph` exposes the existing alpha
classification; `is-light` means the sampled background is opaque and every RGB
channel is at least 240. Opaque corner luminance also exposes `is-dark` (<.25), `is-mid` (.25–.5), and `is-bright` (>=.5). These are renderer metadata, not author-supplied app data.

In this optional mode, card `background-color` CSS is emitted with a narrow trusted
cascade override so inline brand backgrounds cannot defeat transparency. An exact
`.ctv-card.is-focused` CSS rule requesting both `border-style:none` and
`border-width:0` in `scenic-grid` uses a trusted 110% scale and visible white caption
instead of a card border. Other themes keep the existing border minimum. Themes
still cannot hide or reposition interaction controls. Clock/date-only `font-size`
is bounded to 22–176px; other text geometry remains trusted.

The [Itachi source](../../themes/itachi/README.md) has only wallpaper/preview images
and CSS. No replacement-logo support was introduced. Opaque colored backgrounds
cannot all be extracted by this CSS effect, and original Netflix resolution is
not improved by making it white. Browser tests do not establish TV acceptance.

Decorative image scale is also authored as CSS: `.ctv-card .ctv-icon { transform:
scale(1.6); }`. Only `scale(1..2)` on a card's icon is accepted, together with
card-only `overflow:hidden/visible`. Scaling requires a fixed `scenic-grid` with
at most five columns; other layouts/overrides reject before mutation so expanded
logos cannot overlap neighboring interaction cells. `is-wide` means original
image aspect ratio >1.5. Original sources and native pixel dimensions stay intact.
The engine emits the validated icon transform with a narrow trusted cascade
override against layout defaults, within the same stylesheet budget.

Native inventory capture prefers available `extraLargeIcon`, `largeIcon`,
`mediumLargeIcon`, `icon`, `miniicon`, then `favicon` resources from the same TV.
The desktop reader retains its same-host/protocol/size checks; Root retains its
existing filesystem boundary and per-image/total byte limits. Missing, rejected
or too-large variants fall back. This is normal inventory acquisition, not
a theme replacement map; the CSS renderer does not rewrite the selected source.

The `.ctv-position` part styles the decorative scenic-ribbon position indicator.
A transparent `color` hides its count and arrows without changing navigation.


<a id="theme-owned-input-placement-unreleased"></a>

## Theme-owned input placement

The selected theme chooses the header Inputs menu or the Inputs shelf. Omitted
`layout.inputs` means `"menu"`, including Classic and existing themes. There is
no global placement preference or **Show inputs on Home** switch. Liquid Glass
opts into `"shelf"`; the shelf is currently supported only on `dock-grid`. A
nonempty shelf replaces the header Inputs shortcut, and remote navigation skips
that hidden shortcut. When no source tiles exist, the menu remains available.
An explicit `"menu"` is valid on any preset.

For example, this compiled descriptor excerpt pairs the field and capability
(other required manifest fields are omitted):

```json
{
  "layout": {
    "preset": "dock-grid",
    "columns": 5,
    "spacingScale": 1,
    "textScale": 1,
    "focusScale": 1.1,
    "inputs": "shelf"
  },
  "requires": {"capabilities": ["input-placement-v1"]}
}
```

The source compiler emits `input-placement-v1` when `layout.inputs` is present,
including explicit `"menu"`. Descriptor policy requires the field and capability
together. Older Home rejects this capability before storing or applying the
theme. Input placement and the [Classic motion opt-in](#classic-motion-opt-in-unreleased)
are independent; selecting the shelf does not opt into Classic motion.

Use the existing parts and states for appearance, without new CSS syntax:

```css
.ctv-input-shelf { color: #ffffff; }
.ctv-input-tile { background-color: #202536; border-radius: 24px; }
.ctv-input-tile.is-connected { box-shadow: 0 0 0 1px rgba(120, 220, 160, 0.6); }
.ctv-input-tile.is-disconnected { color: rgba(255, 255, 255, 0.5); }
.ctv-input-tile.is-focused { background-color: #eef3ff; color: #101420; }
.ctv-input-status { color: rgba(255, 255, 255, 0.7); }
.ctv-input-tile.is-focused .ctv-input-status { color: #30384a; }
.ctv-input-preview { background-color: #000000; }
.ctv-input-tile.is-previewing .ctv-input-status { color: #ffffff; }
```

The engine owns geometry, hitboxes, source launch and video start/release. It
requests muted playback, but the native external-input pipeline may ignore that
request. Previews are on by default; an explicitly saved Off stays off. The user
can disable **Preview inputs on focus** in Appearance.
On a shelf, Up from the dock reaches the shelf, Up again reaches the header,
Down or Back returns to the dock, and OK launches the source. A connected HDMI
source can preview after about 800 ms of focus while **Preview inputs on focus**
is enabled; this preference only applies while the selected theme uses a
shelf. HDMI previews may play sound or switch HDR on some TVs. Home does not
automatically change global TV mute or HDR settings. Theme CSS cannot start
media, enable previews or change those TV settings. Software rendering clips the
frame to its inherited radius.
Native video composition must be checked per renderer/firmware: earlier webOS 6
observations ignored rounded clipping, masks and opacity. A 2026-11-02 standalone
browser probe on an OLED55C3RLA (firmware 43.21.71, SDK 11.2.0) rounded real HDMI 3,
but audio still played despite `video.muted = true`, and an HDR notification
appeared. This does not verify packaged Home or other models; mute and HDR
behavior remain unresolved. Do not rely on arbitrary masks/opacity for video
release or navigation safety. The engine releases previews when focus leaves, Home hides or loses focus, or an owned
dialog opens. Connection states appear only when the TV supplies them. Device
names come from firmware-provided input metadata; otherwise a connected source
shows the localized **Connected** status. Never invent a PlayStation name or
guarantee CEC identification. `previewing` appears only while a live picture is
playing.

In 1.7.0, Root reads input metadata through the authenticated,
same-package service `listApps` broker with the exact `{inputs:true}` selector
because firmware can deny direct WebApp EIM access. The existing method and
retained permission grant are reused; no new endpoint is registered.
The broker performs a fixed, bounded, privileged read-only query; it adds no
permissions or TV-setting writes. Root refreshes once when Home becomes visible,
a different input receives focus or Settings opens. There is no polling or
automatic retry, and failed/unavailable reads leave connection status unknown.
This is not continuous hot-plug monitoring. No-root keeps its direct EIM
subscription where available. A definitive permission refusal (`errorCode: -1`)
switches that session to bounded snapshots through its own renewal service's
`inputStatus` method. Only the Home application may call it with an empty payload.
The native Helper uses the existing pairing and only the TV's own interface
addresses to read `ssap://tv/getExternalInputList`; it never pairs or accepts a
caller-selected address, URI or command. Keys stay inside Helper. Replies contain
at most 100 devices, five bounded strings and boolean/unknown connection states.
No-root snapshots refresh on the same explicit foreground interactions as Root;
failure clears stale status and does not start a retry loop.

The fallback reuses the provisioned service `state/home-control` directory and
its shared-group permissions. Expiring correlated `input-request.json` and
`input-response.json` messages (atomic `.tmp` writes, mode 0660) are separate from
the existing Home-command files, so metadata cannot occupy Home settings or
stock-Home control. The query has a three-second budget within the five-second
broker deadline; concurrent controller reads share one query. Stop/emergency
state suppresses late responses. No directory, privilege grant, boot activity or
startup policy is added. Physical acceptance is specific to the selected build;
simulated services do not certify unrooted Developer Mode installation.

<a id="classic-motion-opt-in-unreleased"></a>

## Classic motion opt-in

By default a theme gets immediate remote focus on every layout: the card and the focus
frame snap, rows jump, there are no edge bumps or edge fades, and the ambient glow keeps
its two crossfading layers. A `dock-grid` theme can instead opt into the motion of
unthemed Classic with `"motion": "classic"` in `layout`:

```json
{"preset": "dock-grid", "columns": 5, "spacingScale": 1, "textScale": 1, "focusScale": 1.1, "motion": "classic"}
```

- **What it turns on:** the row glide on a single Up/Down press, the 10 px edge bump,
  the card zoom with the focus frame growing on the same 240 ms transform, the top and
  bottom edge fades (slightly softer than Classic's, so they read as a vignette over a
  wallpaper), and the baked glow.
- **Baked glow:** once the colour settles, the glow moves to a plain base element and
  both layers stop drawing. The base also carries `.ctv-ambient`, so the theme's ambient
  rule styles it, but only while the glow is baked; during a crossfade the base is empty,
  so a translucent ambient style never doubles.
- **Engine-owned transitions:** under this opt-in a `transition` on `.ctv-card`,
  `.ctv-focus`, `.ctv-label`, `.ctv-shortcut` or `.ctv-input-tile` is rejected, because
  it would replace the engine's transform, grow and fade motion and let the card and
  frame fall out of step.
- **Capability:** the compiler emits `classic-motion-v1`, and descriptor policy requires
  the field and the capability together, only on `dock-grid`. Older Home rejects the
  capability before storing or applying the package, keeping its current theme.
- **Cost:** keep shadows off parts that repaint on every press. On a 4K webOS TV a
  blurred shadow on the dock band and a translucent border on input tiles each cost
  about 2 missed frames per shelf press; a `0 0 0 1px` ring is cheap.

Reduced motion still turns all of this off.


<a id="parameterized-scenic-ribbons-unreleased"></a>

## Parameterized scenic ribbons

Use optional `layout.ribbon` with `preset: "scenic-grid"`, an explicit 1–8 column count and `allowColumnOverride: false`. The compiler automatically emits `ribbon-layout-v1`; descriptor policy requires options and capability together. Older Home rejects this capability before storing/applying a new package, retaining its current theme. This capability is included in Home 1.8.1 / release 1.7.0; the separate author toolkit still requires a matching exported runtime. Existing layouts without `ribbon` remain unchanged.

| Field | Allowed value | Default |
| --- | --- | --- |
| `left` | integer 64–640 px | 112 |
| `right` | integer 32–320 px | 112 |
| `bottom` | integer 0–200 px | 162 |
| `cardHeight` | integer 96–240 px | 128 |
| `gap` | integer 0–64 px | 24 |
| `skewDeg` | finite number −18–18 degrees | 0 |
| `focusLift` | integer 0–64 px | 0 |
| `iconScale` | finite number 0.4–1 | 1 |
| `shortcuts` | `header`, `bottom-left` | `header` |
| `edgeNavigation` | `wrap`, `shortcuts` | `wrap` |
| `labels` | `below`, `focused-above` | `below` |
| `showClock` | boolean | `true` |

Unknown keys and invalid combinations reject. Bottom-left shortcuts require `left >= 256` (three 68 px controls with 8 px spacing and a 28 px edge inset); below captions require `bottom >= 64`. Geometry reserves maximum focused skew extent on both sides and rejects a computed card width below 64 px; width is capped at 360 px. Combined checks use the fixed column count. The selected card grows and raises by `focusLift`, preserving its bottom edge. Captions, icon counter-skew and matching hit targets are trusted geometry. `iconScale` shrinks the original app-image box inside its card; Add app retains its native SVG artwork. Author CSS retains appearance hooks, wallpaper and colors.

```json
{
  "preset": "scenic-grid",
  "columns": 8,
  "allowColumnOverride": false,
  "spacingScale": 1,
  "textScale": 1,
  "focusScale": 1.1,
  "ribbon": {
    "left": 340,
    "right": 84,
    "bottom": 0,
    "cardHeight": 180,
    "gap": 0,
    "skewDeg": -13,
    "focusLift": 36,
    "iconScale": 0.65,
    "shortcuts": "bottom-left",
    "edgeNavigation": "shortcuts",
    "labels": "focused-above",
    "showClock": false
  }
}
```

This is the value of `layout`, not a complete manifest. The separate toolkit needs an explicit exported runtime declaring `ribbon-layout-v1`. Its stable reviewed runtime pin is not silently replaced by a PR candidate. Arbitrary author `position`, `skew`, `translate`, selectors or JavaScript remain unsupported. Version and capability checks both apply. Optional icon effects still require `modern-icon-css-v1` separately.


<a id="optional-date-placement-unreleased"></a>

### Optional date placement

A `dock-grid` theme may set `layout.datePlacement` to `below-clock` to wrap the
date beneath the clock and hide the divider, or `inline` to retain the standard
header. Declare the paired `date-placement-v1` capability; the compiler infers
it from the field. Engines without the capability reject the theme before apply.
Omitting the field preserves current themes. Suspension, replacement and reset
use the existing theme stylesheet lifecycle. No new controls or permissions.

### Optional overlay presentation (unreleased)

A theme with bounded `layout.ribbon` may set `layout.presentation` to `overlay`.
The compiler adds the paired `overlay-presentation-v1` capability. Engines that
do not know this capability reject the descriptor atomically, preserving the
accepted theme. The field cannot select another window type or execute code.

Presentation is host-owned: Root can expose active content only after a fresh
normalized compositor check. No-root falls back to the full wallpaper. Theme
suspension, settings/trial/recovery dialogs and unknown context force opacity;
reset removes the request. The native host never changes routing or permissions
because of a theme. See [Ribbon presentation](RIBBON-PRESENTATION.md).

## Weather integration

See the [shared weather contract](WEATHER.md) for supported formats, developer styling, preset reservations, compatibility and maintainer fork provenance. Home owns weather data and settings; themes contain no provider code.
