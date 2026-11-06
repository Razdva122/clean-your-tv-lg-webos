# Root wallpaper LS2 source fix 2026 11 06

## Integration

[PR #341](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/341) merged
into release/next as `ff71dbee68069c1aa34e24111fc02ca39096eaa4` after every
required check passed on `b2e927f1c103b6932d351c3754f32c3064fa1b2b`.
The owner explicitly selected integration into the current candidate and testing
inside its replacement build. Issue #337 stays open pending delivery and
signed-package acceptance. No new device result is published in this record.

## Source contract

Legacy snapshots retain their original API list. The historical receiver
attachment adds four themeReceiver methods, but not the five wallpaperCache
methods needed for personal video. LS2 captures provided method groups when
registering a category; attaching permission files after the service connects
can leave a live worker using stale groups.

The fix prepares receiver/media permissions before the private Root service
connects to LS2. A separate media API attachment and transition receipt require
both private service.js and package.json in the verified recovery inventory and
wallpaperMediaProtocol 1 in that protected metadata. Existing snapshots and
receiver receipts remain unchanged. No wildcard, new client, recovery operation
or external network endpoint is granted. Permission failure preserves recovery.
Delivery requires the coherent signed System update of Root and private
infrastructure; a UI-only update cannot replace the worker. No-root keeps its
existing same-application service permissions.

## Host validation

[Final PR CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42167024052)
passed all eight Linux/macOS runtime shards, both summaries, browser and optional
Python; full-release was unselected. Local checks included 31 permission tests,
the failing-before/passing-after startup-order/failure test, actual Root packaging
with the protected marker, copied private-service startup, provisioning,
cancellation and updater regressions, plus localhost HTTP/cache and browser
transfer/Apply/reload in both editions. Independent review found no actionable
issue for the coherent System delivery path. Twelve direct-candidate admission
tests passed.

Direct build 42165361732 exhausted its 15-minute job limit during the unsharded
safety suite, with completed checks passing and no packages produced. The
workflow now permits 30 minutes without removing checks or changing signing.
Direct QA 42167035832 was cancelled after the owner selected combined-candidate
testing. Duplicate timeout-only PR #342 was closed. Neither run is final release
or hardware evidence.

## Replacement candidate

The earlier full build 42112684336:1 and signing 42115451492 predate #341.
Their dated records remain historical evidence; the obsolete current build pin
is removed. Component targets are unchanged. New Root/private infrastructure
bytes require a replacement full candidate, signature/provenance/hash checks and
affected acceptance. The RC QA chat owns the next build, pin, signing and device
session; no parallel full build is started by the fix task.

Required wallpaper checks are retained Root receiver startup, image/video
transfer, explicit Apply, UHD/FHD and static playback, reload and original-data
restoration. Record first service activation latency and verify recovery remains
valid. Evaluate controls/audio, standby, cold boot and actual OTA/rollback under
the candidate's affected acceptance scope; none is implied by host tests or a
package installation. Published guide notices still describe 1.8.2 correctly;
setup/controls are unchanged and no locale announces the fix as shipped.

Inventory/record validation passed, including 16 release-flow, 10 release-input
and 3 README release-metadata tests. No main merge or public release is claimed.
