# Product website

Astro generates the GitHub Pages product website as static HTML. Its dependencies
and TypeScript configuration are isolated here: they do not change the TV build
or require a client UI framework. The existing Python preview export is composed
under `demo/` without changing its standalone development server.

## Develop

From the repository root, install the existing build dependencies first:

```sh
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/build-requirements.txt
npm ci --prefix website
```

The demo exporter prepares pinned Chinese font subsets; the first build needs
network access for the existing verified source-font cache. Do not install these
host build tools on a television.

```sh
PYTHON="$PWD/.venv/bin/python" npm run build --prefix website
npm run dev --prefix website
```

Open the dev server URL with `/clean-your-tv-lg-webos/` appended. Product page
edits reload during development. To refresh copied screenshots, brand assets or
the launcher demo, rerun the build (or `node website/scripts/prepare.mjs`) from the
repository root, then restart the dev server if its public files were cached.
Generated `public/`, `.astro/` and `dist/` contents are ignored.

```sh
npm run check --prefix website
npm run test --prefix website
npm run test:browser --prefix website
npm run test:dev --prefix website
npm run format --prefix website
```

The static verifier runs automatically after each build. It checks all 78
localized pages for one H1, descriptions, canonical URLs, reciprocal language
alternates, page-preserving language links, sitemap inclusion and exported local
links/anchors, including same-page help links and existing source-reference files.
The translation verifier recursively checks nested keys and array lengths. Browser acceptance uses the root project's Playwright, verifies
all pages without JavaScript, keyboard language switching, selected mobile
layouts, browser-language selection, remembered manual preferences, explicit locale
URLs, blocked storage and the offline Root/No-root demo. Use `BROWSER_CHANNEL=chromium` for
Playwright's bundled browser or the default installed Chrome. Set
`WEBSITE_SCREENSHOTS=/absolute/output/directory` to retain QA images.

## Content and translations

- `src/lib/locales.json`: all product text and navigation in the thirteen complete
  installation-guide languages. Keep all keys translated; the build rejects
  missing keys and empty strings. Keep technical names such as Developer Mode,
  Root and No-root recognizable. Do not infer installer/TV language support from
  the website's locale list.
- `src/lib/support.json`: translated quick-start steps, edition comparison,
  compatibility checks and five help topics. `support.ts` validates nonempty
  fixed-size arrays/tuples using Astro's existing Zod export before generation.
  Review these summaries against `docs/INSTALL.md`, `docs/EDITIONS.md`,
  `docs/COMPATIBILITY.md`, `docs/RECOVERY.md` and `docs/MAINTENANCE.md` whenever
  requirements or procedures change. Do not copy device reports into this file.
- `src/lib/site.ts`: shared locale, section and URL definitions.
- `src/layouts/Site.astro`: common navigation and social/search metadata.
- `src/pages/[lang]/`: localized static routes and guide rendering.
- `../docs/i18n/*.md`: the single source for installation guides. These are loaded
  by the content collection; do not copy instructions into the website.
- `astro.config.mjs`: rewrites relative Markdown links during rendering. Other
  localized guides link to the corresponding website install route. Remaining
  references point to the public repository's `main` documentation. Original
  Markdown files are unchanged.

Czech is a complete installation-guide and website locale. Register new locales
in both catalogs, Astro configuration and the static/browser acceptance registries.
The five source-guide download buttons are copied from `assets/brand/downloads/`
to generated `assets/downloads/`; Markdown images use those local website URLs,
while their download links continue to target published release assets.

Installation pages render the source guide directly, without a candidate notice
or release-version preamble. Keep setup guides focused on installation; technical
release documentation records publication boundaries and candidate evidence.
Public download actions use
`releases/latest`. Do not present candidate features as already published or
expand hardware compatibility beyond documented version-specific results. Newly
written website translations have automated/browser checks, not native-speaker
acceptance. The compatibility page includes localized access/runtime requirements and an owner
checklist. A short user-confirmed model list reads `../docs/compatibility-reports.json`;
only records explicitly marked `showOnWebsite: true` appear. It displays models,
editions and known versions; source links, dates and diagnostic details remain
in the audit record. Results apply to their recorded versions, not every device
in a model family. No private diagnostics are copied into website content.

## URLs and publication

