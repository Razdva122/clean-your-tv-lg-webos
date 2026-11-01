# Multilingual Pages implementation plan

Goal: Build the agreed product website and installation guides in all twelve complete guide languages using Astro, TypeScript, Markdown and plain CSS. Keep website dependencies isolated from TV tooling. Target release/next; no merge or publication.

## Design and constraints

Use the approved B1 house mark, warm charcoal #241D19, cream #FFF8EB and restrained orange #FF4C20. Lead with the real launcher image and clear installation/demo actions. Responsive readable articles, accessible language navigation and visible focus. No UI framework, runtime server, CMS or analytics collector.

Use /en/, /de/, /es/, /pt-BR/, /fr/, /it/, /ko/, /hi/, /pl/, /ru/, /zh-Hans/, /zh-Hant/ with translated home, edition, compatibility and theme content, plus installation Markdown reused from docs/i18n. Czech is currently candidate-only TV-interface documentation, not a complete installation guide. Preserve explicit unreleased notices and technical identifiers. Do not promise universal compatibility or system-wide ad removal. Language links preserve the current page and never force browser-language redirects. Sitemap contains canonical public content with reciprocal hreflang. Root is an English landing page with x-default; preserve old #root/#no-root demo links.

Reuse the Python preview export beneath /demo/ unchanged, with its own assets. Rewrite Markdown relative links to existing repository sources or corresponding translated website guides; keep heading anchors. Do not expose workspace files. Published release and candidate documentation remain explicitly distinguished. Do not change TV controls or release scope.

## Tasks

- [ ] Add failing static-export tests for localized routes, HTML metadata, reciprocal alternates, local links and demo preservation; observe failure.
- [ ] Implement the isolated Astro project, shared layout, translated copy and Markdown collection.
- [ ] Compose demo and approved site assets, retaining old fragment deep links.
- [ ] Add responsive browser checks and inspect actual screenshots.
- [ ] Integrate dependency install/build/check into Pages CI and path scoping.
- [ ] Document development, translations, deployment and owner Search Console setup.
- [ ] Run affected preview/scope/website checks, push and open/update a draft PR with actual verification.

Acceptance: All localized HTML is readable without JS, with language-appropriate title/description/H1 and canonical; language switching preserves page; sitemap and links resolve beneath project base; no mobile overflow or browser errors; unchanged demo supports both editions and inline themes offline. Search Console requires an owner token and is not claimed configured.
