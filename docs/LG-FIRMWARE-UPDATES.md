# LG firmware update blocking (since 1.2.0)

This optional Root Edition control is included in 1.2.0 (Root 0.3.0). Open **Home settings → LG firmware updates**. It controls LG's TV
firmware updates, including firmware security updates. Clean Your TV's own
**Software updates** screen remains separate.

## Use and limitations

- Homebrew Channel must be installed, running with root access, and expose its
  configuration API to Home. If unavailable or denied, the switch is disabled;
  check Homebrew Channel and use **Check status**. No permission escalation or
  alternate system-file modification is attempted.
- The switch shows Homebrew's saved `blockUpdates` preference. A fresh read
  verifies each change. It does **not** certify that update servers are blocked
  now, that an update was not downloaded, or that root will survive an update.
- Changes take effect when Homebrew's startup script runs on a real TV restart.
  Use Homebrew Channel's restart action; ordinary standby/wake may not run it.
  Turning the setting off also needs a restart to remove Homebrew's existing
  boot-time overlay. Other tools/router rules can still block updates.
- Some root startup methods run after LG's first update check. Notifications can
  therefore remain even with the preference on. Network blocking on your router
  may be necessary. Existing downloaded updates and notifications are not deleted.
- Homebrew owns the setting. Changing it here changes the same preference shown
  in Homebrew Channel. It remains after removing or rolling back Clean Your TV;
  use either interface to turn it off and restart. No previous Homebrew setting
  is silently restored on uninstall.
- After an error, timeout or concurrent change, check status before retrying.
  A command may have succeeded even if its reply did not arrive. The UI does not
  automatically repeat a failed write. A stale view is re-read before writing;
  Homebrew does not provide a cross-client compare-and-swap transaction.

This control uses the existing public
`org.webosbrew.hbchannel.service/getConfiguration` and `setConfiguration` APIs.
Only `{blockUpdates: boolean}` is written; SSH, telnet and failsafe flags are
never sent. There is no new private recovery-service API, persistent CYTV flag,
daemon or mount. Compatible app updates can deliver the UI without changing the
pinned recovery-service contract; a denied/unsupported Homebrew API stays
unavailable. The TV's own auto-update setting is distinct and is not modified.

