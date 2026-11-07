# No-root webOS 3.x compatibility integration, 2026-11-07

[PR #381](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/381)
was updated for the unfrozen `release/next` candidate. All eight overlapping
JavaScript/test files were merged after normalizing the three inputs with the
project's pinned Prettier configuration. The newer inventory fallback and the
other integration changes were retained. Original contributor commits remain
in the ancestry; no force push is needed.

Implementation revision: `20c8d063e7c0aa075c5630623c0d59f46c7143b2`. Integrated
into `release/next` as merge `a83c8011534481adb2178a3263fec115d142cd93`.
The follow-up inventory commit selects no version and records no new acceptance.

## Changes and review

- Transform strict block function declarations that Acorn accepts as ES5 but
  Chrome 38 rejects. Other compatible ES5 scripts retain their bytes.
- Confirm `running:false` with the independent Home broker. Preserve explicit
  safety blocking and deliberate start confirmation. Async status completion
  retains focus and remote scrolling in open diagnostics.
- Keep inventory and screen-watch SSAP manifests identical, including app,
  input and power permissions. No additional endpoint, key or persisted state
  is introduced; each connection now requests the existing combined set.
- Compile the No-root Home and independent Updater services, including the
  injected Home theme receiver, through the existing Helper Node compiler in
  both source and embedded-payload builders.
- Use the old Node `url.parse`/`url.resolve` APIs for Updater transport. Retain
  verified HTTPS/custom CA, host/path/credential/port restrictions, response-size
  and redirect limits. Reject literal/encoded dot path segments and missing
  redirect locations. Test actual transport operations after compilation.

Independent read-only review found no actionable remaining findings. This is
AI-assisted review, not human hardware acceptance.

## Local verification

macOS ARM64 host, current Node 23.11.0 and official Darwin x64 Node 0.10.15,
0.10.25 and 0.12.2 runtimes. Python checks use the maintained project virtualenv.
The added focus regression failed before its correction. The original compiled
Updater transport rejects the fixed release URL on old Node; the corrected
runtime fixture exercises real validation and redirect handling with HTTPS
substitutes instead of merely loading the service.

Passed on the combined product tree:

- `node tests/tv-service-compat.cjs` with `NODE010`, `NODE01025` and `NODE012`:
  both compiled services load; Updater accepts fixed URLs and handles relative
  and CDN redirects, refuses forbidden destinations, absent Location and loops.
- `node tests/helper-compat.cjs` on all four runtimes: controller, service,
  Buffer/polyfills, local WSS/frame limits, watchdog and stop regressions.
- Panel diagnostics and published-Helper UI; app inventory; screen-watch;
  updater transport; `tests/web-build.cjs`; `scripts/check-tv-web.cjs` for all
  four web frontend directories.
- `python -m unittest discover -s tests/setup -p test_package.py`: five tests,
  including actual embedded Home/Updater IPK runtime and receiver contents.
- `python -m unittest discover -s tests/setup -p test_update_ui_package.py`:
  standalone Updater staging test.

Per the maintainer's instruction, integration does not wait for feature-PR CI.
The complete combined candidate suite, browser coverage and final platform
build remain pending; these focused results must not be recorded as their pass.

## Packaging, documentation and acceptance limits

No version is selected or bumped in this implementation PR. Freeze must bump
Home, Helper and the independent Updater, synchronize component manifests and
validate changed packages/embedded installers and the Helper rollback approval.
Current approved/published Helper 0.7.4 bytes do not approve changed source bytes.
The explicit historical Helper reuse map contains only 0.6.16/0.6.17/0.6.19;
other current source packages are rebuilt rather than served by that map.

Updated `docs/TV-WEB-BUILD.md`; no new installation command, user control or
translated string is introduced. Current user/translated guides need no changed
procedure for this source fix. Final prerequisite/compatibility/update/recovery
and translation review remains part of candidate freeze.

No television was accessed or changed. Model, firmware/webOS, remote and device
installer result for this integration are unestablished. Home routing, physical
controls/emergency release, sound, standby, cold boot, Developer Mode permission
behavior, installation, OTA and rollback are untested. Historical author tests
are not acceptance of this branch or a plain Developer Mode installation.
Original issue #47 remains open awaiting original-device confirmation; the
separately reported boot permissions and nested installation paths are not
claimed fixed here. Public delivery follows normal candidate publication.
