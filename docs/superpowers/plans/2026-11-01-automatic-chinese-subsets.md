# Automatic Chinese subsets implementation plan

**Goal:** Translation changes automatically gain static Chinese glyph coverage without enlarging distributed full fonts or editing tracked font binaries.

**Approved design:** A single build-only preparation module collects decoded Chinese locale strings from explicit runtime source roots, checks the retained faces, and creates deterministic weight-400 subsets when coverage changes. Sources come only from the existing pinned Google Fonts commit and recorded SHA-256 digests. A content-keyed atomic cache preserves verified sources and generated fonts for offline reuse. Invalid cache entries fail closed. Build dependencies never enter TV runtime or frozen installer imports.

**Constraints:** Keep Home/Root IDs, versions, Helper and OTA behavior unchanged. Never change tracked font assets during ordinary builds. Preserve OFL licenses and current static-font compatibility. Use the same prepared bytes in packages, standalone installer fonts and live/static previews. Cold-TV rendering remains untested.

- [x] Add failing regressions for decoded locale collection, new glyph preparation, immutable tracked files, offline reuse, deterministic output and cache corruption.
- [x] Implement `scripts/chinese_fonts.py`: `required_characters(root)`, `prepare_fonts(root, cache)` and verified source/cache helpers. Use stdlib cmap parsing for the retained-font fastpath and fonttools 4.60.1 only for regeneration.
- [x] Route `compile_web`, standalone installer fonts, Root preview preparation and live/static preview font serving through the shared module. Centralize package glyph assertions on its collector.
- [x] Add pinned build requirements to all actual build/preview/browser CI paths; retain a thin legacy tool wrapper. Update font provenance and developer setup instructions.
- [x] Run focused font/package/preview regressions and affected compatibility/build checks. Measure generated font sizes and preserve red/green evidence. Commit isolated changes for parent review.


## Verification evidence

The first `python3 -B -m unittest discover -s tests/setup -p test_chinese_preparation.py` failed because the shared preparation module did not exist. The implemented regressions reproduce absent retained `形`/`力` glyphs by injecting a runtime catalog, cover escaped template text and a new compiler-input catalog, and require exact static weight-400 coverage. Tests refuse unsupported full-source glyphs and corrupted source/subset caches, regenerate identical bytes with networking disabled, and confirm tracked fonts remain unchanged.

Passed with the pinned build environment:
- Chinese preparation/package tests: 15 tests.
- Installer asset tests: 9 tests.
- Static Outfit compatibility tests: 2 tests.
- Live/static preview tests: 5 tests, including both SC/TC font URLs for both editions.
- TV development staging tests: 14 tests.
- `npm run test:compat`.
- `scripts/build-cytv.py --payload-only`, including full payload hashes and release-version verification.

Independent review confirmed module/collector/cache behavior, concurrent offline generation, and CI dependency conditions for preview-only and UI-only runs. Actual generated faces are SC 213,636 bytes and TC 178,288 bytes. All six font-bearing IPKs and standalone fonts contain identical prepared bytes. Home FHD is 5,530,090 bytes compressed / 8,753,530 bytes unpacked; Root FHD is 5,399,718 / 8,723,485. Every affected package remains below 32 MiB compressed, 64 MiB unpacked and 16 MiB per member. Generated faces remain below 1 MiB each. No tracked font binary, release version, Helper or OTA code was changed. Physical-TV font rendering/performance remains untested.


## Collector completeness review

An additional failing regression reproduced four omitted input forms: unscoped escaped JavaScript/templates, JSON titles, HTML entities/inline runtime code, and CSS escaped content. These now use the existing Acorn/parse5/PostCSS parsers without evaluating runtime code. Tests distinguish locale metadata from ordinary `id` fields, normalize foreign locale tags and selector spacing, retain shared inline code under an initially English document, and conservatively collect negated/mixed CSS selectors.

The two declared font faces form a cascade in all UI locales, preserving Chinese regional preference while allowing shared `简约` titles and a Traditional Chinese catalog quoting `简书`. Actual font-generation tests verify union coverage. Unsupported glyphs fail only when both pinned originals lack them. Source and subset cache FIFO fixtures are refused immediately without blocking. The complete six-package payload was rebuilt and all 209 hashes, shared font bytes and package bounds rechecked after this change; compatibility tests and lints passed.

The thirteen-language Chromium browser regression passed for both Home editions, including actual custom-font inspection: mixed `简體` uses packaged SC in English and SC fallback plus preferred TC in Traditional Chinese. This is host-browser evidence, not physical-TV rendering/performance acceptance.
