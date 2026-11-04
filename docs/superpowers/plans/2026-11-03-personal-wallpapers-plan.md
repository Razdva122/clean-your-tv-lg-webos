# Personal Wallpapers Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan. Independent receiver and desktop tasks may use dispatching-parallel-agents. Test each behavior before implementation.

**Goal:** Implement approved desktop UHD and phone QR image upload in CYTV and both TV editions.
**Architecture:** Extend temporary receiver with an explicit personal-media mode; independent personal IndexedDB slot feeds the existing renderer; desktop Qt prepares H.264 locally.
**Tech Stack:** Existing Python/Qt, packaged FFmpeg, ES5/IndexedDB, existing private Node receiver.
**Spec:** docs/superpowers/specs/2026-11-03-personal-wallpapers-design.md

## Global constraints

- Preserve frozen release inventory and normal Home/input/update/recovery behavior.
- No personal photographs, TV addresses, PINs or raw diagnostics in Git/public reports.
- Exact shared interfaces, wire shape and byte limits are defined in the spec; unknown input is rejected before application.
- One replacement slot; no cloud, background listener or Node prerequisite for desktop users.
- Run npm ci before tests, use project's existing Python environment and font cache when building UI.

### Task 1: Receiver and mobile page (independent)

Files: theme-receiver/core.js, register.js; new wallpaper-phone.js; scripts/theme_receiver.py; launcher/theme-receiver.js; tests/themes/personal-receiver.cjs, personal-phone-ui.cjs.
Interfaces: `receiver.start({kind:'wallpaper'})`, `ThemeReceiver.start(signal,'wallpaper')`; GET phone page + authenticated capabilities and POST personal JSON as specified. Agent owns service packaging closure. No TV personal manager/panel or desktop edits.

- [x] Write failing real HTTP tests: wrong/expired PIN; foreign Origin; theme browser upload remains rejected; wallpaper mode-only routes; source phone cannot include video/over-HD image; size/base64 envelope; successful status/read; stop/expiry closes sockets and releases holds.
- [x] Run `node tests/themes/personal-receiver.cjs`; expect missing wallpaper routes.
- [x] Implement minimal mode extension and a bundled mobile page with file picker, 16:9 position/zoom crop, JPEG <=2MiB, acknowledgement required and clear limitations, progress/cancel and same-origin fetch. It must not retain a PIN/file beyond the receiving session.
- [x] Run real phone browser upload: local image fixture -> actual canvas JPEG -> authenticated HTTP -> receiver read. Verify decoded output <=1920x1080, no variants, explicit warning, unsupported image rejection, no external requests.
- [x] Run existing receiver, video-cache, receiver-ui and package closure tests. Supply test results and focused diff for integration review.

### Task 2: CYTV preparation and UI (independent)

Files: new cytv/wallpaper.py, wallpaper_gui.py; cytv/gui.py; build-requirements.txt; scripts/desktop_packaging.py; tests/cytv/test_wallpaper.py, test_wallpaper_gui.py and package assertions. Agent owns desktop strings in translations.py only for its additions.
Interfaces: produce the exact personal envelope from spec, HTTP GET capabilities + POST `/v1/wallpaper`, no redirects, RFC1918 literal only, six-digit PIN, 20s timeout, bounded replies. No SSH/pairing/provisioning necessary for this upload.

- [x] Write tests for source dimensions, bounded output/hashes, destination/PIN rejection before network, forbidden redirect, cancel terminating FFmpeg, failed transfer preservation, and 202 labelled received rather than applied.
- [x] Run new tests and observe failure for absent module.
- [x] Implement local preparation using packaged FFmpeg (pin imageio-ffmpeg build dependency or equivalently bounded bundled binary), source JPEG/PNG header/decode checks and 16:9 crop. Qt worker thread never blocks UI. No upscale marketed as 4K; source-dependent variants, poster <=2MiB.
- [x] Add independent Wallpapers action on CYTV start screen; select image, crop/zoom preview, original resolution, destination and PIN, instructions to open receiver on TV, progress and Cancel. Keep installation operations single-flight.
- [x] Exercise real FFmpeg on generated source and validate produced MP4 with `ThemeData.videoInfo`; test Qt form/crop/worker cancellation offscreen and frozen binary inclusion. Supply evidence and diff for review.

