# Issue 207: bounded inventory fallback and remote icon refresh

## Scope

Related issue: [#207](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/207).
This is source-only follow-up work after the contributor supplied an IR patch
and an inventory-permission report. It does not modify the frozen 1.10.0
candidate, select a release version/build, copy the contributor's patch, or
establish compatibility on either reported TV.

The picker previously queried only the cross-package Helper service. A denied
LS2 request therefore returned the saved inventory even if the live native
controller could make its existing paired SSAP query. No-root now keeps that
first request, including its original 12-second deadline, and on failure tries
`com.gathin.tvhome.renewal/listApps` once with a six-second client deadline.
Root retains its original service and does not enter this fallback.

The same-package service authorizes the exact Home application and an empty
payload. It sends an expiring, correlated fixed `listApps` request through
`catalog-request.json` / `catalog-response.json` in its existing `state/home-control`
directory. Files use the existing 0660 atomic-write convention; the directory's
existing provisioned group/permissions remain the boundary. This new transient
channel is separate from Home commands and input status. It contains private
inventory metadata and must not be copied into diagnostics or public reports.
The caller cannot select paths, commands, endpoints or pairing credentials.

The live controller shares an in-flight catalog read and calls the existing
SSAP transport with a three-second budget. That transport retains its existing
pairing-key validation/permission normalization, host selection and payload
limits. No new permission grants or broader ACLs are introduced. No service
restart, pairing prompt, Helper start, latch clearing or input remapping is
performed. A stopped/blocked controller does not serve the fallback. Late
responses after Stop, terminal relay output or request expiry are discarded.

Catalog refresh also previously preferred any cached icon over a fresh remote
URL. Fresh remote URLs now replace old remote URLs. Missing metadata preserves
the previous icon; packaged and embedded icons remain preferred over raw remote
metadata, and a fresh embedded icon may replace an older embedded icon. This
fix does not fetch/inline remote resources or resolve TLS certificate rejection.

## Verification

- Added regressions were observed failing before implementation, including
  LS2 refusal/timeout, stale URL replacement and missing catalog broker reads.
- Final focused command passed 70 tests:
  `node --test tests/apps/inventory-fallback.cjs tests/apps/native-icon-quality.cjs tests/controller-watchdog.cjs tests/home-control-bridge.cjs tests/home-control-jail.cjs`.
  Covers success/empty catalogs, bounded failure, old-service compatibility,
  stale callbacks, exact caller/payload validation, service-only jail access,
  independent Home commands, shared reads and terminal/Stop reply fencing.
- Independent review found a shortened direct-request deadline. A virtual-clock
  regression reproduced rejection of a valid 6.5-second response; restoring the
  original 12-second deadline made it pass. Final review had no remaining
  actionable findings.
- `tests/helper-compat.cjs` passed on current host Node 23.11.0 and exact Node
  0.10.15, 0.10.25 and 0.12.2, including compiled controller/watchdog regressions.
  Renewal service/import compilation passed its ES5 parser gate.
- Related inventory, input status, layout/profile, tuner discovery, Home control,
  resume, published Helper UI, diagnostics and renewal/storage checks passed.
- `npm run test:compat`, `npm run lint:compat`, and `git diff --check` passed.
- Browser compatibility passed modern, no-inset and no-inset-or-es2015 profiles.
  `prefixed-webkit` failed the existing shortcut horizontal-row assertion.
  A targeted repeat failed, and the same failure reproduced in a temporary
  launcher copy with the original HEAD app-library. No layout assertions or
  product CSS were weakened to bypass it.
- `PREVIEW_URL=<local-preview> node tests/apps/ui.cjs` passed the complete
  app-management scenario, including selection of a discovered homebrew fixture
  after a simulated cross-package refusal and successful same-package fallback.

The initial preview failed because the selected Python lacked fontTools. Using
an existing environment with the declared fontTools 4.60.1 resolved preview
startup. The first extended browser attempts placed the new scenario after the multirow
fixture, where the toast layer intercepted its pointer click (including after
reload). The fallback scenario now runs on the preceding ordinary layout,
restores that fixture afterward, and retains normal pointer assertions. Product
CSS and the existing multirow assertions remain unchanged.

## Delivery and remaining work

Home/its renewal service, Helper and embedding installer payloads need coordinated
rebuilds. At freeze, the release coordinator must bump/synchronize Helper rather
than reuse a published package pin, verify source-package content, and perform
appropriate update/rollback and physical acceptance. No versions or published
package bytes are changed by this preparation branch.

Original standard-remote routing remains unresolved. Contributor permission to
adapt the unlicensed gist, test provenance and the source of unprivileged input
access were requested in the issue. Icon resource expiry versus certificate
rejection and the provenance of manually generated permission files also remain
questions. Neither the rooted mixed setup nor host tests prove stock Developer
Mode input access or a fix on the original LJ550T. TV model/firmware/remote,
physical Home, audio, standby, cold boot, OTA and rollback acceptance for these
changes are untested; no TV was accessed.

User controls and installation steps are unchanged, so localized setup/control
guides need no new steps in this source-only PR. The English app-management guide
records candidate-only behavior and limitations; publication wording remains a
release-coordinator responsibility.
