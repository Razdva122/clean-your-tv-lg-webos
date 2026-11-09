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
`https://razdva122.github.io/clean-your-tv-lg-webos/`. Each language has six core pages:
home, installation, edition comparison, compatibility, themes and help, plus an
article index and four full articles. The root URL
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

## Articles and search visibility

`src/content/articles/{locale}/{topic}.md` holds four practical articles in each
of the 13 supported locales. They explain changing the home screen, the limits
of avoiding home-screen ads, choosing Root or No-root and maintaining Developer
Mode. These are editorial guides, separate from `docs/i18n/` installation sources;
they link the current installation, compatibility and recovery instructions.
Keep prerequisite and control claims aligned with those references. Do not
announce candidate features as published or turn a reported TV configuration
into a compatibility guarantee.

The content collection validates language, topic, title, description and ISO
update date. Build-time validation requires exactly one translation per topic
and supported locale. `src/lib/article-copy/*.json` supplies the small localized
navigation/metadata vocabulary; `src/lib/site.ts` defines the topic registry.
Article URLs use stable topic slugs under `/{locale}/articles/{topic}/`.
Use absolute website paths for internal article links: relative Markdown URLs
are reserved for the existing GitHub documentation-link renderer.

The header, footer, home-page article links, index and related links expose the
articles without JavaScript. Canonicals and reciprocal `hreflang` links retain
the selected topic, including when switching language. The sitemap includes
all article/index URLs and translation links; article `lastmod` comes from the
reviewed `updated` field, never from build time. Update that field when the
article changes, not during every deployment.

Pages emit `WebSite` and `WebPage` JSON-LD. Article pages add `Article` and
`BreadcrumbList` with the visible title, description, language, project attribution,
breadcrumbs and update date. No publication date, ratings or hardware certification
are invented. Existing pages retain their URLs, metadata and installation anchors.
`verify-articles.mjs` checks the exported pages, metadata/schema agreement, sitemap,
translation destinations and local links. Browser acceptance covers every new
route without JavaScript and checks desktop/mobile overflow and navigation.

The AI-search approach follows [Google's AI search guidance](https://developers.google.com/search/docs/appearance/ai-features):
crawlable text, direct useful answers, source links, internal discovery and
structured data matching visible content. AI-specific text files and special
schema are not required by Google. No visibility, citation, indexing or traffic
gain is claimed from local checks. After publication, the site owner can submit
the sitemap and inspect representative pages in Search Console and Bing Webmaster
Tools. Host-level crawler rules must be managed at the domain root; this project
does not change them or connect analytics accounts.

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

The product site retains the original logo, graphite palette and orange brand
accent. The home page leads with a real Liquid Glass demo screenshot beside the
introduction, then a theme gallery, edition prerequisites, installation steps and
editorial links. A solid header, restrained control/screen radii, system typography
and shorter section spacing replace the translucent pill shell, decorative
gradients and repeated framed text cards. No generated hardware images, invented
customer evidence or new front-end dependencies are used.

`home.css` owns the product-page composition. `editorial.css` provides a narrower
reading measure, a desktop margin index and a native collapsed mobile contents
menu for articles. The article index features a real product screenshot and
linked summaries. Existing localized installation guides keep their original
content and anchors in `article.css`; shared header, footer and tokens cover all
locales. Header, language and article contents navigation work without JavaScript.
The Astro development toolbar is disabled so local design previews show only
the site's own interface.

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