The configured public base is
`https://razdva122.github.io/clean-your-tv-lg-webos/`. Each language has six pages:
home, installation, edition comparison, compatibility, themes and help. The root URL
renders English without JavaScript and canonicalizes to `/en/`. With JavaScript,
only this language-neutral entry redirects to the saved manual language choice,
then the first supported browser language, or English if none match. Regional tags
map to supported translations, including Portuguese and both Chinese scripts.
The redirect preserves query parameters and fragments. Each page has its own canonical and
reciprocal `hreflang` links; `x-default` points to the corresponding English page.
Languages switch through ordinary links. With JavaScript, selecting a language
stores only its locale code in `localStorage` under `cytv-website-language` for
future visits to the root URL. Explicit language URLs always retain their language
and do not overwrite this preference. Blocked storage leaves language links and
browser detection usable; without JavaScript, links still work without persistence.

Old root `#root` and `#no-root` links forward to the corresponding demo mode.
Ordinary demo links in README now target `demo/`. Demo internals are marked
`noindex` and excluded from sitemap; their assets remain crawlable. The custom
404 page returns users to all language home pages.

The existing Preview Pages workflow now installs and builds this project,
checks types, verifies export/navigation/layout/demo and uploads `website/dist`.
Pull requests validate without deployment. Only the latest `main` commit can
publish using the existing GitHub Pages environment; feature PRs target
`release/next`. Website, localized-guide and used brand/screenshot changes select
preview checks. This work does not merge a release or alter its frozen scope.

## Search Console setup (site owner)

After normal publication, add the URL-prefix property for the exact public base
in Google Search Console. Verify ownership with the HTML file or meta token
Google supplies, then submit `sitemap.xml` and inspect representative home and
guide URLs. No token or connected Search Console account was supplied for this
change, so ownership, indexation and organic traffic are not claimed verified.

A project-site `robots.txt` below `/clean-your-tv-lg-webos/` would not control the
host. The current absence of a root `robots.txt` does not prohibit crawling.
Submit sitemap directly through Search Console; do not add a misleading nested
robots file. No analytics collector, consent cookie or external font service is
added. For a future domain change, update base/site, canonical generation, sitemap,
asset paths and their tests together.

## Help content and scope

Each `/{lang}/help/` page has stable fragments: `#connection`, `#developer-mode`,
`#home-button`, `#interrupted` and `#update-remove`. Keep them stable for support
links. The page and language navigation work without JavaScript. Help summarizes
existing instructions and links the full English references; it does not promise
that candidate recovery actions are available in every published installer.

Quick-start steps link to edition selection and the existing installation guide.
Edition comparison uses captioned tables with row/column headers. Requirements
are prerequisites, not device certification. The reference Node/Python floors
remain the documented released requirements; source prototypes do not lower them.

This preparation adds no analytics collector, account connection or PR-preview
hosting service. Publishing and Search Console configuration remain separate
release/owner actions.

## Local demo routing regression

Astro dev serves public files directly, but does not resolve a public directory
index at `/demo/` the same way GitHub Pages does. The `demo-directory-index` Vite
middleware rewrites that local request to the existing `/demo/index.html` file
while preserving the public URL and fragment/relative resource behavior. It runs
only in the development server; it is not a production server or redirect.

`test:dev` starts an isolated real Astro dev server on a free loopback port,
checks `/demo/` returns 200, exercises both launcher editions and inline themes,
then stops the owned server. This complements the static export/browser test
which resolves directory indexes itself.

## Visual design

The product site uses a graphite palette, restrained warm ambient gradients,
a floating translucent header, pill controls and rounded product imagery inspired
by https://plxnative.com/. The centered home-page introduction leads into the
existing launcher demo. Shared tokens and CSS apply the same visual language to
all locales and guides; screenshots, installation content and destinations stay
project-owned. The header and language/menu controls work without JavaScript;
its background remains readable without backdrop-filter support.

The interactive demo uses matching graphite surfaces, rounded edition and remote
controls, outlined theme previews and a framed TV viewport. Its shared source is
`../preview/index.html`; the preview renderer, input controls and theme loader
remain the same in local development and the exported website.

The demo theme selector has independent Video and 4K filter toggles. Enabling
both shows their intersection; disabling both shows the complete catalogue.
Filters use exported `hasVideo`/`has4k` metadata, preserve the selected theme and
remain active across edition switches within the current page session. An empty
result explains that no themes match; toggle the filters off to restore cards.
Filtering does not fetch or install theme packages.
