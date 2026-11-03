# Wallpapers video layer implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Real video wallpapers with automatic quality selection and Wallpapers settings for the next release.
**Architecture:** Backward-compatible optional media metadata; bounded trusted transport; lifecycle-owned video plane; shared settings pane and existing recovery/profile behavior.
**Tech Stack:** Existing ES5 browser scripts, IndexedDB, native webOS metadata, Node/Python build tests.
**Spec:** docs/superpowers/specs/2026-11-03-wallpapers-video-design.md

## Global constraints

Image-only themes remain valid; video always has a static fallback. No Home routing/emergency changes. No new dependencies, external network services or redistributed Apple assets. Native playback adds one tokenized loopback HTTP cache endpoint and five owner-authenticated Luna methods. No frozen-candidate integration without coordinator admission. Native Blob transport needs explicit physical evidence.

- [ ] Validate physical cached-media path; restore lab after probe.
- [ ] Policy/transport/storage: test first; optional gated variants, header validation, byte/hash bounds, prepare/dispose and receiver budget consistency.
- [ ] Runtime/settings API: actual video, capability detection, bounded preferences, dim, cascade, media release on lifecycle transitions; test actual playback and stale async work.
- [ ] Shared Wallpapers pane and navigation in both editions; localized strings and proper empty/image-only states; tests keyboard/pointer behavior.
- [ ] Connect packaging/preview allowlists, profiles and twelve guides; document theme-author contract.
- [ ] Review all changes; run affected checks and inspect browser UI.
- [ ] Prepare isolated dev TV artifact for owner QA; record actual vs untested results.
- [ ] Save feature work, prepare release/next review without touching frozen inventory, remove temporary worktree when finished.
