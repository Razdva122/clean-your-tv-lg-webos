# Root setup with an absent Home override

This describes published setup behavior for issue #82, reported on
43NANO90A6B / firmware 33.31.61 with cytv 0.3.1 and Root 0.3.0.
No physical acceptance of this correction has been performed.

## Evidence and design

Settings Service may return `general.defaultApps` with unrelated entries but no
`home`, while System Profile reports stock Home for both `defaultApps` and
`idleApp`. Runtime recovery deliberately requires an independent settings read.
It must not substitute the profile's Home, an installed app, or a successful
launch for that observation.

Other projects support the hypothesis that an absent override is possible, but
do not establish this firmware's routing or recovery contract:

- [Glasshouse research](https://github.com/rorygallagher2024/glasshouse/blob/main/docs/development/TV-RESEARCH.md#glasshouse-home-on-webos-10-g5-webos-1031)
  records SAM launching an app declaring the Home category even with the setting
  absent on a G5. Its current
  [Home takeover](https://github.com/rorygallagher2024/glasshouse/blob/main/server/lib/home-takeover.js)
  mounts its app under LG Home's identity; that is a different mechanism.
- [Galaxy Launcher setup](https://github.com/guntiss/webos-galaxy-launcher/blob/main/tools/install-ssh.sh)
  explicitly writes a default app through SAM. Its
  [service](https://github.com/guntiss/webos-galaxy-launcher/blob/main/service/service.js)
  watches settings and foreground Home; it does not prove our restoration gates.
- [Hearth's Home hook](https://github.com/rudra-avatar/Hearth/blob/main/src/lib/homehookcmd.ts)
  installs a watcher that launches its app when LG Home appears. It does not
  supply an independent readback adapter for our profile recovery.

Our explicit setup finalization therefore materializes a stock override rather
than assuming one. After verifying the private pending runtime manifest, it:

1. Reads Settings Service. Existing valid `home` values are never rewritten;
   explicit null, empty or malformed values are refused.
2. For an absent key, refuses existing recovery readiness, routing overrides,
   staging files, trial journals, persistent intent or transaction bindings.
3. Requires System Profile to report stock Home for both routes and
   `idleApp.support` to be exactly true.
4. Durably records a mode-0600 `stock-home-initialization.json` in the existing
   private Root state directory before invoking the fixed SAM
   `setDefaultApp` operation with stock `com.webos.app.home`.
5. Independently reads Settings Service again. It requires explicit stock Home,
   unchanged other `defaultApps` entries, and unchanged complete profile data.
   Only then is the initialization receipt marked verified. The existing service
   status, root callback, activity and recovery-manifest checks still follow.

No new Luna URI, permission or service method is exposed: the provisioning process
uses the existing settings/profile reads and SAM write, with fixed payloads,
five-second deadlines and the existing bounded transport. The new private journal
contains the original settings object, profiles, schema and phase; it is recovery
evidence, not a diagnostic export. It is not copied into public reports.

An interrupted or unacknowledged submission is reconciled only through readback.
If the result cannot be proved, setup remains blocked and never repeats the
write. Do not delete the journal to force a retry. The explicit stock setting is
retained after failed setup, rollback and removal; the selected application is
still LG Home. This does not restore the original *absence* of the override.
No unrelated settings are intentionally changed.

Status/doctor, ordinary recovery and removal never perform this initialization.
Activation, guardian, emergency-stop and restoration comparisons remain strict.
The incomplete stock state is never admitted as an activation baseline.

## Delivery and acceptance

The correction must ship in newly provisioned matching Root/cytv packages, with
their private code and supervisor inventory rebuilt. An app-only update cannot
modify retained recovery drivers. Do not overwrite retained files on an already
failed installation or automatically resubmit it: use the supported coordinator
only when its operation, current state and exact private driver hashes permit
continuation. Otherwise preserve the state and obtain reviewed recovery advice.

Target-device testing must confirm that SAM accepts this stock-only write and
Settings Service then returns the explicit key, with both profiles and unrelated
settings unchanged. Then verify setup, guarded activation, triple-Home release,
ordinary controls and removal, followed by standby and true cold boot separately.
The original `provision-finalize-starting` report may have an additional startup
failure; this correction does not establish its absence or certify the model.
