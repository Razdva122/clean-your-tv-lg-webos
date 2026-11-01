# Issue 207: 720p and passive diagnostics

User-authorized implementation and reviewed integration into unfrozen `release/next`.
No TV connection, installation or reporter test is authorized by this development task.

## Constraints and chosen design

- Preserve the 1920×1080 logical Home scene and existing 1080p default package.
  Fit only `#homeSurface` to actual CSS viewport; trusted dialogs/settings remain
  responsive in physical viewport coordinates. Convert the two Home DOM-rect
  consumers back into logical scene coordinates; pointer hit-testing stays native.
- Offer explicit 1280×720 manifest staging/build mode without patching installed
  packages or signed updater payloads. LG supports separate HD/FHD app graphics
  resolutions; default artifacts remain coherent 1080p until release packaging
  selects otherwise. Physical HD package acceptance remains pending.
- Preserve all Helper/native relay bytes, grabs, key-up, emergency and watchdog
  behavior. Do not change IR routing based on the unconfirmed device/key hypothesis.
- Standalone IR observation is fixed-duration, ARM32 little-endian, read-only,
  restricted to named remote sources, with bounded first key-pair output and no
  raw log, timestamp, device path, identity, app inventory or input history.
- Panel diagnostics describe its actual existing caller context, never infer it
  from an SSH public-bus probe. No extra RPC, retry, automatic start or state write.

## Tasks and checks

1. Reproduce clipped 1280×720 Home in a real browser and assert physical scene
   bounds, then implement `HomeViewport.update()` and `HomeViewport.rect(element)`.
   Load before Home bootstrap and include in explicit package/preview inventories.
   Test 1080p unchanged, 720p fit, five theme presets, columns 1–8, Inputs placement,
   top-button navigation, pointer targets and standard dialogs.
2. Add validated optional resolution to `tv_web_build.stage`, Root preview/build
   and the manual No-root build path. Test both accepted resolutions, rejection
   before writes and immutable source manifests. Do not silently modify public feeds.
3. Parallel isolated-file task: implement passive remote diagnostic and fixtures
   covering denied access, unknown names, unsafe leaves, malformed events, flooding,
   repeats, partial pairs, monotonic deadline and descriptor cleanup. Parse ES5 and
   run exact legacy Node when available. No production relay changes.
4. Parallel isolated-file task: add bounded allowlisted panel RPC snapshot and
   Show/Hide diagnostics using existing translated strings. Test malformed/denied/
   timed-out replies, privacy, stale generations, no extra calls and unchanged start
   confirmation. Verify 13 locales at 720p/1080p with actual keyboard focus.
5. Wire focused checks into CI; update developer/usage and localized guide boundaries
   without advertising shipping acceptance. Run affected UI/TV/installer/setup checks.
6. Request independent review of implementation and privacy/admission boundaries.
   Resolve findings, wait for final selected CI, merge ready PR into release/next,
   recollect inventory and dated evidence, refresh candidate human/generated records.
   Keep original standard-remote failure unresolved with accurate issue status.
