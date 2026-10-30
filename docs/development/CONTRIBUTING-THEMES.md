# Contribute a theme to Clean Your TV

This walkthrough takes an independent author from an empty theme folder to a
reviewable Showcase pull request. Theme sources stay in **your own repository**;
the main project stores a reviewed, fixed distribution and its catalogue record.
You can test a private, unfinished theme on your TV without submitting anything.

**Candidate status:** the author toolkit/runtime and theme-enabled TV controls
are still development candidates. Do not assume a published Home package contains
them. The current controls live in **Settings → Appearance**. No official
prebuilt author-runtime download is pinned yet; runtime preparation below is an
explicit source-development step. A theme PR does not update Home or publish a
release by itself.

## Contents

1. [Understand what you are contributing](#1-understand-what-you-are-contributing)
2. [Prepare the tools and a trusted runtime](#2-prepare-the-tools-and-a-trusted-runtime)
3. [Create your theme repository](#3-create-your-theme-repository)
4. [Style the theme and choose a layout](#4-style-the-theme-and-choose-a-layout)
5. [Open the interactive PC preview](#5-open-the-interactive-pc-preview)
6. [Prepare real preview images and credits](#6-prepare-real-preview-images-and-credits)
7. [Try the theme on your own TV](#7-try-the-theme-on-your-own-tv)
8. [Commit and build a fixed distribution](#8-commit-and-build-a-fixed-distribution)
9. [Generate a Showcase submission](#9-generate-a-showcase-submission)
10. [Open the main-project PR](#10-open-the-main-project-pr)
11. [Understand review and publication](#11-understand-review-and-publication)
12. [Maintain and update your theme](#12-maintain-and-update-your-theme)
13. [Troubleshoot common failures](#13-troubleshoot-common-failures)

## 1. Understand what you are contributing

| Item | Where it belongs | Purpose |
| --- | --- | --- |
| `theme.json`, `theme.css`, original images, license and credits | Your public author repository | Editable source of truth |
| `cytv-theme.json`, hashed rules/images/documents | A versioned directory in your author repository | Data-only package downloaded by Home |
| `showcase/registry/owner--repo--slug.json` and reviewed package copy | Your PR to the main project | One fixed version for discovery and review |
| Generated `launcher/theme-catalog*` files and inventory | Same main-project PR | Catalogue snapshot consumed by TV packages and live refresh |
| Preview server, browser screenshots and local draft folders | Your computer | Development/review artifacts; not executable theme content |

The author writes CSS against the public styling API. The compiler converts it
into validated, typed rules. A TV does not execute your source CSS as unrestricted
code. Author JavaScript, HTML, installers, plugins, remote fonts and network
imports are not accepted theme payloads.

Themes can style **Home, the app library and Inputs**. Settings, confirmation,
updates and recovery retain their trusted appearance. Layout presets own card
geometry and remote hit areas; a theme cannot replace navigation code.

One author can publish several themes. Each has its own stable lowercase ID:

```text
github:your-name/your-tv-themes:ocean
github:your-name/your-tv-themes:forest
```

The ID identifies the theme; its display title can change. A version identifies a
particular release of that theme. Approval of Ocean does not approve Forest or a
future Ocean version.

## 2. Prepare the tools and a trusted runtime

You need Node.js **22 or newer** and npm. The optional source-export route also
needs Git and Python 3. A GitHub account and a public repository are needed for Showcase
submission, but not for a local PC/LAN preview.

The [tested toolkit candidate](https://github.com/Razdva122/clean-your-tv-lg-theme/actions/runs/40934073336)
includes the runtime. Download its `theme-toolkit-candidate` artifact and follow
the [archive instructions](https://github.com/Razdva122/clean-your-tv-lg-theme/blob/48a7594c872794229801f0a6495952d3733a3f99/docs/CANDIDATE.md); no manual runtime export is needed for that bundle.

For development from source, use three separate directories: the main project, the author toolkit, and your
own theme repository. The following shell examples use POSIX syntax suitable for
macOS/Linux or Git Bash. In PowerShell, set equivalent absolute path variables
and run the same Node commands; shell assignments and `cp` syntax differ.

For a reproducible candidate baseline, these revisions contain the documented
commands and current theme-settings flow:

| Repository | Candidate revision |
| --- | --- |
| `Razdva122/clean-your-tv-lg-webos` | `08b6acac0972ac035370070450953ac2a3d9938f` |
| `Razdva122/clean-your-tv-lg-theme` | `48a7594c872794229801f0a6495952d3733a3f99` |

The downloaded bundle above pins main runtime `a790807d` and already supports
da.gd. Its actual provenance source is the PR merge `a3c3718b`, whose complete
Git tree equals toolkit source `48a7594c` in the table. The source workflow below
exports the newer main `08b6acac` runtime; that exact toolkit/runtime combination
also passed validation of the CSS-only Itachi theme. The newer runtime is needed
for optional `modern-icon-css-v1` authoring; an older bundled runtime cannot compile
those effects. Keep `--runtime` explicit rather than silently substituting files.

These are source candidates, not signed releases. Maintainers may provide a newer
reviewed pair. Do not mix an older runtime with hooks introduced by newer tools,
and do not use an unrelated theme repository as executable runtime tooling.

From a parent development directory, clone dedicated checkouts:

```sh
git clone https://github.com/Razdva122/clean-your-tv-lg-webos.git
git clone https://github.com/Razdva122/clean-your-tv-lg-theme.git

cd clean-your-tv-lg-webos
git checkout --detach 08b6acac0972ac035370070450953ac2a3d9938f
npm ci --ignore-scripts
python3 scripts/export-theme-runtime.py --out build/theme-author-runtime
cd ../clean-your-tv-lg-theme
git checkout --detach 48a7594c872794229801f0a6495952d3733a3f99
npm ci --ignore-scripts
mkdir -p .runtime
cp -R ../clean-your-tv-lg-webos/build/theme-author-runtime .runtime/candidate
cd ..
```

Use new clones for these commands; do not switch or reset an existing checkout
with unfinished work. The exporter requires a clean tree unless explicitly run
with `--allow-dirty`. An author should normally use the clean export above. A
maintainer-supplied dirty snapshot is labelled as such and remains a candidate.
Existing export directories are not overwritten: choose a new output path for a
new export.

Set these variables to the absolute directories on your own computer:

```sh
THEME_TOOLKIT="/absolute/path/clean-your-tv-lg-theme"
THEME_RUNTIME="/absolute/path/clean-your-tv-lg-theme/.runtime/candidate"
THEME_REPO="/absolute/path/your-tv-themes"
THEME_DRAFTS="/absolute/path/theme-submission-drafts"
```

`THEME_RUNTIME` must point at the **whole exported directory**, including
`runtime.json`. Keep it unmodified and outside your editable theme folder.
Keep this export under the toolkit checkout, as `.runtime/candidate` above, so
its compiler can resolve the installed build dependencies. An arbitrary standalone
temporary directory will not resolve those dependencies. `node_modules` belongs
in the toolkit checkout, not inside the runtime export.
The toolkit verifies the runtime's inventory, byte lengths and hashes before
loading its compiler. Hashes detect changed files; use a trusted source to establish
who supplied the runtime.

There is no working `runtime:fetch` download to substitute at this stage. See the
[toolkit runtime reference](https://github.com/Razdva122/clean-your-tv-lg-theme/blob/48a7594c872794229801f0a6495952d3733a3f99/docs/runtime.md)
for the candidate trust model.

## 3. Create your theme repository

Create an empty public GitHub repository under an account you control. Replace
`your-name`, `your-tv-themes` and `Your Name` below with your actual values. Use
the same lowercase owner/repository spelling in theme IDs and submission URLs.
Clone your repository into the `THEME_REPO` directory, then run:

```sh
cd "$THEME_REPO"
node "$THEME_TOOLKIT/bin/theme.cjs" init themes/ocean \
  --name Ocean \
  --repository https://github.com/your-name/your-tv-themes \
  --author "Your Name"
```

The target theme folder must be empty. The result is:

```text
your-tv-themes/
  themes/
    ocean/
      theme.json
      theme.css
      LICENSE.txt
      CREDITS.txt
      assets/
        preview.png
```

Edit `theme.json` and check the generated ID, title, description, author profile,
version, layout, asset declarations and licensing. The description must explain
the actual design in plain text. Do not keep another author's ID or profile when
starting from their example.

The generated `preview.png` is a **1×1 placeholder**, not an acceptable Showcase
thumbnail. Replace it in step 6. Also complete the license text and credits;
template text does not grant rights to third-party images.

For a second theme, run `init themes/forest` with `--name Forest` and the same
repository. Do not copy Ocean's identity into Forest. Each folder keeps separate
CSS, assets, version and licensing metadata.

## 4. Style the theme and choose a layout

Start with a small `theme.css` using public parts:

```css
:root { --ink: #eeeae1; }
.ctv-home { color: var(--ink); background-color: #182025; }
.ctv-clock { color: var(--ink); }
.ctv-card {
  background-color: #223039;
  border-color: #51636a;
  border-radius: 12px;
}
.ctv-card.is-focused { border-color: #c5dfaa; }
```

Use the [public CSS reference](THEME-CSS.md) and the exported
[contract](../../theme-api/contract.json) for supported selectors, states and
properties. Internal DOM IDs, arbitrary selectors, `position`, transforms or
unlisted properties are not an extension API. The compiler rejects unsupported
rules instead of accepting a partial design silently.

Choose `layout` in `theme.json`, for example:

```json
{
  "preset": "dock-grid",
  "columns": 6,
  "allowColumnOverride": true,
  "spacingScale": 1,
  "textScale": 1,
  "focusScale": 1.1
}
```

This is the **value of the existing `layout` field**, not a replacement for the
whole manifest.

| Preset | Composition |
| --- | --- |
| `dock-grid` | Low shelf and app grid |
| `icon-grid` | Compact square icons |
| `side-grid` | Sidebar shortcuts and app grid |
| `channel-list` | Numbered app rows with selected-app artwork |
| `scenic-grid` | One horizontal ribbon that loops in both directions |

Columns are 1–8. With `allowColumnOverride: true` or the flag omitted, the user's
explicit Columns setting takes priority over your default. With `false`, your
composition uses its fixed count and hides that setting; the user's saved
preference returns on switching to an adjustable theme. This does not unlock
arbitrary card placement. In this candidate, use exactly `spacingScale: 1`,
`textScale: 1` and `focusScale: 1.1`; other combinations are rejected.

Unreleased parameterized scenic ribbons use optional `layout.ribbon` with fixed columns. See the [bounded ribbon parameters](THEME-CSS.md#parameterized-scenic-ribbons-unreleased) for geometry and `ribbon-layout-v1`. Use a matching explicit PR runtime; the reviewed toolkit pin does not gain capabilities automatically. Unsupported Home rejects the new theme before installation, retaining its selection.

For wallpaper, declare a local PNG/JPEG/WebP asset with its real dimensions and
media type, then use its ID in `defaults.wallpaperAssetId`. `defaults.dim` accepts
0–0.85. Check readability over both bright and dark parts of the image.

Home shortcut artwork uses `.ctv-input-icon`, `.ctv-network-icon` and
`.ctv-settings-icon`. Register transparent PNG/WebP images, then style the hook:

```css
.ctv-input-icon {
  color: transparent;
  background-image: url(assets/button-inputs.png);
}
```

Keep the visible button label and focused contrast. Theme-uploaded SVGs, remote
URLs and data URLs are not accepted. See the toolkit's
[icon recipe and layout examples](https://github.com/Razdva122/clean-your-tv-lg-theme/blob/48a7594c872794229801f0a6495952d3733a3f99/docs/authoring.md).
Alpine's source directory/old external ID uses `glasshouse`; its display name is
Alpine. Channel's source directory/ID uses `terminal`. Give your own theme an
independent identity rather than reusing either historical name.

## 5. Open the interactive PC preview

From your theme repository:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" preview themes/ocean \
  --runtime "$THEME_RUNTIME" --edition no-root --port 8766
```

Open **http://127.0.0.1:8766/** in a browser. Keep the terminal running. Click
inside Home to give it keyboard focus, then use arrows, Enter and Esc/Back. Save
`theme.css` to see valid changes automatically. Invalid edits keep the last valid
design and display an error above the screen. Stop the server with **Ctrl+C**.
Use `--port 8767` if the port is busy or `--port 0` to have a free port printed.

Repeat with `--edition root` to inspect that edition. For several local themes:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" showcase themes \
  --runtime "$THEME_RUNTIME" --edition no-root --port 8877
```

Open **http://127.0.0.1:8877/** and choose a theme preview above the real Home
surface. The local picker includes Classic for comparison. This author preview
is separate from the published community Showcase and does not submit a theme.
Apps and services are simulated; the preview never pairs with a TV automatically.

Check the following manually rather than reviewing only the first Home image:

| Area | What to inspect |
| --- | --- |
| Home | First/last app, clock/date, shortcuts, long labels, missing icons |
| Focus | Pointer and arrows, visible frame, no cropped labels or flicker |
| Scrolling | Last rows for grids/lists; repeated left/right wrap for the ribbon |
| Reordering | Hold Enter, move, place, cancel; labels and controls stay readable |
| Library | Add app, selected/empty states, scrolling, close button, wallpaper scrim |
| Inputs | Readable labels, focus and Back |
| Settings | Standard readable appearance, including Appearance and Columns |
| Layout preference | By theme and an explicit user override; fixed themes preserve it |
| Editions and sizes | Root/No-root; 1920×1080 and 1280×720 scenes |

Browser checks do not establish physical remote, TV storage, standby, cold boot,
OTA or rollback compatibility. Record untested scenarios honestly.

## 6. Prepare real preview images and credits

Install the toolkit's pinned browser explicitly, separately from npm setup:

```sh
cd "$THEME_TOOLKIT"
npm exec playwright install chromium
cd "$THEME_REPO"
node "$THEME_TOOLKIT/bin/theme.cjs" screenshots themes/ocean \
  --runtime "$THEME_RUNTIME" --edition no-root --out review/ocean-draft
```

Stop another preview using the default port before running `screenshots`. Output
must be new/empty. The command creates `home.png`, `inputs.png`, `settings.png`
and `provenance.json`. It uses the actual renderer, synthetic apps, English locale
and a fixed clock. The captured scene is scaled to fit the preview viewport,
so current output may be smaller than 960×540; read the PNG's actual dimensions
instead of assuming a fixed size. It checks trusted Settings isolation.
The provenance records the runtime and browser used. It does not automatically
cover every locale, long-name/empty-list case or scrolled layout.

Replace the placeholder with the actual Home capture:

```sh
cp review/ocean-draft/home.png themes/ocean/assets/preview.png
node - <<'NODE'
const fs = require('node:fs');
const path = 'themes/ocean/theme.json';
const manifest = JSON.parse(fs.readFileSync(path, 'utf8'));
const png = fs.readFileSync('themes/ocean/assets/preview.png');
const asset = manifest.assets.find(a => a.id === manifest.previewAssetId);
asset.path = 'assets/preview.png';
asset.mediaType = 'image/png';
asset.width = png.readUInt32BE(16);
asset.height = png.readUInt32BE(20);
fs.writeFileSync(path, JSON.stringify(manifest, null, 2) + '\n');
console.log('Preview dimensions:', asset.width, asset.height);
NODE
```

The script updates the declared dimensions from the actual screenshot header,
retains PNG media type and keeps the scaffold's `previewAssetId: "preview"`.
If you resize or recompress an image, declare its final actual dimensions and
format. You may also register the Inputs/Settings images as separate assets for
additional catalogue previews. A Showcase record accepts **one to four** previews;
each must be an actual, hashed image asset in the reviewed distribution.

| Resource | Current limit |
| --- | --- |
| Preview image | At most 960×540 and 300 KiB |
| Wallpaper (`defaults.wallpaperAssetId`) | At most 3840×2160 and 2 MiB; downsample the original rather than upscale a thumbnail. Requires the UHD wallpaper candidate runtime. |
| Other image | At most 1920×1080 and 2 MiB each |
| All images | At most 16 assets and 6 MiB total |
| Supported image formats | PNG, JPEG, WebP with matching extension/media type |
| Source CSS / typed rules | 128 KiB each |
| Emitted stylesheet | 256 KiB |
| Descriptor | 64 KiB |

Limits are ceilings, not a reason to ship unnecessarily large files. The toolkit
does not resize/compress images automatically. Verify image sizes before building.
Do not use a photograph or AI mockup as evidence of what the renderer looks like.

Update `CREDITS.txt` for every wallpaper, icon and other third-party asset: its
filename, creator, original source, license and modifications. Retain required
notices. Add full license text to `LICENSE.txt`. A freely viewable/downloadable
image is not automatically licensed for redistribution.

The exact catalogue license identifiers are `MIT`, `Apache-2.0`, `BSD-2-Clause`,
`BSD-3-Clause`, `ISC`, `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, and the specifically
reviewed composite `MIT AND CC-BY-SA-3.0`. The last value exists for Alpine's
reviewed combination; it is not a general expression parser or permission to
relicense another asset. Other licenses/combinations require maintainer review
and, if necessary, an explicit policy change.

Validate the final source and capture final review images into a new directory:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" validate themes/ocean --runtime "$THEME_RUNTIME"
node "$THEME_TOOLKIT/bin/theme.cjs" screenshots themes/ocean \
  --runtime "$THEME_RUNTIME" --edition no-root --out review/ocean-final
```

Keep the final provenance with your review evidence. Do not put credentials,
real device screenshots, network names, addresses or private app inventories into
public previews. Optional physical-device reports need the device owner's
permission before publication; follow the main project's [report rules](../../AGENTS.md#installation-results-and-user-consent).

## 7. Try the theme on your own TV

No Showcase PR, public repository or clean source commit is required. The main author workflow is **outgoing PC → temporary TV receiver**, so it works without opening an incoming port on your Mac.

1. On a matching theme-enabled TV candidate, open **Settings → Appearance → Receive from computer**. The TV shows its private IPv4 address, six-digit PIN and expiry time.
2. Start the toolkit's `preview` or `showcase`, choose your theme and press **Send to TV**.
3. In the computer dialog, enter the address and PIN **shown by the TV**, then click **Send theme**. The local toolkit compiles a fixed snapshot and makes an outgoing HTTP request to TV TCP **8879**; the browser does not need a cross-origin network exception.
4. The TV checks descriptor identity, rules, image/document hashes and native image decoding before saving a downloaded copy. Choose **Apply theme** on TV to save the selection immediately, without a timer. The computer's Sent status confirms delivery, not application.
5. Inspect actual Home, library, Inputs and standard Settings with your remote. The installed copy works after the receiver closes and after the computer shuts down.

Keep both devices on the same trusted home network and the receiver pane open during transfer. Guest-network/device isolation and a blocked TV port can still prevent delivery. A managed Mac's incoming block-all rule does not need changing for this direction. The transfer uses local HTTP and a short-lived PIN; do not forward the TV port to the internet.

The receiver handles one upload and closes on receipt, cancellation, leaving the pane, ten-minute expiry or twenty invalid PIN attempts. It accepts a bounded compiled envelope, not source scripts or arbitrary files. PINs are not persisted or placed in transfer URLs. The toolkit may remember the TV address, but clears the PIN after successful sending or closing the dialog.

After editing, reopen Receive from computer on TV for a new session/PIN and send again. Saving a source file does not silently change the installed copy.

Command-line alternative:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" send themes/ocean \
  --runtime "$THEME_RUNTIME" --tv TV_PRIVATE_IPV4 --pin SIX_DIGIT_PIN
```

Replace both placeholders with the current TV values. The preview dialog is the normal entry point and avoids typing shell commands for each transfer.

Only PC → TV transfer is supported. Do not start a server or enter a computer address on TV; enter the TV address and PIN on the computer.

Installed/built-in themes apply without a timer. A new Showcase trial still requires **Keep theme** within 20 seconds. To remove an active downloaded version, apply another theme first and then select **Remove**; built-ins cannot be deleted. Showcase hides installed IDs, so updates use Send to TV or **Add by URL**.

If the primary receiver is unavailable, update the complete matching Home/service set. Root upgrades also need the supported retained worker and receiver permission transition; replacing only the Home IPK is insufficient. The [Root upgrade diagnostic](../history/2026-10-29-root-receiver-upgrade.md) records the initial candidate limitation and distinguishes explicit computer maintenance from rebuilt-package acceptance. A new toolkit alone cannot add a service to an older installed Home. Root and No-root browser/packaging checks cover both editions; [the physical record](../history/2026-10-29-theme-push-acceptance.md) describes only the tested fixture/model and its limits. See [TV theme instructions](../THEMES.md).

## 8. Commit and build a fixed distribution

There are deliberately two revisions:

```text
Source commit A
    ↓ build (descriptor records A)
Distribution commit B
    ↓ public URL pinned to B
Showcase PR (records A, URL at B and descriptor SHA-256)
```

You cannot put B's final hash inside files that are part of B itself. The build
records the source revision A; the public descriptor URL points at the later
revision B containing the generated bytes. Both are fixed and independently
verified.

Before building, complete the previews, credits and manual checks. Commit every
file inside the source theme folder, including images and notices:

```sh
cd "$THEME_REPO"
git add themes/ocean
git commit -m "Create Ocean 1.0.0 theme sources"
THEME_SOURCE_COMMIT=$(git rev-parse HEAD)
node "$THEME_TOOLKIT/bin/theme.cjs" build themes/ocean \
  --runtime "$THEME_RUNTIME" \
  --source-repository https://github.com/your-name/your-tv-themes \
  --source-commit "$THEME_SOURCE_COMMIT" \
  --out distributions/ocean/1.0.0
```

The build checks that the supplied source commit is the repository's current
HEAD, that theme inputs are tracked and clean, and that the repository matches
the theme identity. Output must be outside `themes/ocean` and new/empty.

The distribution contains a descriptor (`cytv-theme.json`), typed rules under
`rules/`, hashed images under `assets/`, hashed license/credits under `documents/`
and a validation report. Do not hand-edit generated bytes or remove referenced
files. Source `theme.json` and distributed `cytv-theme.json` have different roles;
the TV installs the latter.

Commit and publish the distribution in your own repository:

```sh
git add distributions/ocean/1.0.0
git commit -m "Publish Ocean 1.0.0 distribution"
THEME_DISTRIBUTION_COMMIT=$(git rev-parse HEAD)
git push origin HEAD
THEME_DESCRIPTOR_URL="https://raw.githubusercontent.com/your-name/your-tv-themes/$THEME_DISTRIBUTION_COMMIT/distributions/ocean/1.0.0/cytv-theme.json"
```

Keep that commit reachable in the public repository. Do not force-push it away,
replace its URL with `main` or require authentication. Showcase submission records
keep this full immutable URL. Personal installation may additionally use the
keyless da.gd ID described in the toolkit’s release-link guide; it never replaces
the canonical descriptor URL or digest in a reviewed record.
All referenced files must be publicly available alongside the descriptor with
unchanged bytes. Personal development can continue through LAN; public Showcase
review requires these fixed remote bytes.

### Optional: discover several themes from one repository URL

Build each theme into a separate versioned directory. To create a root discovery
index while keeping the descriptor paths unchanged:

```sh
node "$THEME_TOOLKIT/bin/theme.cjs" collection \
  distributions/ocean/1.0.0 distributions/forest/1.0.0 \
  --out . --runtime "$THEME_RUNTIME"
```

Commit/push the generated repository-root `cytv-themes.json` in another commit.
The existing descriptor URL at B remains valid. The root index discovers 1–32
unique theme IDs from the same repository; it does not grant catalogue approval.
A root `dist/cytv-themes.json` alone is not repository-root discovery: the file
must actually be at the repository root with correct relative paths.

Each theme still needs a separate Showcase record, independent version and
review. To submit a second theme, repeat the build and submission steps for that
folder. When building another theme at a later HEAD, pass that actual clean HEAD
as its source commit instead of reusing a stale value of `THEME_SOURCE_COMMIT`.

## 9. Generate a Showcase submission

Keep the variables from step 8. Replace the evidence text with the scenarios and
results you actually observed, including browser/runtime versions in the PR:

```sh
THEME_REVIEW_DATE=$(date -u +%F)
node "$THEME_TOOLKIT/bin/theme.cjs" submission distributions/ocean/1.0.0 \
  --runtime "$THEME_RUNTIME" \
  --source "$THEME_DESCRIPTOR_URL" \
  --out "$THEME_DRAFTS/ocean-1.0.0" \
  --date "$THEME_REVIEW_DATE" \
  --tags dark,minimal \
  --evidence "Browser: Home focus, library, Inputs, reorder/cancel and standard Settings checked in both editions. Physical TV not tested."
```

The command validates and creates a **local draft**. It does not open a PR,
publish your theme or approve itself. Do not copy the sample evidence unless you
performed those checks. The current generator creates `kind: "browser"`
evidence; add properly consented/redacted `kind: "device"` evidence separately
when you actually have it.

```text
theme-submission-drafts/ocean-1.0.0/
  registry/
    your-name--your-tv-themes--ocean.json
  assets/
    your-name--your-tv-themes--ocean/
      <descriptor-sha256>/
        cytv-theme.json
        rules/...
        assets/...
        documents/...
  SUBMISSION.md
```

Check the generated record against [the schema](../../showcase/schema.json):

| Field | What must be true |
| --- | --- |
| `id`, title, author, version | Match this exact descriptor; profile matches repository owner |
| `sourceRepository`, `sourceCommit` | Your actual repository and source commit A |
| `descriptorUrl` | This specific descriptor at distribution commit B, not a collection URL |
| `descriptorSha256` | SHA-256 of the exact descriptor bytes; generated automatically |
| `previewFiles`, `creditsFile` | Paths relative to `showcase/`, within this hashed package |
| `tags` | Only `dark`, `light`, `minimal`, `colorful`, `photographic`, `high-contrast` |
| `addedAt`, `reviewedAt` | Draft proposals; final dates belong to maintainer review |
| `evidence` | Actual observations and explicit limits, not a compatibility promise |

The generator selects one Home preview. To offer up to four images, include the
additional captures as registered source assets **before building**, then list
their generated hashed paths in `previewFiles`. Do not add an unrelated image to
the draft and bypass the descriptor's asset inventory. Keep `provenance.json`
with review evidence; it is not a runtime theme asset and does not belong inside
the hashed package unless the accepted format explicitly permits it.

## 10. Open the main-project PR

Fork **Razdva122/clean-your-tv-lg-webos** on GitHub. Use a separate checkout of
your fork for the submission; keep the pinned runtime-export checkout untouched.
Create a branch based on the current **`release/next`** target:

```sh
git clone https://github.com/your-name/clean-your-tv-lg-webos.git theme-showcase-pr
cd theme-showcase-pr
git remote add upstream https://github.com/Razdva122/clean-your-tv-lg-webos.git
git fetch upstream release/next
git switch -c theme/ocean-1.0.0 upstream/release/next
npm ci --ignore-scripts
cp -R "$THEME_DRAFTS/ocean-1.0.0/registry/." showcase/registry/
cp -R "$THEME_DRAFTS/ocean-1.0.0/assets/." showcase/assets/
node scripts/build-tv-theme-catalog.cjs
```

If the integration target does not yet contain the candidate Showcase tools,
ask maintainers which prepared base to use or wait for integration. Do not copy
the whole theme-engine feature into an unrelated theme-submission PR.

The catalogue generator updates the explicit launcher catalogue, preview/notice
files and packaged inventory. Commit its changed files together. Do not commit
generated website output under `build/` or your author toolkit, runtime export,
`node_modules`, local credentials or private review captures.

Run the submission checks from the main-project PR checkout:

```sh
node scripts/check-theme-submissions.cjs
node scripts/check-theme-submissions.cjs --remote
node scripts/build-tv-theme-catalog.cjs --check
node tests/showcase/registry.cjs
node tests/showcase/submission-security.cjs
node tests/showcase/remote.cjs
node tests/showcase/site.cjs
node tests/showcase/browser.cjs
node scripts/build-showcase.cjs build/theme-submission-review/themes
```

The Showcase browser test needs Playwright Chromium (installed in step 6 with
`npm exec playwright install chromium`), or an explicit
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` pointing at an existing browser. A custom
browser is a diagnostic departure from the pinned browser; record which one you
used. CI installs Chromium itself. The final builder
needs a new/empty destination; use a new output directory on a repeat run.
`--remote` checks every active pinned record, not just your new one. If another
record has disappeared, identify which source failed in the PR; do not rewrite
someone else's package to make the check pass.

For the full repository regression entry point, run `bash scripts/test.sh` with
the tools described in [build requirements](../BUILD.md). The commands above
are the focused Showcase checks, not a replacement for repository contribution
requirements.

Review `git diff --stat` and `git diff` before committing. Stage only your new
record/package and the catalogue files changed by the generator; inspect its
console output and `git status --short` for the exact file list. Commit, push
your branch to your fork, then open a PR to upstream **`release/next`**.

Suggested PR title: **Add Ocean 1.0.0 theme to Showcase**. A useful body contains:

```text
Theme: Ocean 1.0.0
ID: github:your-name/your-tv-themes:ocean
Design: [what makes the composition distinct and readable]
Source commit A: [full hash]
Distribution commit B: [full hash and descriptor URL]

Licensing/ownership:
- [what you authored]
- [each third-party asset, source, license and preserved notices]

Validation:
- [exact toolkit/runtime revisions]
- [commands run and actual results]
- [browser editions, sizes and manual scenarios]
- [link/attachment for synthetic previews and provenance]
- Physical TV: [not tested, or redacted observed tests with consent]

Limitations:
- [known layout/locale/device issues and untested scenarios]
Related issue: [only if one exists]
```

Do not label an install success as proof of standby, OTA, cold boot, rollback or
all-TV compatibility. For another person's device, obtain their permission for
the exact public report and destination before posting it.

## 11. Understand review and publication

Automated checks validate identity, source metadata, allowed files, selectors,
resource bounds and all referenced hashes. The remote job fetches pinned bytes
without redirects or credentials. Submission checks do not execute your
repository's scripts, dependency hooks or workflows.

Maintainers review design usability, focus/navigation, preview accuracy,
attribution, license permissions, evidence and source ownership. A matching
profile string is not proof that you own someone else's work. Approval applies
to a fixed descriptor digest and the normal reviewed merge; there is no
author-editable `approved` flag.

The normal path is:

```text
Your theme repository: committed source + published distribution
    → PR to main project's release/next
    → automatic checks + maintainer review
    → normal release integration into main
    → Pages/TV catalogue availability
    → users download and try the theme
```

A PR inspection artifact is not a deployment. A merge into `release/next` does
not mean the theme is already public on TVs. Opening/refreshing the TV Showcase
checks reviewed catalogue data on main without reloading Home; an unpublished
or unreachable remote catalogue falls back to the bundled snapshot. Installing
a theme still verifies its own pinned source files. Verify publication before
announcing that others can install it through Showcase.

Voting and automatic promotion into built-in themes are **not implemented**.
Popularity is not approval, and a public listing does not bundle a theme with
Home. Published built-ins are Classic and Alpine; this unreleased candidate also bundles Ribbon. Channel remains an external listing.

## 12. Maintain and update your theme

For a release such as Ocean 1.1.0:

1. Keep the same `id`; change `themeVersion` and document visible changes.
2. Update CSS/assets/credits and repeat preview, validation and relevant TV checks.
3. Commit the new source A, build into a new empty
   `distributions/ocean/1.1.0` directory, then commit/push distribution B.
4. Generate a new draft using the new descriptor URL, digest, evidence and date.
5. Update the existing main-project registry record, retaining its original
   `addedAt`; maintainers assign the new `reviewedAt` after review.
6. Add the new digest directory, regenerate the TV catalogue, and submit a new PR.

Do not modify old distributions in place or remove historical files required by
reviewed versions. Keeping the same ID does not grant permission to silently
change installed TVs: installed copies are cached and do not follow a branch.
Users explicitly install/select an update. Current Showcase filtering hides
installed IDs, so existing users update through LAN or **Add by URL**.

For a permanent source outage, contact maintainers through the existing
submission PR/relevant issue. Maintainers can review an `unavailable` state or
remove the listing while retaining a stable explanatory page. A new mirror or
replacement package needs explicit review; it is not a silent URL substitution.
See the [maintainer Showcase guide](../../showcase/README.md).

## 13. Troubleshoot common failures

| Symptom | Check/fix |
| --- | --- |
| `Runtime unavailable` | Complete trusted export path, `runtime.json`, compatible toolkit revision; no published fetch is pinned yet |
| `Runtime integrity mismatch` | Replace the whole export with the trusted original; do not edit hashes to hide a change |
| `127.0.0.1` refuses connection | Keep the preview command running and use its printed port; Ctrl+C stops the server |
| CSS stays on the previous design | Read the compiler error above Home; the last valid design is retained intentionally |
| Unsupported selector/property/layout | Follow the exported contract; use a trusted preset and the candidate's exact supported scales |
| Preview is a colored dot | Replace the scaffold's 1×1 PNG and declare its real dimensions |
| Image size/dimensions rejected | Resize/recompress externally, update declared format/dimensions, then validate again |
| Screenshot output/port exists | Stop the other preview; choose a new output directory or port |
| Build says source is dirty | Commit all files inside the theme source folder, then obtain the actual full HEAD |
| Source identity/version mismatch | Check the ID's repository, descriptor metadata and pinned source URL; do not manually alter generated bytes |
| Remote hash/source check fails | Ensure B is pushed publicly with every referenced file; preserve exact bytes and use raw.githubusercontent.com at the full commit |
| Draft appears to approve itself | Dates/evidence are proposals; only maintainer-reviewed merge approves that digest |
| Theme missing from TV Showcase | Check publication, availability and compatibility; installed IDs are intentionally hidden |
| Send to TV fails | TV receiver pane open, TV address/PIN entered on PC, same private network, TV TCP 8879 reachable, no guest isolation; update Home and its service together |
| Saving on PC does not update TV | Reopen the TV receiver for a new PIN, send a fresh snapshot from PC and apply it again |
| Remove is refused | Apply another installed/built-in theme before removing the active package |
| Old TV Home has no Appearance theme cards | Install the supported theme-enabled candidate when released; a theme URL cannot upgrade the engine |

For unresolved authoring problems, include the theme ID/version, toolkit/runtime
revisions, exact command, redacted error and a minimal public source reproduction.
Keep device credentials, private paths, network details and unrelated app data out
of issues and PRs.


## Keyless release installation links

The matching author toolkit provides **TV link**, **Copy ID** and **Copy link**.
It checks a public commit-pinned descriptor against the selected ID/version before
sending its URL to da.gd. Only published public URLs are sent to the shortener.
The generated short link is looked up again to verify its destination. Shortener
failures retain the full URL, with no repeated rate-limit retries.

Run `theme release-workflow` from your theme repository using the trusted toolkit
to generate a pinned GitHub Actions workflow. Commit it to your default branch,
commit/push versioned distributions, then publish a `vX.Y.Z` GitHub release at
that distribution commit. The workflow selects matching theme versions, generates
`tv-links.json` and adds a theme/ID table while preserving current release notes.
It needs no shortening-service secret; the standard job token updates only the
author's release. Theme files are read as data, not executed. The preview can
retrieve the matching release's metadata, or accept its full published descriptor
URL manually. This does not submit anything to Showcase.
