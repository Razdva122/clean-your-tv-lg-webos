# Legacy Root Beta Implementation Plan

> Execution: inline using executing-plans, with independent code review.

**Goal:** Offer legacy Root Beta and No-root via existing root SSH in the common installer.

**Architecture:** Separate persisted edition, SSH connection and Root variant.
Build a separate authenticated legacy payload using the existing compiler. Route
all frontend choices through the shared CLI and keep device checks authoritative.

**Tech Stack:** Python, existing unittest suites, Babel/core-js, Node 0.12.2, Qt/Android CLI bridges.

**Spec:** `docs/superpowers/specs/2026-11-07-legacy-root-beta-design.md`

## Global constraints

- Exactly Node 0.12.2 for Beta; ordinary Root retains Node 8+.
- No system runtime replacement, Developer Mode installation, automatic publication or recovery reset.
- No edition switch with pending operations; keep all package and transport trust checks.
- Beta ordinary OTA is disabled; recovery and removal remain available.

## Tasks

- [x] Add failing profile/transport regressions: No-root root SSH persists root credentials, trust and port while retaining the No-root product identity; invalid combinations are refused.
- [x] Extend `cytv/state.py`, `transport.py`, CLI and frontend argument consumers with optional connection/variant fields; run profile/SSH/Android tests.
- [x] Add failing runtime-choice regressions: exact Node eligibility, explicit selection/cancel, cross-edition pending refusal and saved variants. Implement shared selection before mutation in `cytv/root_runtime.py` and `cli.py`.
- [x] Add generated-payload regressions; extend Root builders and installer payload staging with a distinct Beta mode, baked device policy and disabled OTA. Keep prototype mode host-only. Run exact Node 0.12.2 closure and device policy tests.
- [x] Integrate vendor module/bootstrap probe, Root preflight and authenticated payload selection. Verify negative Home/Python/native checks, recovery and local removal paths.
- [x] Add voluntary feedback and allowlisted variant diagnostics; update setup guidance and translations for all supported frontends/locales.
- [x] Run affected installer, Android and TV checks, inspect generated artifact identities, request independent review and resolve findings. Record physical acceptance as untested; reconcile issue labels and preserve other workspace files.

Verification and remaining physical acceptance are recorded in `docs/history/2026-11-07-legacy-root-beta-installer.md`. No release or TV installation was performed.
