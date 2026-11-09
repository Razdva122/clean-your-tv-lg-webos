# Community theme showcase (candidate)

The static showcase is part of the next theme candidate, after 1.4.1. URL installation and the Themes picker are implemented in the preparation branch;
published packages may not contain them yet. Classic, Ribbon and Liquid Glass are app-bundled choices.
Channel and Itachi were early themes and are retired from the current catalogue.
Their registry records, including the older main-repository Itachi identity,
remain marked `availability: "removed"` for history. They are not offered by the
TV catalogue or browser theme picker; already installed copies are not removed.
Keep their entries in `order.json` so retiring them does not reorder other themes.
Descriptor URLs remain commit-pinned and hashes remain authoritative. The historical
external Alpine 1.4.2 record is archived. Alpine 1.4.4 is maintained under
`themes/alpine/` for the current Showcase distribution; its existing appearance,
assets and license notices are preserved. An old `builtin:alpine` preference
restores Classic with the normal recovery notice and does not download or select
a replacement automatically. Reinstall Alpine explicitly from its reviewed
Showcase listing when that source distribution is available.
There are no votes, popularity counts or automatic built-in promotions.

Use the simple author path below to suggest a theme. The [author walkthrough](../docs/development/CONTRIBUTING-THEMES.md) is optional for creating and packaging themes yourself. The rest of this page defines maintainer integration and review.

## Suggest a theme: author path

[Open a theme suggestion](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new?template=theme-submission.yml)
with a theme name, a public link to its source or package, and its license/asset
permissions. A normal issue or a PR with the same information is also welcome.
A repository link is enough to start; maintainers can help prepare the fixed
package and catalogue entry. A screenshot and known limitations are optional.

Authors do not need to fork this repository, prepare registry JSON, generate the
TV catalogue, install Playwright, run repository tests, write a review report or
test on a physical TV to request inclusion. Maintainers own those review and
integration steps. Suggestions are evaluated by maintainers; submission does not
automatically approve or publish a theme.

The sections below describe the maintainer integration contract. Authors who
prefer to prepare a complete PR may use it, but it is not an admission requirement.

## Submit one fixed theme version

This is the maintainer integration path.

Use the pinned author toolkit in `clean-your-tv-lg-theme` to validate/build your
CSS and assets. The main project's `theme-api/compile.cjs` and shared
`launcher/theme-policy.js` define the API; author JavaScript and HTML are never
part of a theme. Authors may keep several themes in one repository; submit one
record per stable `github:owner/repository:slug` ID. Approval of a collection does
not approve its other themes or future versions.

Maintainers prepare or finish a PR targeting `release/next` containing:

- `showcase/registry/owner--repository--slug.json`, matching `schema.json`.
- `showcase/assets/owner--repository--slug/<descriptorSha256>/cytv-theme.json`
  and every manifest-relative rules, image, license and credits file.
- One to four reviewed previews named in `previewFiles`, each also a hashed
  manifest image (960×540 and 300 KiB maximum). Do not submit personal screenshots,
  raw diagnostics, addresses, private paths, tokens or device backups.

`sourceCommit` is the exact 40-character source revision in the manifest.
`descriptorUrl` must point to this theme's specific `cytv-theme.json` on
`raw.githubusercontent.com`, at an exact 40-character distribution commit in the
same public repository. Source and distribution commits can differ: generated
files are normally committed after the source build. Moving branches, collections,
credentials, redirects, query strings and arbitrary hosts are rejected. The
SHA-256 binds the descriptor bytes; all referenced files have their own hashes.
Copy TV link always copies that specific pinned descriptor, never the collection.

