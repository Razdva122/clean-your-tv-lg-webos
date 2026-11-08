# Preserving AOD during Root profile activation

Published correction for [#282](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/282).
Use matching released Root infrastructure and installers. Host regression
results do not establish the original C4 failure cause or B4 compatibility.

## Write boundaries

The independently read stock baseline contains the complete `defaultApps` and
`idleApp` profiles. The Root override now copies both objects and changes only
`defaultApps.categories.home` and `idleApp.appId`. This preserves AOD, other
categories, support flags and unknown vendor fields even when profile resolution
replaces a nested category map instead of merging its members.

Both activation and stock recovery use the same transport. It reads
Settings Service `general.defaultApps`, copies the whole object, changes only
`home`, submits `com.webos.settingsservice/setSystemSettings`, and verifies the
whole settings object afterward. The former activation-only `setDefaultApp`
shortcut is removed. A failed, malformed, denied or timed-out read/write does not
trigger a fallback or a blind retry. Each RPC retains its five-second bound.
The read/write pair is not a platform compare-and-swap; concurrent external
settings writers are not serialized by our private transaction lock.

Full profile equality during activation and restoration remains mandatory.
Losing AOD is an activation failure, never an ignored difference. Independent
guardian, emergency release, publication identity and conflict checks remain.
The setup-only absent-Home initializer still uses its existing stock-only SAM
operation and strict unchanged-settings/profile checks; this correction does
not bypass a failed initialization or resolve an existing pending installer
operation.

The Settings endpoint already exists in Root for sound configuration, but writing
`general.defaultApps` through it is new to this routing path. No LS2 permission,
network host, dependency or user control is added. The public
[Settings Service API](https://www.webosose.org/docs/reference/ls2-api/com-webos-service-settings/)
describes the general read/write interface; OSE is not a contract for retail B4
or C4 Home behavior. Package/device acceptance must verify the exact firmware,
SAM cache updates, physical Home and AOD, not only Settings readback.

## Recovery records and older runtime compatibility

New active transactions use profile journal version 2. The payload bytes and
SHA-256 are deterministically derived from the journal's validated stock baseline.
The recovery adapter checks the matching bytes, owner, inode, mode and link count
before deleting either the staged or published file. Version 1 journals retain
their original fixed payload and remain recoverable.

After owned-file removal and exact complete baseline readback, recovery atomically
writes a version 1 **restored terminal record**, with the legacy fixed digest.
`completed_payload_sha256` retains the actual completed version 2 payload digest.
This terminal record represents verified removal, not permission to remove an
active legacy file. An interrupted/failed final save leaves version 2 recovering;
there is no early conversion and no automatic deletion of journal evidence.

The terminal bridge matters because a retained old runtime validates even a
restored journal before archiving it for another activation. Leaving that record
at version 2 would break old-version reactivation. New pending/recovering journals
must never be interpreted by old runtime code: existing update and rollback paths
require route restoration before replacing infrastructure. The existing recovery
manifest continues to bind all installed runtime files; do not hot-patch private
files or overwrite an unresolved installation to test this change.

## Acceptance still required

Rebuild Root infrastructure, app payloads and embedded desktop/Android installers
through the coordinator. Do not change the selected release build or pinned
supervisor from this focused fix task. Verify signed update and retained rollback,
AOD/unrelated categories, guarded activation, ordinary off and triple-Home release,
Home/Back/other controls and sound. Test standby and true cold boot separately.
No TV was contacted or changed for this source correction.

[Investigation and checks](../history/2026-11-05-root-aod-preservation.md).

## Cross-project source review

The [pinned comparison](../history/2026-11-05-aod-cross-project-review.md)
supports preserving the full category map: Home Chooser's firmware/VM study
reports shallow category replacement on webOS 10.3.1, and its implementation
also copies the existing categories before changing Home. Its normal setter
preserves other Settings keys in the sampled firmware; a separate boot-time
cached-map race is reported. Do not describe every `setDefaultApp` call as
destructive or treat the original report as isolating that boundary.

Settings notifications and third-party firmware research support the direct
write mechanism, but our `sam_home` readback reads Settings, not an independent
SAM consumer-cache query. Stored-value equality is not physical routing proof.
Source/host review is available without target TVs; target Home/AOD, power and
signed-update/rollback acceptance remains untested. The source review neither
waives release gates nor changes the frozen candidate.
