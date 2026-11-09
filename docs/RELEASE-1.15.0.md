# v1.15.0 — weather and installation recovery

Unpublished release candidate in [PR #458](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/458).
Versions and the ten-PR scope are frozen after the reviewed weather correction
batch. Public delivery, exact-artifact
acceptance of that replacement and final package/feed verification remain pending.

## Changes

- Add optional weather to both Home editions: manual or approximate automatic
  city selection, metric/imperial units, four theme-aware formats, localized
  previews and an accessible Data sources dialog (#463, #353). Weather is off
  by default. Add manual MET Norway/Open-Meteo selection and Auto with at most
  one fallback attempt; show the actual source. MET uses the existing trusted
  Home/Root service with identifying User-Agent and verified TLS. Fixed HTTPS
  forecast/geocoding and GeoJS endpoints are contacted only after the applicable
  location choice; preferences/cache stay local and are
  excluded from legacy profile exports. Failed requests retain bounded cache
  behavior and six-hour expiry. Ribbon suppresses weather; Liquid Glass uses
  Compact. Update weather-capable themes and credited temporary community forks.
  Remove Channel and Itachi from the active catalog; historical packages remain.
- Complete legacy No-root stock-screen removal and retained C1 recovery support;
  use bounded asynchronous Root cleanup and reconcile a currently verified,
  matching completed removal (#457; #240, #283, #418, #438). Explicit removal
  may return older TVs to Live TV when no launchable LG Home is available.
- Deliver the selected Root runtime through explicitly confirmed full
  reinstallation, rather than activating an older self-consistent installation
  (#459, #355). Full removal deletes project preferences; interrupted cleanup
  and required restart stop replacement until verified. Preserve root access,
  unrelated applications and original operation/recovery authority.
- Admit only narrowly verified immutable internal system images and permit a
  separate fresh native installation after verified cleanup (#462, #440).
  Unknown mounts and foreign Home state remain refused. This is not proof of
  the original reporter's mount subtype or successful device recovery.
- Unify website/demo presentation and add independent Video/4K theme filters
  (#461). Detect and remember visitor language at the neutral website entry;
  retain explicit locale URLs (#468). Reconcile the previous publication's
  current documentation (#460).

## Versions and packaging

| Component | Published v1.14.0 | Candidate v1.15.0 | Reason |
| --- | --- | --- | --- |
| Home FHD/HD | 1.13.3 | 1.14.0 | Shared weather, settings, localization and theme assets |
| Home Helper | 0.8.0 | 0.8.0 | No source change; preserve exact published bytes |
| cytv installer | 0.15.0 | 0.16.0 | Removal, reinstallation and native admission |
| Android / versionCode | 0.14.0 / 29 | 0.15.0 / 30 | Shared operations and rebuilt embedded payload |
| Root / infrastructure | 0.14.0 | 0.15.0 | Weather UI, cleanup and native recovery support |
| Both edition Updaters | 0.5.5 | 0.5.6 | Changed embedded cleanup/Luna support and shared resources |
| Fresh System / protocol | 1.2.7 / 1 | 1.2.8 / 1 | Embedded Luna support changed; existing supervisors stay pinned |

Rebuild desktop/CLI, Android and both-resolution Root/No-root payloads, including
normal/Beta/experimental support closures. Preserve Android ID, original signer
and stored private data. No Homebrew promotion or new supervisor migration is
selected. The paired author toolkit has an independent release lifecycle.

## Validation and acceptance

[Candidate preparation and scoped cases](history/2026-11-09-release-1.15.0-preparation.md)
records pre-dispatch verification. Earlier implementation results are in the
[combined installer integration](history/2026-11-09-next-candidate-integration.md)
and [weather integration](development/2026-11-09-weather-integration.md) records.
Those checks do not establish a successful full versioned candidate or new TV
acceptance. The current selected build and remaining gates belong to PR #458.
The [dated QA inventory](history/2026-11-09-release-1.15.0-qa.md) records the
failed preliminary full runs and reviewed fixture corrections #464/#465.
No failed run is selected; the current release record owns the replacement build.

The third full build passed all21 jobs. Its exact signed Root packages passed
ordinary update, supported rollback/forward, profile retention and automated
UI/service checks on the maintainer C3 (OLED55C3RLA, firmware43.21.71,
webOS SDK11.2.0, Magic Remote exact model unknown; macOS15.6.1 ARM64 installer).
Its exact signed Android upgrade passed on an isolated API35 ARM64 emulator.
That case pass found Compact preview overflow and direct Open-Meteo forecast
connectivity failure. The correction batch adds MET and repairs the preview;
installed native MET/API cases7/7 and preview cases39/39 now pass. Supported
rollback/forward removes and recreates the MET grant while preserving preferences
and profile state. Final replacement artifacts still need affected acceptance. Earlier results retain their
original hashes. Physical Home routing, audible sound, emergency behavior,
standby, cold boot and OTA remain untested in this session.

All linked issues stay open. #240/#418 original installation failures and #355
original C2 activation remain unresolved/planned. #283/#438/#440 need relevant
published-version device confirmation after delivery; #353 awaits weather
release. Do not repeat diagnostics or change another user's TV for this record.
