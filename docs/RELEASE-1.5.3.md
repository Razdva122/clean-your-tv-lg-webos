# v1.5.3 — Ribbon, installer checks and legacy Helper runtime

Status: unpublished candidate. The maintainer approved adding Ribbon to 1.5.3
and rebuilding after the remaining planned PRs are integrated. The intermediate
build was cancelled at the maintainer’s request. The prior successful build and
[verification report](history/2026-10-30-release-1.5.3-final-verification.md)
remain historical evidence for their original artifacts. The expanded candidate
requires a new complete build and affected acceptance; see the
[scope reset record](history/2026-10-30-release-1.5.3-ribbon-rescope.md).
Physical TV acceptance, the new Helper transition and the unresolved standby
decision remain pending. This release must not be presented as universal TV compatibility.

## Changes

- #191: separate Appearance layout/app controls from Themes, add ID-first theme installation, show the effective Columns count and place language choices directly in their category. Remote navigation, delayed-status focus and twelve-language browser checks passed; physical TV acceptance remains pending.

- #188: bundle Ribbon for offline selection in both editions, with theme-driven
  scenic ribbon geometry, slanted cards and shortcut placement. Navigation enters
  Settings at the visible left edge, including after the application window moves.
  The existing Classic default remains. Theme authoring uses the optional
  `ribbon-layout-v1` capability; older Home versions reject unsupported imports
  before replacing the selected theme. Physical remote acceptance is pending.

- #175 and #183 (#160, #164): visible prerequisite results in console, desktop
  and Android, retained failure rows and diagnostic-report guidance. Root still
  requires TV Node.js 8+ and supported Python/Home interfaces. This improves
  diagnosis, not the original reporters' unsupported runtime or connection.
- #176 (#170): fixed-layout themes preserve hidden Columns geometry during
  Appearance Apply; hidden controls remain unavailable to pointer, keyboard and
  accessibility navigation. Installed-package acceptance is still required.
- #181 (#152): compile Helper for Node 0.10.25+, use descriptor-safe pairing-key
  reads and compatible vendored WebSocket calls. Published baseline pairing and
  emergency/watchdog guards remain authoritative. EF950V installation, input,
  power behavior and rollback remain unverified until actual target-TV results.
- #177 (#133): isolate maintainer read-only admission from retained Python code
  and obtain the original candidate from its authenticated operation. This does
  not perform individual recovery or add a Settings-only firmware adapter.
- #180 (#171): record guarded wake refusal stages and bounded private power-stream
  outcomes. This is diagnostic coverage, not a fix for automatic Home after wake.
- #117 (#116): explain exact Homebrew exec denial in twelve languages, preserve
  original request IDs and inspect before retry. Supported upstream prerequisite,
  exact-artifact acceptance and public Homebrew promotion remain pending.

## Component versions

| Component | Published 1.5.2 | Candidate 1.5.3 | Reason |
| --- | --- | --- | --- |
| cytv | 0.6.0 | 0.6.1 | Changed preflight, visible checks and recovery tooling |
| Home | 1.6.0 | 1.6.1 | Ribbon, shared layout module and Appearance CSS |
| Home Helper | 0.6.20 | 0.6.21 | Node 0.10.25/runtime and pairing-key handling |
| Root | 0.6.1 | 0.6.2 | Shared UI and infrastructure diagnostics |
| Both edition Updaters | 0.3.3 | 0.3.4 | Both embed changed Appearance CSS |
| Android / versionCode | 0.5.0 / 15 | 0.5.1 / 16 | Changed UI/native replay/bridge and embedded payload |
| System supervisor | 1.1.2 | 1.1.2 | Executable supervisor/IPK closure unchanged |

Home, Helper, Root/infrastructure, both Updaters and all computer/Android installers
must be rebuilt from this source. The changed Helper runtime requires a new
version; published 0.6.20 must not be replaced with different bytes. Existing supervisors remain pinned;
normal admission, signatures and minimum-supervisor checks remain unchanged.

## Delivery and acceptance limits

The existing Helper rollback record approves only the exact 0.6.19 to 0.6.20
transition. It does not approve 0.6.20 to 0.6.21 or cover the vendored/runtime
changes under a permission-only exception. The new raw/canonical Helper hashes
and authenticated published Home 1.6.0 / Helper 0.6.20 rollback bytes are recorded
in the final verification report. The new transition still needs applicable
acceptance or explicit exact-scope approval;
publication must remain blocked until that gate is truthfully satisfied.

The [unattended C3 record](history/2026-10-30-unattended-c3-ui-proof.md) tested the
installed Root 0.6.1 baseline plus a temporary in-memory footprint proof. It is
not acceptance of these new packages. Its clean restoration and renderer result
retain their original artifact scope.

#171 standby remains unresolved. The previous release's limited-risk decision
is not a new passing result or automatic approval of this release. Record an
explicit fix/follow-up decision and the affected artifact tests before final
release approval. Root firmware support and other users' retained recovery remain
separate unresolved work. The independent Homebrew Installer stays unreleased
with promotion disabled.

The previous selected build was run 41095949258 / attempt 2. Its pin was removed
when Ribbon expanded the frozen scope; a new complete build must be selected.
Remaining work is to record scoped controls,
startup, UI and update/rollback results and satisfy Release
policy before main/publication. No new physical compatibility, phone test,
installer success or completed device recovery is claimed by these notes.