Upstream evidence: [configuration API](https://github.com/webosbrew/webos-homebrew-channel/blob/main/services/service.ts),
[startup implementation](https://github.com/webosbrew/webos-homebrew-channel/blob/main/services/startup.sh),
and [early update-check limitation](https://github.com/webosbrew/webos-homebrew-channel/issues/96).

## Unreleased diagnostics correction and webOS 11 access (#110)

Root SSH access does not grant Root Home access to Homebrew's Luna API. On the
maintainer's C3 (webOS 11.2.0, firmware 43.21.71, Homebrew 0.7.3, installed Root
Home 0.4.0), read-only investigation confirmed that root can read configuration
with `root: true`, while a client matching Root Home's generated LS2 client-name
pattern receives a denied `getConfiguration` response (`returnValue: false`,
error code `-1`). The generated Home client grants do not intersect Homebrew's
configuration API grants. This models the application's LS2 access boundary;
it is not a test of the newly built UI in the running application.

Homebrew 0.7.3 exposes its elevated API to `public`, its own service group and
ares CLI. Ordinary webOS 11 apps no longer receive `public`. Upstream
[Homebrew #233](https://github.com/webosbrew/webos-homebrew-channel/pull/233)
([merged permission change](https://github.com/webosbrew/webos-homebrew-channel/commit/50fa99e1f08959b665b2e34d0d85cb2222c4c2c9))
adds `lunabus.query` for elevated APIs. At investigation time, the latest
published Homebrew release is still
[0.7.3](https://github.com/webosbrew/webos-homebrew-channel/releases/tag/v0.7.3).
Do not assume a source merge is an available supported package or that this
change alone grants every client access: the installed Home client still needs
an intersecting supported grant. See also the related Installer investigation
[#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

The candidate UI distinguishes denied API access, missing service, Homebrew
running without root, timeout and unsupported configuration replies. Raw remote
errors and configuration fields are not displayed. A denied call leaves the
switch disabled and directs the user to change the setting in Homebrew Channel
itself, whose own API grant is separate. The diagnostics change alone does not enable the denied API or establish
active blocking. The following candidate access correction provides a separate
CYTV-owned grant; its lifecycle and device acceptance are tracked separately.

No Homebrew ACL, flag, overlay, service or package was modified during the
read-only C3 investigation. The saved preference was unchanged in reads before
and after. On/off
writes, a real restart, effective server blocking and the new UI on the TV were
not tested. Preserve the restart/security-update limitations above.

## Candidate: Root Home configuration API access (#110)

The candidate provides a CYTV-owned grant for Homebrew `getConfiguration` and
`setConfiguration`, scoped to Root Home's existing private control group. It
works independently of Homebrew's `public`/`lunabus.query` grants and does not
edit Homebrew ACLs, binaries or configuration flags. LS2 grants a whole method,
not individual JSON fields; the existing controller still writes only the
strict boolean `blockUpdates` field and verifies it by reading back.

Fresh Root provisioning registers this grant after validating recovery. An
optional registration failure is reported as `firmware_permissions_registered:
false` without failing core Home/recovery setup; verify the actual control and
use the explicit maintenance command rather than treating core readiness as API
access acceptance. For an
existing supported Root installation, use the **new candidate installer**, with
the saved trusted Root connection and no pending installation/removal:

```sh
cytv enable-firmware-access --edition root
```

The source checkout needs its normal verified embedded payload built first.
The command verifies bundled source, installed Root identity, retained recovery
code, original ACL hashes and pending operations. It runs the permission helper
in the pinned TV Python, without replacing retained executable files. It takes
the product lock and modifies only the SDK-generated Root Home manifest plus
CYTV-owned permission data. Reopen Root Home and use **Check status**. If LS2
still uses cached Homebrew API registration, stop other Homebrew work and
restart Homebrew normally before retrying; do not patch its ACLs or restart the
TV automatically just to test this command. A running Homebrew service can cache
its API groups in either direction: restart it normally after revocation too
before treating effective access as revoked.

The new data consists of `firmware-permissions.json` (durable transition and
original SDK manifest), `firmware-permissions.lock`, and
`permissions/homebrew-configuration.api.json` under the existing private Root
state. The original four recovery ACLs, their snapshot, recovery code/proof,
Home intent and bootstrap/update selectors remain unchanged. Writes preserve
manifest UID/GID/mode. Interrupted registration is resumed with the same command;
a conflicting file, pending update/removal or changed proof stops the operation.

To revoke this API access, without changing the Homebrew preference:

```sh
cytv disable-firmware-access --edition root
```

Revocation restores the current SDK manifest without the extra reference,
removes the API data and records disabled access so automatic maintenance does
not re-enable it. To change firmware blocking afterward, use Homebrew itself or
explicitly enable API access again. Original Root removal restores the old
client ACL, revoking Root Home's control group; SDK package removal removes the
referencing manifest. Remaining inert permission data stays with archived Root
recovery evidence. No external permission manifest is left behind.

Revocation authenticates the private receipt, recovery proof and exact protected
LS2 manifest; it does not require installed SDK `appinfo.json`. It can therefore
remove an owned grant when that metadata is missing, malformed or in a writable
application directory. Enabling access retains the strict SDK identity and
permission checks. This does not repair an unsafe SDK tree or make enabling
access supported there; use Homebrew itself while that installation needs review.

The candidate runtime reconciles the reference on boot and after a complete
update, under the existing product/control locks. Failures never prevent Home,
emergency or rollback recovery. It uses the existing `runtime/cli.py` path, so
it does not expand the original 1.3 OTA executable inventory. A host-side grant
repair leaves an older installed runtime unchanged: after a later app-only
update regenerates the SDK manifest, rerun `enable-firmware-access` until that
runtime is upgraded through a supported complete update or computer migration.
All package rebuild/version decisions remain candidate gates.

On the maintainer's C3 / webOS 11.2.0 / firmware 43.21.71 / Homebrew 0.7.3,
the verified candidate helper registered the grant for installed Root Home
0.4.0. LS2 scan alone left the running Homebrew API groups cached. Its normal
quit and root-preserving restart loaded the new control-group grant. Root Home
client reads then succeeded; an unrelated `getAppInfo` method and the Root
Updater client remained denied. All 52 checked Root app/service files, the
retained code/proof and original four ACLs/snapshot stayed byte-identical;
Homebrew ACL/manifest bytes and other configuration fields stayed unchanged.
The maintainer confirmed that the actual TV switch became available and toggled.
No new TV app/runtime package was installed for this test.

This is existing-installation access acceptance, not fresh-setup, physical
signed upgrade/rollback/removal or multi-device acceptance. Standby/cold boot,
revocation on the TV and active firmware-server blocking were not tested.
Active blocking still requires the separately documented real restart and
effective-host/network check. A successful API write alone does not
prove that LG updates are blocked.

## Acceptance and further device checks

Automated tests cover strict boolean values, partial configuration writes,
missing/non-root/denied API, rejected/malformed replies, stale preference,
concurrent operations, uncertain write outcomes and readback. UI checks cover
remote navigation, focus return, delayed replies and ten translated catalogs.
These do not establish physical TV compatibility.

On a rooted TV, record model, firmware, Homebrew version and startup method.
Compare Homebrew's preference before/after each direction. Confirm SSH, telnet,
failsafe, Home routing, emergency exit and volume/mute are unchanged. Test a
real restart separately from standby, inspect effective update blocking without
starting a firmware installation, and record any remaining update prompt.
Test preference changes from Homebrew while this screen is open. Verify a
supported Home update/rollback and that the preference remains Homebrew-owned.
See the [1.2.0 acceptance record](RELEASE-1.2.0-ACCEPTANCE.md) for the
maintainer confirmation and its evidence limits. Original-device checks remain
separate.


<a id="explicit-package-permission-repair-candidate"></a>

## Explicit package permission repair (1.5.0+)

Installers since 1.5.0 provide an explicit maintenance option for an installed
Root package whose own SDK directories retained group/other write permissions:

```sh
cytv enable-firmware-access --edition root --repair-package-permissions
```

This is not part of ordinary enable, boot reconciliation or revocation. Under
the existing product and firmware-permission locks, the helper first validates
pending-operation exclusions, protected recovery code/ACLs, the exact LS2 manifest
and permission receipt. The current private updater publication and checked cache
select the expected installed package; SDK metadata never selects that authority.
All expected files must match, be singly linked and belong to root. Unknown
entries, symlinks, special modes, foreign owners, unsupported or incomplete private
proofs and conflicting versions stop repair before permissions change.

The helper holds directory/file descriptors, checks path identities and narrows
only group/other write bits on the package's own app/service/package leaves.
Shared SDK containers are excluded. It rechecks bytes, paths and the private
publication afterward, then applies the original strict SDK identity check before
ordinary API registration. Existing file contents, ownership, executable bits,
profile, Home intent/emergency-off, recovery data and Homebrew preferences are
preserved. No retained executable is replaced: checked bundled helper/dependency
sources run from stdin in the pinned isolated Python.

If the platform later restores writable SDK modes, ordinary enable still refuses
them. Recheck state and use the same explicit repair option when needed; it
authenticates the current private package again. This option does not enforce
SDK modes across platform lifecycle changes or automatically chmod on boot.

If interrupted after a permission change, some own paths may already be hardened.
The command does not restore unsafe permissions or report success; retry the same
explicit command after checking state. Changed bytes or paths still prevent a
grant. Cached Homebrew API groups may require its normal service lifecycle refresh
as described above; this option never restarts the TV or changes firmware blocking.
A source/test result is not device lifecycle acceptance or published delivery.
