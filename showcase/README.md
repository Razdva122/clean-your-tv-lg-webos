# Community theme showcase (candidate)

The static showcase is part of the next theme candidate, after 1.4.1. URL installation and the Themes picker are implemented in the preparation branch;
published packages may not contain them yet. Classic and Alpine are app-bundled choices. Channel is the initial external
listing, pinned to its separately committed toolkit distribution. Channel 1.3.3 is fixed by toolkit tag `v1.3.3`; Itachi 1.0.2 uses the existing toolkit tag `v1.0.2`. Descriptor URLs remain commit-pinned and hashes remain authoritative. The older main-repository Itachi identity is retained as a removed historical listing. The historical
external Alpine record is archived; it is not an additional download.
There are no votes, popularity counts or automatic built-in promotions.

Start with the [complete author contribution walkthrough](../docs/development/CONTRIBUTING-THEMES.md) for setup, live PC preview, LAN testing, source/distribution commits and a step-by-step PR submission. This page is the registry and maintainer-review reference.

## Submit one fixed theme version

Use the pinned author toolkit in `clean-your-tv-lg-theme` to validate/build your
CSS and assets. The main project's `theme-api/compile.cjs` and shared
`launcher/theme-policy.js` define the API; author JavaScript and HTML are never
part of a theme. Authors may keep several themes in one repository; submit one
record per stable `github:owner/repository:slug` ID. Approval of a collection does
not approve its other themes or future versions.

Submit a PR targeting `release/next` containing:

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
propose dates but cannot approve themselves. Include `browser` or `device`
evidence with a concise public summary and optional repository issue/PR link.
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
node tests/showcase/site.cjs
node tests/showcase/browser.cjs
node scripts/build-showcase.cjs build/site/themes
```

Local validation rejects metadata/source mismatches, duplicate identities, path
escapes, symlinks, unsupported rules/API, wrong byte lengths/hashes and unsafe
public file types. `--remote` additionally checks every pinned public source byte
against the reviewed hashes, with redirects disabled, omitted credentials,
15-second request limits and a 16 MiB total download budget per run. Larger
catalogs will need reviewed job sharding rather than an unbounded fetch loop. It never runs author
install scripts, commands, plugins or workflows. Only named manifest files are
copied into the site; unrelated workspace content is excluded.

`.github/workflows/theme-submissions.yml` runs untrusted submission checks in a
read-only `pull_request` job without publishing secrets, retained checkout
credentials or dependency lifecycle scripts. It limits Node memory, job time and
remote-check time, then uploads an inspection artifact. Deployment remains a
separate trusted main job. A manual run may disable live remote checks, but PR
checks always verify pinned public bytes. Maintainers
must verify author control through matching committed repository content or
explicit permission for third-party work. Matching profile text alone does not
prove ownership, and attribution is not redistribution permission.

Before approval, use the trusted preview runtime with validated theme data,
synthetic app inventory/fixed clock and external network blocked. Produce Home,
library, Inputs and standard Settings isolation screenshots plus policy/resource
reports. Compare submitted preview bytes to that exact reviewed version. The
static builder validates/copies review artifacts; it does not generate these
screenshots or certify device acceptance. Initial Alpine/Channel evidence is recorded in [the catalog review](review/initial-themes.md).
These are candidate browser-reviewed versions; the normal PR review/merge is
still required and no physical-TV compatibility is claimed.

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
optional `availability: "unavailable"` through review. Its detail page explains
the unavailable state without a copy/install control. For removal, set
`availability: "removed"`: the record leaves the catalog/search and its stable
page becomes a tombstone; image/distribution bytes are omitted from the site.
Moderated records retain local review evidence but skip live remote checks. Do not fabricate compatibility or silently substitute a new source.

## Browser preview and local catalogue review

The public site uses the [primary browser preview](https://razdva122.github.io/clean-your-tv-lg-webos/)
with inline theme cards. It does not publish a separate `/themes/` catalogue or
theme detail pages. `scripts/preview.py --build OUTPUT` exports the main preview,
both editions, theme data and the existing launcher/preview paths into fresh staging.

`scripts/build-showcase.cjs` and its `buildShowcase(destination, {showcaseRoot})`
export remain available for local author/reviewer inspection. Their HTML output
is not included in the public Pages workflow. The on-TV Showcase uses reviewed
registry/catalogue JSON and is unchanged by removing the separate web page.

Publication follows registry PR → `release/next` → normal main release → existing
Pages deployment with its current-main check. PR inspection artifacts must not
deploy. Verify the deployed site before claiming public availability; a local
build does not publish it.

## Preview cards

Catalog cards and the local author-tool picker share `src/theme-card.css`.
A card uses an actual 16:9 Home capture and a visible theme name. The local
picker adds an `aria-pressed` selection marker; the community catalog keeps its
review metadata and links to the pinned theme detail. An empty registry still produces an honest empty state. Built-in Classic is shown separately using the
synthetic renderer capture in `assets/classic-preview.png`, with credits and
capture provenance alongside it. A built-in preview is not a reviewed installable
community descriptor or a hardware acceptance claim.


### On-TV catalogue snapshot

After approving or changing a registry entry, run `node scripts/build-tv-theme-catalog.cjs`
and commit the generated launcher catalogue, previews, notices and inventory together.
`node scripts/build-tv-theme-catalog.cjs --check` verifies freshness. Home Settings →
Appearance → Theme showcase uses this offline snapshot; external downloads retain the
reviewed commit-pinned source. Removed/unavailable records are not installable cards.
This does not publish a Home package or refresh installed TVs before the normal release.