Names/descriptions are bounded plain text. Profiles must match the repository
owner and the manifest. Tags are `dark`, `light`, `minimal`, `colorful`,
`photographic`, `high-contrast`. Supported license identifiers are `MIT`,
`Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `CC0-1.0`, `CC-BY-4.0`,
`CC-BY-SA-4.0`, and the specifically reviewed composite
`MIT AND CC-BY-SA-3.0` used by Alpine (MIT styling and CC BY-SA 3.0 wallpaper).
This is an exact allowlisted value, not a general SPDX-expression parser. Individual asset permissions still need review. Public license and
credits files use `.txt`; images use their actual PNG/JPEG/WebP extension. The exact `LicenseRef-Personal-Fan-Theme` value is additionally reviewed for Itachi: MIT CSS, generated wallpaper for personal non-commercial fan use with its notice retained; underlying character rights are not granted. It is not an open-source character license or a commercial-use grant. Other
licenses require a reviewed policy change, not a misleading identifier.

Dates use `YYYY-MM-DD`. Maintainers assign `addedAt` and `reviewedAt`; drafts can
propose dates but cannot approve themselves. Maintainers record actual `browser` or `device`
evidence with a concise public summary and optional repository issue/PR link.
The final registry requires review evidence; the initial author suggestion does
not. Never label an untested draft as a completed browser or device check.
Browser evidence does not establish TV compatibility. Device reports follow
`AGENTS.md` consent/redaction requirements and distinguish known model, firmware,
remote, edition, versions, tests, expected/actual results and untested fields.

## Checks and maintainer review

Run from the main project checkout after `npm ci`:

```sh
node scripts/check-theme-submissions.cjs
node scripts/check-theme-submissions.cjs --remote
node tests/showcase/registry.cjs
node tests/showcase/submission-security.cjs
node tests/showcase/remote.cjs
BROWSER_CHANNEL=chromium node tests/preview-themes-ui.cjs
python3 scripts/preview.py --build build/theme-preview-review
```

Local validation rejects metadata/source mismatches, duplicate identities, path
escapes, symlinks, unsupported rules/API, wrong byte lengths/hashes and unsafe
public file types. `--remote` additionally checks every pinned public source byte
against the reviewed hashes, with redirects disabled, omitted credentials,
15-second request limits and a 16 MiB total download budget per run. Larger
catalogs will need reviewed job sharding rather than an unbounded fetch loop. It never runs author
install scripts, commands, plugins or workflows. Only validated theme data and
allowlisted preview resources are exported; unrelated workspace content is excluded.

`.github/workflows/theme-submissions.yml` runs untrusted submission checks in a
read-only `pull_request` job without publishing secrets, retained checkout
credentials or dependency lifecycle scripts. It limits Node memory, job time and
remote-check time, then uploads an inspection artifact. Deployment remains a
separate trusted main job. A manual run may disable live remote checks, but PR
checks always verify pinned public bytes. Maintainers
must verify author control through matching committed repository content or
explicit permission for third-party work. Matching profile text alone does not
prove ownership, and attribution is not redistribution permission.

Before approval, maintainers use the trusted preview runtime with validated theme
data, synthetic apps and external network blocked. Check Home focus/navigation,
app library labels, Inputs and standard Settings isolation. Record the checked
version, actual results and untested paths in a short PR comment or description,
then put a concise summary in the final registry evidence. Check that the listed
preview represents that version. Save screenshots when they help explain a
problem or design decision; a separate screenshot set, policy/resource report or
review document is not mandatory. Automated validation still enforces the
allowed selectors, resource limits and hashes. Authors may share their own
observations, but maintainers own acceptance and must not demand a report or
physical-TV testing as the price of submitting a theme. Browser checks do not
certify device compatibility.

Review outcomes are needs changes, approved fixed version, unavailable source or
removed listing. Approval is represented by the reviewed merge and fixed digest;
there is no author-controlled `approved` flag. Request changes with actionable
validation output. Reject disputed ownership or unlicensed assets. Appeals go
through the submission PR with evidence; do not create duplicate issue reports.
Check and maintain applicable issue statuses under `AGENTS.md` independently.

For an update, keep the same ID and `addedAt`, submit a new digest directory,
replace the record's version/source/preview metadata and obtain a new review.
The former digest is not permission for new bytes. A source that disappears or
fails pinned-byte verification must not keep an install CTA: maintainers set
optional `availability: "unavailable"` through review. Unavailable entries are not
offered for installation in the on-TV catalogue.
For removal, set `availability: "removed"`: the record leaves the catalogue
and its image/distribution bytes are omitted from preview exports.
Moderated records retain local review evidence but skip live remote checks. Do not fabricate compatibility or silently substitute a new source.

## Browser preview and local catalogue review

The public site uses the [primary browser preview](https://razdva122.github.io/clean-your-tv-lg-webos/)
with inline theme cards. It does not publish a separate `/themes/` catalogue or
theme detail pages. `scripts/preview.py --build OUTPUT` exports the main preview,
both editions, theme data and the existing launcher/preview paths into fresh staging.

The standalone Showcase HTML builder, pages, filters and page-only assets have
been removed. Local maintainer review and PR inspection artifacts use this same
inline theme preview. The on-TV Showcase continues to use the reviewed registry
and catalogue JSON.

Publication follows registry PR → `release/next` → normal main release → existing
Pages deployment with its current-main check. PR inspection artifacts must not
deploy. Verify the deployed site before claiming public availability; a local
build does not publish it.

## Preview cards

The local author-tool picker uses `src/theme-card.css`, exported through the
theme runtime. This shared component is retained for author tooling; it does not
build a standalone catalogue page. A card uses an actual 16:9 Home capture, a
visible theme name and an `aria-pressed` selection marker. The main browser
preview offers its inline theme switcher above Home. Its initial JSON contains only
catalogue metadata and package URLs; reviewed external theme envelopes are fetched
on a preview click and reused for the rest of the page session, including edition
switches. A failed download can be retried by clicking the preview again. Classic reference captures
and credits remain in `assets/classic-preview.png` and adjacent provenance files.
Browser previews are not hardware acceptance evidence.

### Preview metadata (next candidate)

Cards show the complete declared package size in decimal MB, including the
manifest, rules, images, notices and both video variants. Classic is app-native
and retains its Built-in label instead of an invented standalone package size.
A 4K badge means the package has a 3840×2160 video variant for UHD output; a UHD
JPEG alone is insufficient. It does not promise native source detail or that
any particular television has accepted UHD playback.

The film icon means a moving background. `moving-wallpapers.json` lists the
SHA-256 hashes of reviewed moving video bytes, not theme names or mutable URLs.
Alpine and Crăciun use still MP4 loops and do not receive it. Unknown motion is
not advertised. Installed cards reuse reviewed motion metadata only when their
exact descriptor digest matches the catalogue; arbitrary installed packages
remain usable. Metadata adds no remote focus targets and has accessible labels.

Crăciun 1.2.0 is maintained in `themes/craciun/` under the main-project identity,
with the original author's styling, appearance and attribution retained. The
historical author listing is removed from new catalogue offers, not rewritten.
Existing cached author installations keep their identity and selection. The
new package adds silent UHD/FHD still loops and keeps the original JPEG
fallback. Its source image remains an AI-generated Real-ESRGAN upscale.

### Catalogue order

Built-in themes stay first. `showcase/order.json` preserves the existing order
of community themes for the TV catalogue and primary interactive preview.
New registry entries absent from that list appear after its entries, with
filename order as a deterministic fallback. When integrating a new theme,
maintainers append its ID to the end of this list so later submissions cannot
move it. Updates keep the same position; removed/unavailable entries remain
hidden under the existing moderation rules. Authors do not need to edit this file.

### On-TV catalogue snapshot

After approving or changing a registry entry, run `node scripts/build-tv-theme-catalog.cjs`
and commit the generated launcher catalogue, previews, notices and inventory together.
`node scripts/build-tv-theme-catalog.cjs --check` verifies freshness. Home Settings →
Appearance → Theme showcase uses this offline snapshot; external downloads retain the
reviewed commit-pinned source. Removed/unavailable records are not installable cards.
This does not publish a Home package or refresh installed TVs before the normal release.

## Weather integration

See the [shared weather contract](../docs/development/WEATHER.md) for supported formats, developer styling, preset reservations, compatibility and maintainer fork provenance. Home owns weather data and settings; themes contain no provider code.
