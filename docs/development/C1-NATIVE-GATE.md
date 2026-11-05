# Experimental C1 Home routing

This unpublished backend addresses [#298](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298). The common computer installer selects it for eligible fresh C1 Root installations. It has no automatic updates and has not passed physical C1 acceptance. Existing normal Root bundles keep their profile backend.

## Selection and recovery

Admission requires a C1 model, webOS SDK 6, ARM32 native Home and an explicitly absent systemprofile service. Permission errors, timeouts, malformed replies and existing or orphaned recovery state refuse installation. The installer rechecks admission and fingerprints the stock Home executable before creating installation state.

New C1 bundles use marker schema 2 with routing `compositor-keyfilter-v1`. They intercept physical Home through a private compositor key filter and watch application lifecycle events for return after content closes. LG Home remains installed and may appear briefly during return. This is Home-key and lifecycle routing, not a replacement for every native Home launch.

The implementation uses no bind mounts, checkpoint changes, CRIU operations or permission changes to checkpoint directories. Existing schema 1 installations retain their original mount guardian and recovery path; do not replace their helper or marker to migrate them. A fresh installation is required after verified recovery/removal.

Triple Home, long Back, Open LG Home, lease loss, controller loss, trial expiry or handled shutdown latches routing off. Explicitly enable Change Home again after a safety or power stop. Boot reconciliation restores rather than automatically rearming. Unknown foreground state and conflicting SAM/compositor observations cancel return; a new content event cancels the one-second return delay.

State is root-owned under `/var/lib/clean-your-tv-root/c1-keyfilter` (0700), with volatile guardian state under `/tmp/clean-your-tv-root-keyfilter`. The selected marker remains `home-backend.json`. A native guardian requires independent emergency-input, lifecycle-controller and service-broker leases. The filter expires its own in-memory lease and passes Home to LG when authority is lost. Healthy Home requests and lifecycle returns both use the guardian's fixed `--home TOKEN` operation. Durable stop revokes authority before waiting for an in-flight launch and closing only the owned Root app, then requesting LG Home. Recovery never signals a journal PID. SIGKILL cannot execute guardian UI cleanup: the compositor lease expires independently, but explicit Restore may still be needed to close retained Root UI and reconcile the owned chain.

The private Root service owns the LS2 alias `com.webos.cleanyourtv.root.lease`. Root provisioning adds its name to the existing project activation record and snapshots the exact original; it is not advertised as a developer-package service outside the application ID. Only authenticated `com.webos.surfacemanager` may call its two methods, `c1Lease` and `c1Home`. The alias accepts no arbitrary command or application ID. The existing activation-file path remains registered by the package manifest; LS2 supports multiple names in its semicolon-delimited `Name` field. Vendor compositor roles are not edited. No network endpoint is added. Ordinary Root does not activate this alias.

Restore retires the guardian and controller before removing exactly the owned configd chain entry. Foreign entries are preserved. Concurrent or unexpected edits, failed UI release and uncertain retirement retain recovery evidence. Do not delete journals, private files or stop latches to bypass refusal. Full C1 removal still refuses when other No-root components remain; remove those through their normal flow first. Root and System Updater reject experimental/orphaned state.

## Build and internal developer commands

The common builder compiles `gate/keyfilter.c` once with pinned Zig 0.14.1 into a static ARM32 executable and embeds both graphics variants. The existing backend key `c1-native-gate` remains for installer compatibility; the routing marker distinguishes the implementation.

```sh
python3 root-edition/build.py --output /absolute/new/bundle \
  --experimental-c1-keyfilter /absolute/c1-keyfilter-guard
```

Internal `setup_gate.py` supports status, trial, enable, restore and uninstall; applying operations requires a separately authorized device. Users install through the common installer without a backend flag.

If Python is unavailable, schema 2's native stop/recovery command is:

```sh
/var/lib/clean-your-tv-root/runtime/c1-keyfilter-guard --restore
```

It stops routing and requests stock UI. Python reconciliation is still required to remove the owned configd entry and prove complete restoration. Effective stock proof requires `stock_verified:true`, `mounted:false`, `healthy:false`, `filter_installed:false` and `routing_active:false`. Preserve evidence on any failure.

For existing schema 1 mount installations, retain their original recovery command:

```sh
/var/lib/clean-your-tv-root/runtime/c1-home-gate --restore
```

Do not remove that helper or its journal until its native stock/mount proof and normal recovery checks succeed.

## Source basis and verification boundary

The design follows compositor Home filtering and lifecycle return used by [Lightkeeper](https://github.com/chiotas/lightkeeper), including its [one-second C1 return timing](https://github.com/chiotas/lightkeeper/blob/5f26515fe6fd9cc74d29b04a342a2ed6abf424f0/app/service/lightkeeper-init#L63). The owned-chain approach also follows [GlassHouse](https://github.com/rorygallagher2024/glasshouse/blob/25ac2c93171f394884d9fde76e5e6bcedcb98e33/server/lib/remotekeys.js#L567). The Root overlay requires its own visibility checks rather than assuming a CARD application. The activation format follows the [LS2 multi-service parser](https://github.com/webosose/luna-service2/blob/5bc38aa348b35f5799f1bf9ed7c6cb513bc5f702/src/ls-hubd/file_parser.cpp#L468). LG's [service naming rules](https://webostv.developer.lge.com/develop/guides/js-service-usage) also apply to package metadata.

Host process tests cover independent leases, malformed state, stop persistence, child deadlines, launch/restore ordering and PID-reuse avoidance. Python and Node fixtures cover chain ownership, cancellation, conflicting foreground observations, stale callbacks, key pairing, unrelated buttons, binary authority, legacy recovery and package isolation. Static ARM cross-compilation is a build check. These checks do not establish TV Home routing, standby/cold boot, audio/media/HDMI or physical emergency behavior. No new owner tests or diagnostic collection are requested by this implementation.
