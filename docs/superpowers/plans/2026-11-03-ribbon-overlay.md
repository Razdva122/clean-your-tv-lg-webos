# Ribbon overlay implementation plan

> Execute with subagent-driven-development; focused task reviews and a final whole-branch review.

**Goal:** Root Ribbon over active content, full wallpaper fallback, coherent shared style/demo, and a reviewable PR.
**Architecture:** Existing Root overlay host plus bounded presentation controller and sanitized read-only context; shared theme renderer.
**Tech stack:** Existing ES5/Babel/PostCSS, webOS Luna service, Python runtime, Playwright.
**Spec:** ../specs/2026-11-03-ribbon-overlay.md

## Global constraints
No-root native behavior unchanged; preserve triple-Home emergency, startup/input ownership, key-up and updater. No release bump/merge. No publication of private prototype observations.

- [ ] Task 1: Root platform context and manifest. Add failing context/observer tests; implement read-only context and prevent overlay-induced startup-source changes.
- [ ] Task 2: Presentation/theme contract and app integration. Add failing state tests; implement generic opt-in, full fallback, modal/launch/Back/relaunch ownership.
- [ ] Task 3: Ribbon visual pass, actual-renderer demo states and preview assets. Verify contrast/focus and both editions; regenerate bundled sources with correct committed provenance.
- [ ] Task 4: Documentation/localizations, affected checks and independent review. Fix findings, push feature branch, create PR to release/next; do not merge. Archive own temporary worktree after preserving source/artifacts.

Ruling: user explicitly approved design behavior then requested design+implementation+MR; continue without another design permission cycle. Root-only scope separately confirmed.
