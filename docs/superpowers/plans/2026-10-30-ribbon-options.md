# Ribbon Options Implementation Plan

> **For agentic workers:** Use subagent-driven-development to execute the isolated file groups, then request whole-branch review.

**Goal:** Ship bounded scenic-ribbon parameters and the corresponding author-toolkit example through two implementation PRs.

**Architecture:** Keep one existing scenic renderer. Author manifests supply data-only ribbon parameters; the trusted Home engine validates geometry and emits bounded styling and navigation. The separate toolkit consumes an explicitly exported matching runtime.

**Tech Stack:** Existing browser ES5-compatible JavaScript, Node.js compiler/toolkit, Playwright and Python build/export scripts. No new dependencies.

**Spec:** ../specs/2026-10-30-ribbon-options-design.md

## Global constraints

No release/component version changes; target release/next. No arbitrary author scripts/styles, theme-name/brand conditions, native Home handling changes or physical-TV claims. Absent ribbon options preserve existing themes. New manifests require ribbon-layout-v1. Preserve existing runtime lock until reviewed provenance is available.

### Task 1: Contract and geometry

Files: launcher/theme-policy.js, launcher/home-layout.js, theme-api/contract.json, theme-api/compile.cjs, tests/themes/ribbon-options.cjs, package.json.

- [x] Add failing option/capability/compiler/default/atomicity tests; run `node tests/themes/ribbon-options.cjs` and confirm rejection before implementation.
- [x] Implement optional layout.ribbon and bounded geometry per spec; automatically emit capability.
- [x] Expose normalized ribbon in HomeLayoutState.state(), supportsRibbonOptions, and geometry's third argument. Coordinate exact helpers with Task2.
- [x] Register/run unit tests and existing compiler/layout/policy regressions.

### Task 2: Trusted rendering and navigation

Files: launcher/app.js, launcher/theme-runtime.js, launcher/style.css, tests/themes/ribbon-options-ui.cjs.

- [x] Add failing browser tests for both editions and approved example plus a different numeric configuration.
- [x] Thread normalized state into geometry and generate scoped budgeted CSS for ribbon card/caption/shortcut/clock layout.
- [x] Add the optional shortcut boundary route and on-screen input popup placement; leave native Home/keyup paths unchanged.
- [x] Verify reset/suspension, pointer/wheel, selected bounds and reorder with `node tests/themes/ribbon-options-ui.cjs`; run existing ribbon and isolation tests.

### Task 3: Toolkit

Files in separate toolkit: lib/toolkit.cjs, examples/ribbon/, tests/ribbon.cjs, docs/authoring.md, docs/runtime.md, docs/compatibility.md, tutorial links.

- [x] Test old explicit runtime refusal and new contract preservation.
- [x] Add runtime contract preflight and postcompile preservation guard.
- [x] Add a data-only Ribbon example from the original procedural wallpaper/real runtime capture. Do not include prototype geometry CSS or publish a fake install URL.
- [ ] Export main PR candidate and run full toolkit suite against the explicit runtime. Preserve runtime.lock.json.

### Task 4: Integration, legacy behavior and delivery

- [x] Document full numeric contract, developer walkthrough, user capability rejection and shortcut behavior in all12 localized guides. Clearly mark unreleased support.
- [x] Exercise actual pre-change policy/data/manager for LAN and URL installs; assert current choice/visual unchanged and zero cache writes.
- [ ] Run `bash scripts/test.sh`, appropriate browser regressions and toolkit `npm test`; fix scoped failures and disclose unrelated blockers.
- [x] Request independent code review of both complete diffs; resolve material findings and rerun affected checks.
- [ ] Commit sources separately, push feature branches, open and attach paired PRs targeting release/next, cross-link dependencies and verified tests.
- [ ] Keep review artifacts outside temporary worktrees; remove/archive worktrees after changes are committed and pushed. Report PR links, exact old-TV outcome and any untested TV behavior.
