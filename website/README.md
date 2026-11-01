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
npm run format --prefix website
```

The static verifier runs automatically after each build. It checks all 60
localized pages for one H1, descriptions, canonical URLs, reciprocal language
alternates, page-preserving language links, sitemap inclusion and exported local
links/anchors. Browser acceptance uses the root project's Playwright, verifies
all pages without JavaScript, keyboard language switching, selected mobile
layouts and the offline Root/No-root demo. Use `BROWSER_CHANNEL=chromium` for
Playwright's bundled browser or the default installed Chrome. Set
`WEBSITE_SCREENSHOTS=/absolute/output/directory` to retain QA images.

## Content and translations

- `src/lib/locales.json`: all product text and navigation in the twelve complete
  installation-guide languages. Keep all keys translated; the build rejects
  missing keys and empty strings. Keep technical names such as Developer Mode,
  Root and No-root recognizable. Do not infer installer/TV language support from
  the website's locale list.
- `src/lib/site.ts`: shared locale, section and URL definitions.
- `src/layouts/Site.astro`: common navigation and social/search metadata.
- `src/pages/[lang]/`: localized static routes and guide rendering.
- `../docs/i18n/*.md`: the single source for installation guides. These are loaded
  by the content collection; do not copy instructions into the website.
- `astro.config.mjs`: rewrites relative Markdown links during rendering. Other
  localized guides link to the corresponding website install route. Remaining
  references point to the public repository's `main` documentation. Original
  Markdown files are unchanged.

The Czech source document currently describes candidate TV localization and
points to the English installation guide; it is intentionally excluded from the
twelve complete installation translations. When a complete guide is available,
add translated product copy, register it in the Astro locale configuration and
update the acceptance locale registry before publishing its routes.

Source guides retain explicit candidate/unreleased notices, and every installation
page explains that distinction before its content. Public download actions use
`releases/latest`. Do not present candidate features as already published or
expand hardware compatibility beyond documented version-specific results. Newly
written website translations have automated/browser checks, not native-speaker
acceptance. The compact compatibility page links to the maintained detailed
English device-test record rather than duplicating a table that could go stale.

## URLs and publication

The configured public base is
`https://razdva122.github.io/clean-your-tv-lg-webos/`. Each language has five pages:
home, installation, edition comparison, compatibility and themes. The root URL
mirrors English and canonicalizes to `/en/`. Each page has its own canonical and
reciprocal `hreflang` links; `x-default` points to the corresponding English page.
Languages switch through ordinary links without forced locale redirects.

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