### Task 3: TV personal state and settings

Files: new launcher/personal-wallpaper.js; launcher/wallpaper.js/panel.js/css/locales.js; both edition boot/profile startup and build/preview explicit allowlists; browser/unit tests.
Interfaces: exactly PersonalWallpaper and HomeWallpaper.setPersonal in spec. Receiver Task 1 supplies `ThemeReceiver.start(signal,'wallpaper')`.

- [x] Write failing tests for strict wire validation, phone restrictions, MP4 spoof rejection, source-independent selection, transactional slot quota failure, stale candidate cancellation, reload restore and release-before-revoke.
- [x] Observe failures, implement data validation/preparation/storage and source switch. Borrow theme state without taking ThemeRuntime URL ownership; personal holds its own handles and media lease. Start once both edition bootstraps have dependencies ready.
- [x] Extend pane: Theme/My wallpaper selector, CYTV and phone entry actions, source warning/quality availability, QR + manual address/PIN, pending preview Apply/Cancel, Remove. Stop receiving on category close/app hide with late-start cleanup. Receiver/settings suspend does not accidentally pause transfer polling.
- [x] Test phone QR by actual decoding and real browser upload in both edition UI; verify 4K unavailable for phone, source stays personal after theme change, settings preview persists, removal returns to theme, stale work cannot replace current choice.
- [x] Update explicit packaging/preview manifests and verify files/order in both editions. Use a pinned offline QR implementation with attribution and no external endpoint.

### Task 4: Integration, baseline regression and release handoff

Files: root-edition/tests/test_private_service.py; package/scripts test registration; docs/development/WALLPAPERS.md; English and twelve translated guides; plan ledger.

- [x] Reproduce base #264 Linux failure in private receiver method-list test; require both original receiver methods and five wallpaper cache methods rather than the old four-method fixture. Verify actual bundled closure startup/stop, keep caller checks intact.
- [x] Run focused tests for all three deliverables; inspect mobile, Qt and TV layouts. Review trust boundaries, no browser cross-origin permission changes on old theme path, profile/reset and URL/decoder lifetimes.
- [x] Run affected UI/installer/setup/browser/compatibility suites; verify exact legacy Node where available. Test cancellation/failure cases once through the integrated path.
- [x] Document both paths and limitations in all guides; retain private preliminary QA artifacts separately. Independent final code review and fix any material findings.
- [ ] Commit/push focused feature branch and open review targeting release/next, declaring dependency on #264 and frozen-candidate hold. Verify CI; preserve artifacts then clean temporary workspace using supported lifecycle without removing another active checkout.

## Verification ledger

- Receiver independent review: clean. Real mobile file/canvas/JPEG transfer and original theme-route regressions passed; packaged closure includes the offline phone page.
- Desktop review: response-body cancellation and reconnect deadline findings fixed with owned transport sockets and nonblocking IPv4 connection polling. Regression tests observed red then green; scoped review clean.
- TV review: source selection during deferred startup restore was reproduced and fixed; ordered persistence, rejected replacement preservation and visible error clearing have real-browser regression coverage. Final scoped review clean.
- Local UI group passed. Installer group passed, including 686 CYTV tests (two environment-dependent skips). New desktop preparation/UI/packaging tests exercise real H.264 through the TV parser.
- Both-edition integration passed: actual HTTP receipt, chunked read, real service cache, explicit Apply, decoded video, reload and theme independence. QR is decoded by an independent library.
- Old private-service fixture regression reproduced against baseline #264 and corrected separately; seven tests passed.
- Rebased onto frozen integration baseline `61094b32` (Root 0.8.3); post-rebase UI, desktop, personal browser, real cache and source/input regressions passed. The pre-rebase broad browser run was interrupted by the source transition; complete frozen-candidate/browser admission remains separate. Preliminary browser/native-cache tests are not physical TV/Safari or release-package acceptance. Exact legacy Node and native multi-platform frozen builds have not yet been exercised for this addition.

- Production Root cache ACL gap found during final integration audit: added explicit fresh media capability, preserved exact historical registration bytes, tested build/provision/repair/cancellation, independent review clean. Effective firmware grants remain a physical acceptance requirement.
