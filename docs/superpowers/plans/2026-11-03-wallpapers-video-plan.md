# Wallpapers video layer implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Real video wallpapers with automatic quality selection and Wallpapers settings for the next release.
**Architecture:** Backward-compatible optional media metadata; bounded trusted transport; lifecycle-owned video plane; shared settings pane and existing recovery/profile behavior.
**Tech Stack:** Existing ES5 browser scripts, IndexedDB, native webOS metadata, Node/Python build tests.
**Spec:** docs/superpowers/specs/2026-11-03-wallpapers-video-design.md

## Global constraints

Image-only themes remain valid; video always has a static fallback. No Home routing/emergency changes. No new dependencies, external network services or redistributed Apple assets. Native playback adds one tokenized loopback HTTP cache endpoint and five owner-authenticated Luna methods. No frozen-candidate integration without coordinator admission. Desktop Blob playback is not evidence of native cached-media playback.

- [x] Validate physical cached-media path in the isolated QA application; retain observations privately, separate from final candidate acceptance.
- [x] Policy/transport/storage: test first; optional gated variants, header validation, byte/hash bounds, prepare/dispose and receiver budget consistency.
- [x] Runtime/settings API: actual video, capability detection, bounded preferences, dim, cascade, media release on lifecycle transitions; test actual playback and stale async work.
- [x] Shared Wallpapers pane and navigation in both editions; localized strings and proper empty/image-only states; tests keyboard/pointer behavior.
- [x] Connect packaging/preview allowlists, profiles and twelve guides; document theme-author contract.
- [x] Review all changes; run affected checks and inspect browser UI.
- [x] Prepare isolated dev TV artifact for owner QA; record actual vs untested results.
- [ ] Save feature work, prepare release/next review without touching frozen inventory, remove temporary worktree when finished.

Focused implementation and independent review are complete. Browser coverage was run in segments after correcting two stale test assumptions (style-node identity and the old cache ceiling). Final versioned-candidate acceptance, including normal audio/control return, standby/cold boot and OTA/rollback, remains the release coordinator’s gate. Exact Node 0.10.25/0.12.2 runtimes were not exercised. Private device results are not published by this plan.
