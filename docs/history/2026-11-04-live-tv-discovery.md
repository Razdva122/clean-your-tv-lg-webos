# Live TV discovery investigation — 2026-11-04

Related issue: [#290](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/290).
This is read-only discovery evidence, not an installation or tuner-launch acceptance.

## Device and scope

- Maintainer TV: LG OLED55C3RLA, checked at the owner's request.
- Firmware/webOS: unknown; the supplementary software-information request did not succeed.
- Remote: unknown, not used.
- Saved connection profile: Root; installed edition and Home/Helper/component versions
  were not independently inspected. No packages were installed or changed.
- Computer platform: macOS. Installer installation/update was not exercised.
- Product scope: candidate Home/Helper/installer inventory correction for #290;
  release/component target versions remain for the release coordinator to select.

## Observations

The TV's paired SSAP `com.webos.applicationManager/listLaunchPoints` succeeded
but omitted `com.webos.app.livetv`. The separate read-only SSAP
`com.webos.applicationManager/listApps` succeeded and reported that installed app
with title `Телетрансляция` and `visible: false`. The related `livetvopapp` system
app is not the broadcast-tuner tile and must not be added with it.

This explains the No-root omission: both initial inventory and picker refresh
previously used launch points alone. Root inventory uses a different query but
also maps `visible: false` to exclusion, so its source filter needs the same narrow
exception for an actually discovered tuner. Root's live inventory response was
not verified: the SSH Luna queries returned no JSON output. This does not prove
that the Root service failed or that its full app list was empty.

The updated Helper query was then executed locally against this same TV using
its existing pairing, with only the socket API adapted to current Node. Expected:
retain ordinary launch points and include the discovered tuner under its native
name. Actual: returned `com.webos.app.livetv`, `Телетрансляция`, `hidden: false`.
No launch, pairing renewal, app installation or TV configuration change occurred.
The installed TV package was not replaced; this observation validates the query
logic, not packaged Helper execution on TV.

## Regression and remaining acceptance

Tests reproduce the omission before the fix and cover optional-query denial,
malformed replies, timeout/disconnect, models without the tuner, duplicate IDs,
localized titles, catalogue bounds and exclusion of unrelated hidden system apps.
The modern installer, legacy sync path and Root visibility mapping are included.
Legacy sync also retains a confirmed tuner when its icon cannot be downloaded.
See the focused PR for the final commands, results and source SHA.

Still untested: installed-package Add app rendering and persistence on this TV,
actual tuner launch/channel switching, sound, Home routing, standby, cold boot,
OTA, rollback and other models/firmware. The reporter's actual model and versions
remain unknown. No compatibility or original-device fix is claimed from these
read-only queries or local tests.

## Packaging

No release version is selected here. The No-root change requires a new Helper
version and rebuilt app/service package; reusing the published Helper baseline
would omit it. Installer source must also be rebuilt for initial discovery. Root
needs its rebuilt Home package. The release coordinator owns component bumps,
manifest synchronization, source-package validation and affected acceptance.
The change adds one fixed optional read-only SSAP endpoint, `listApps`, under the
existing `READ_INSTALLED_APPS` permission. It adds no persistent state, permission,
network host, launch override or pairing action.
