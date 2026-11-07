# Experimental C1 Home routing

## Unpublished capability-based compositor admission (#364)

The next installer extends the existing mount-free protocol to capability-admitted
Qt webOS SDK 6–9 TVs. Model names are recorded observations, not an allowlist;
55NANO77SRA / SDK 9.2.2 / firmware 23.25.55 is the motivating report, not hardware
acceptance. This section describes source preparation, not published support.

Internal package, backend and lease names retain `c1` for compatibility. Existing
schema1 mount recovery and schema2 C1 selection are unchanged. New nonlegacy
admissions use schema3. A schema3 marker cannot be relabeled schema2 to bypass
admission. The common installer requires a payload advertising
`admission_schema:3` and a mount-free release with `compositor_admission:3`.

Before device installation reservation and before activation, admission checks
the observed model/firmware/SDK, native ARM32 Home, 32-bit interpreter/input ABI,
protected stock native app manifest, vendor Qt Home-filter chain/scripts and
independent read-only emergency channel. System Profile must explicitly report
its exact absent-service reply. Permission denials, unknown replies, C++
compositor generations, Home-covering mounts, known other Home integration state
and nonvendor filters refuse this path. An existing Home binding in Input Hook
also refuses admission; that configuration is only read and is never exported or
modified. No foreign integration is removed or repaired. A Magic Remote product
name alone is insufficient: the input channel must advertise Home and Back.

Schema3 configd writes use `volatile:true`; exact readback is mandatory. The
durable inverse precedes writes, and failure retains the transaction. Restore
first stops native routing and retires the lifecycle controller, then reconciles
only the owned filter against the current chain, preserving other entries and
metadata. Controller records include a boot UUID, so previous-boot PIDs are never
followed or signaled. Changed native Home identity permits owned-filter removal
after confirmed retirement, but retains disabled recovery state and refuses to
claim stock proof or delete evidence.
If configd resets the volatile filter, the lifecycle controller stops its lease
and cancels return; it never automatically reinstalls the filter.

Boot reconciliation restores rather than rearms. Lease loss, safety stop and
power recovery require explicit Enable. Changed model, firmware, SDK or Home
fingerprint requires fresh admission; recovery does not require fresh admission.
No SAM/input daemon restart, Home/checkpoint mount, CRIU change, input injection
or network endpoint is added. Normal OTA remains disabled; there is no in-place
migration from another Home integration.

Local fixtures cover schema3 selection, broker authority, volatile/readback
transactions, foreign changes, interrupted writes, boot/PID identity, changed
Home recovery and legacy schema protection. Existing filter/native tests cover
independent leases, paired releases, unrelated keys and emergency stops. Physical
controls, sound, HDMI, standby, cold boot and recovery remain untested. No reporter
operation or further diagnostics are requested.

The temporary configd selection is informed by [Home Chooser's live filter
research](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/docs/home-key-hook.md).
No vendor script is copied or patched; this implementation retains the existing
private filter and native lease barrier instead of Home Chooser's executable gate.

## Existing C1 selection and recovery

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

The design follows compositor Home filtering and lifecycle return used by [Lightkeeper](https://github.com/chiotas/lightkeeper), including its [one-second C1 return timing](https://github.com/chiotas/lightkeeper/blob/5f26515fe6fd9cc74d29b04a342a2ed6abf424f0/app/service/lightkeeper-init#L63). The owned-chain approach also follows [GlassHouse](https://github.com/rorygallagher2024/glasshouse/blob/25ac2c93171f394884d9fde76e5e6bcedcb98e33/server/lib/remotekeys.js#L567). Root presentation requires its own visibility checks; the current candidate uses the ordinary full-screen Home CARD. The activation format follows the [LS2 multi-service parser](https://github.com/webosose/luna-service2/blob/5bc38aa348b35f5799f1bf9ed7c6cb513bc5f702/src/ls-hubd/file_parser.cpp#L468). LG's [service naming rules](https://webostv.developer.lge.com/develop/guides/js-service-usage) also apply to package metadata.

Host process tests cover independent leases, malformed state, stop persistence, child deadlines, launch/restore ordering and PID-reuse avoidance. Python and Node fixtures cover chain ownership, cancellation, conflicting foreground observations, stale callbacks, key pairing, unrelated buttons, binary authority, legacy recovery and package isolation. Static ARM cross-compilation is a build check. These checks do not establish TV Home routing, standby/cold boot, audio/media/HDMI or physical emergency behavior. No new owner tests or diagnostic collection are requested by this implementation.

## Retained schema 1 safety corrections

The legacy mount path retains #327 overlay/stock-return handoff checks and #330 read-only checkpoint preflight before installation or activation. Unsafe leaves or nonsticky writable ancestors refuse that path without changing vendor permissions or checkpoint data. These checks do not solve the historical CRIU restore failure. Schema 2 uses its own admission and never depends on checkpoint paths; the earlier checkpoint warning does not apply to fresh compositor-routing bundles. Legacy recovery remains available without new admission. Neither backend has new physical acceptance from this integration.
