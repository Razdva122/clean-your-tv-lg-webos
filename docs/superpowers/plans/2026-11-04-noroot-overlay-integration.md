# No-root Overlay Integration Implementation Plan

> **For agentic workers:** Execute in this isolated feature branch with test-driven-development and review checkpoints. The coordinator owns build selection and physical device windows.

**Goal:** Make actual No-root Home/Helper open and dismiss Ribbon above content.

**Architecture:** One existing Home identity hosts overlay. Shared presentation controller queries native Helper via an authenticated, read-only LS2 seam; unavailable/stale context stays opaque. Secure Helper storage/authentication is implemented in the coordinated Helper task, not duplicated here.

**Tech Stack:** Existing ES5-compatible JS/Babel, Node 0.10.15+, Python IPK packaging, Playwright compiled UI tests.

**Spec:** ../specs/2026-11-04-noroot-overlay-integration-design.md

## Global Constraints

- Keep com.gathin.tvhome identity, profile and updater contracts.
- No new ACG, network endpoint, dependency or writable cross-app channel.
- Root behavior and emergency/watchdog/key-up ownership remain independent.
- Context timeout, disconnect, malformed reply or age above2000ms means opaque.
- A launch parameter is not authorization or proof of content.
- Real device checks require coordinator-owned exclusive windows; no equal-version force.
- Rooted C3 tests do not prove pristine No-root compatibility.

### Task 1: No-root presentation adapter and real UI regression

Files: launcher/app.js, launcher/home-presentation.js, launcher/appinfo.json,
tests/home-presentation.cjs, tests/home-presentation-ui.cjs.

Consumes: normal launch/relaunch/visibility events and bounded callLuna callback.
Produces: actual No-root UI requesting native read-only presentationContext;
validated replies can enable Ribbon overlay, failures remain opaque.

- [ ] Add compiled native No-root regression, with CYTV_BROWSER_PREVIEW false:
  first missing Helper stays full; a trusted context response enables overlay;
  Back closes, relaunch toggles, settings/editing keep correct ownership.
- [ ] Run node tests/home-presentation-ui.cjs and observe old-source failure.
- [ ] Add a small edition-aware adapter using existing callLuna. Require exact
  returnValue/eligible booleans, a bounded safe generation and finite nonnegative
  observedAgeMs<=2000. Timeout and exceptions return unknown. Do not accept
  PREVIEW_HOME_CONTEXT or launch JSON as native authority.
- [ ] Add metadata from the measured lab to the existing Home, preserving IDs,
  version, ACG and update protocol. Gate transparency on shared controller state.
- [ ] Run pure state-machine, actual compiled UI, startup/first-frame and ES5 tests.

### Task 2: Native Helper activation/context/dismiss ownership

Files coordinated with Helper task: native/app/native.js, screen-watch.js,
new minimal context policy module/tests, native/service trusted broker as needed.
Consumes: actual physical Home, live authenticated SSAP foreground, power/reset,
stop/watchdog and authorized Home caller identity.
Produces: agreed presentationContext response plus generation invalidation;
normal dismissal does not trigger return-after-exit loops.

- [ ] Obtain measured sender authorization evidence and exact RPC URI/schema.
- [ ] Add failing policy tests: real Home versus manual/startup/wake; current
  versus stale/disconnected subscription; own/unknown/system foreground;
  relaunch/dismiss versus ordinary app exit; stop/off/emergency late callbacks.
- [ ] Implement smallest shared policy at all Home launch call sites, keeping
  launch(id,done) compatibility. Context generation invalidates on stop, power,
  off, dismiss and newer activation. Read-only query never changes routing.
- [ ] Run native/controller regressions on current and exact legacy Node runtimes;
  review secure storage/broker and UI integration together before merge.

### Task 3: Wallpaper, packaging and documentation acceptance

Files: launcher/app.js, wallpaper.js as required by tests;
scripts/build-cytv.py and package tests only where existing tracked-file build
needs explicit metadata/asset assertions; docs/THEMES.md, all12 localized guides,
release notes and dated evidence.

- [ ] Add regression for no decoder ownership before the context decision and
  while overlay/settings are shown. Unknown context uses static opaque fallback.
- [ ] Ensure actual app launch success closes the current generation only;
  failed launch keeps UI, editing/Undo cannot be stolen by late callbacks.
- [ ] Build/inspect both1080p and720p actual Home packages, including metadata,
  app identity, updater protocol, ACG and unchanged profile retention paths.
- [ ] Update production guidance to describe No-root overlay, opaque lifecycle,
  prerequisites and actual firmware limits; keep lab evidence distinct.
- [ ] Run affected UI/TV/installer/preview checks; obtain independent review and
  address findings. Create focused PR to release/next; no main publication.

### Task 4: New frozen candidate and physical acceptance

Files: release-plan.json and dated acceptance record/PR281.

- [ ] Integrate reviewed Helper, overlay and Root blocker PRs under one coordinator;
  collect inventory, select compatible versions, freeze, run complete candidate
  checks and matching signed packages. Verify exact artifact identities.
- [ ] Install via supported admission preserving recovery/profile/retained rollback.
  Stop on unknown terminal state, never force or replay an uncertain install.
- [ ] Owner physical checks: Home once, repeated Home, Back, Magic Remote, HDMI
  and app video/audio, settings/edit/Undo, launch/return, unknown/static fallback,
  emergency/off/watchdog, standby and true AC boot; record each actual result.
- [ ] Verify normal upgrade and rollback and reconcile issue labels/evidence.
  Keep draft/not-ready for any unresolved gate; pristine No-root test remains
  separately identified. Main/stable release requires explicit authorization.


## Checkpoint — frontend foundation

Implemented typed context/generation/transport freshness, real No-root native
metadata, activation-aware toggle, opaque fallback and wallpaper/input-preview
decoder fences. Actual compiled native-mode UI tests failed on original source
and now pass, including manual/startup relaunch, settings/Back, stale/invalid
context and HDMI preview acquisition/release. Independent review found two bugs
in relaunch classification and HDMI preview ownership; both were reproduced,
fixed and re-reviewed without further findings. Pure controller/context, ES5
build/lint, both-edition Ribbon edit, startup motion and wallpaper lifecycle
checks pass. This is not a complete integration: trusted native RPC registration,
renewal relay, dismissal/off cancellation, initial native activation and final
packaged/device acceptance remain pending. No package from this branch has been
installed. Current selected RC build/acceptance still refers to old bytes.
