# Experimental C1 Home routing

<a id="unpublished-capability-based-compositor-admission-364"></a>

## Experimental capability-based compositor admission (#364)

The installer extends the existing mount-free protocol to capability-admitted
Qt TVs with a stock ARM32 native Home. Model names and
SDK numbers are recorded observations, not an allowlist;
55NANO77SRA / SDK 9.2.2 / firmware 23.25.55 is the motivating report, not hardware
acceptance. This experimental path is packaged in published releases from v1.11.0; target-TV physical compatibility remains unverified.

Internal package, backend and lease names retain `c1` for compatibility. Existing
schema1 mount recovery and schema2 C1 identity/state/recovery formats are preserved.
The runtime applies the shared read-only environment checks to schema2 fresh
probes and explicit re-enable too: exact System Profile absence, stock native
manifest/vendor chain, no foreign state or covering mounts, and emergency input.
This tightens admission; restore remains independent of re-admission. New nonlegacy
admissions use schema3. A schema3 marker cannot be relabeled schema2 to bypass
admission. The common installer requires a payload advertising
`admission_schema:3` and a mount-free release with `compositor_admission:3`.

<a id="shared-root-runtime-variants-unpublished-beta-packaging"></a>

### Shared Root runtime variants

Ordinary Root packages this alternative. The common installer also embeds
it in the explicitly selected Node 0.12.2 Root Beta payload. Both variants use
the same host selector, device admission, Python backend, QML filter and native
guardian source. The guardian is compiled once and reused; only the Node closure
and its authenticated runtime policy differ. The QML filter is not a Node
module and remains byte-identical, without Node compatibility shims.

Successful Home profile reads retain the normal profile backend. Only the exact
absent-System-Profile reply permits alternative admission; permission errors,
timeouts and malformed replies never authorize it. Beta and ordinary bundles
cannot be substituted for each other. The host-only legacy prototype and old
mount backend remain excluded from the combined Beta build. Schema3 admission
now uses capabilities at every boundary (host preflight, device selection and
lease broker), without a numeric SDK floor. Schema2 retains its historical C1
identity rule. ARM32, input, ownership and foreign-state checks remain required.
A synthetic SDK 3.9.0/native-Home fixture passes; the actual #410 TV has not passed
those checks and no fix for that report is established.

The vendor filter files must resolve inside the protected vendor KeyFilters tree;
the common `/usr/lib/qt5` alias is accepted without writing through it. The live
filter verifies its Qt key/policy, timer, Luna and application-manager APIs before
subscribing. Missing APIs leave Home with LG and prevent guardian activation.

A configured KeyFilters field alone does not prove compatibility. The existing
guardian authenticates `/usr/bin/com.webos.app.home` and returns to LG by launching
that native application. Firmware with an in-compositor ribbon, a web/Flutter
Home or no native executable is refused. Glasshouse uses a different recovery
mechanism for its standalone/ribbon mode: it clears its Home mapping and injects
a 100 ms key press after a delay; its source also records a B8 HDMI regression
when forcibly closing the foreground app. That mechanism is not part of this
native-Home backend. See the [pinned implementation](https://github.com/rorygallagher2024/glasshouse/blob/0d5007aac997d23d2405cfe4f7aad42a1685bb1f/server/lib/home.js#L1335).

The same fresh-install, emergency-stop, explicit re-enable, restore and disabled
OTA rules apply to both runtime variants. No new state layout, LS2 permission or
network endpoint is added. Host tests are not physical TV acceptance.

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

This experimental backend addresses [#298](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298). The common computer installer selects it for eligible fresh C1 Root installations. It has no automatic updates and has not passed physical C1 acceptance. Existing normal Root bundles keep their profile backend.

## Selection and recovery

Admission requires a C1 model, webOS SDK 6, ARM32 native Home and an explicitly absent systemprofile service. Permission errors, timeouts, malformed replies and existing or orphaned recovery state refuse installation. The installer rechecks admission and fingerprints the stock Home executable before creating installation state.

New C1 bundles use marker schema 2 with routing `compositor-keyfilter-v1`. They intercept physical Home through a private compositor key filter and watch application lifecycle events for return after content closes. LG Home remains installed and may appear briefly during return. This is Home-key and lifecycle routing, not a replacement for every native Home launch.

The implementation uses no bind mounts, checkpoint changes, CRIU operations or permission changes to checkpoint directories. Existing schema 1 installations retain their original mount guardian and recovery path; do not replace their helper or marker to migrate them. A fresh installation is required after verified recovery/removal.

Triple Home, long Back, Open LG Home, lease loss, controller loss, trial expiry or handled shutdown latches routing off. Explicitly enable Change Home again after a safety or power stop. Boot reconciliation restores rather than automatically rearming. Unknown foreground state and conflicting SAM/compositor observations cancel return; a new content event cancels the one-second return delay.

State is root-owned under `/var/lib/clean-your-tv-root/c1-keyfilter` (0700), with volatile guardian state under `/tmp/clean-your-tv-root-keyfilter`. The selected marker remains `home-backend.json`. A native guardian requires independent emergency-input, lifecycle-controller and service-broker leases. The filter expires its own in-memory lease and passes Home to LG when authority is lost. Healthy Home requests and lifecycle returns both use the guardian's fixed `--home TOKEN` operation. Durable stop revokes authority before waiting for an in-flight launch and closing only the owned Root app, then requesting LG Home. Recovery never signals a journal PID. SIGKILL cannot execute guardian UI cleanup: the compositor lease expires independently, but explicit Restore may still be needed to close retained Root UI and reconcile the owned chain.

The private Root service owns the LS2 alias `com.webos.cleanyourtv.root.lease`. Root provisioning adds its name to the existing project activation record and snapshots the exact original; it is not advertised as a developer-package service outside the application ID. Only authenticated `com.webos.surfacemanager` may call its two methods, `c1Lease` and `c1Home`. The alias accepts no arbitrary command or application ID. The existing activation-file path remains registered by the package manifest; LS2 supports multiple names in its semicolon-delimited `Name` field. Vendor compositor roles are not edited. No network endpoint is added. The System Profile backend does not activate this alias.

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

### System images and interrupted fresh setup

Capability admission distinguishes a whole immutable `/usr` system image from
a mount replacing Home. A separate `/usr` mount is accepted only at filesystem
root `/`, on read-only squashfs backed by an internal MMC partition (major 179,
minor below 256), with both critical Home paths on that device. Writable,
subtree, stacked, overlay and unknown covering mounts remain refusals. The
[original device probe](https://gist.github.com/metaljay/8a1e63060c7fe7cc1d90fe34fe97e386#11-device-probe-record-2026-11-04)
records read-only `/usr` squashfs; it does not establish another TV's exact mount
table or compatibility.

An early native admission refusal can leave a host pending attempt without a TV
deployment journal. Missing files do not resolve that attempt. Explicit full
removal preserves it and fences original writers, then may use current verified
compositor support to prove stock Home without the unavailable Home settings
APIs. This path requires empty preserved/live CYTV routing evidence and a fresh
native identity, manifest, vendor chain, mount and emergency-input observation.
It records `stock-compositor`, never `never-applied` or installation success.
The final Node cleaner independently rechecks stock identity/hash, manifest,
vendor chain, exact missing service, mount layout and foreign Home integrations
before retirement and final acknowledgement. Later read-only inspection uses
the same current proof; it cannot delete anything.

After verified full removal, the installer selects a new native request through
the shared coordinator. The coordinator revalidates cleanup under its mutex,
moves only pinned component fences, and deploys the selected compositor bundle
under a new lease. The isolated deployment child inherits that mutex FD. The
previous request cannot resume or submit packages again. Initial fresh setup
and retained native recovery keep their existing paths; no updater is installed
by this handoff. These are source/host checks, not physical device acceptance.

The design follows compositor Home filtering and lifecycle return used by [Lightkeeper](https://github.com/chiotas/lightkeeper), including its [one-second C1 return timing](https://github.com/chiotas/lightkeeper/blob/5f26515fe6fd9cc74d29b04a342a2ed6abf424f0/app/service/lightkeeper-init#L63). The owned-chain approach also follows [GlassHouse](https://github.com/rorygallagher2024/glasshouse/blob/25ac2c93171f394884d9fde76e5e6bcedcb98e33/server/lib/remotekeys.js#L567). Root presentation requires its own visibility checks; the current candidate uses the ordinary full-screen Home CARD. The activation format follows the [LS2 multi-service parser](https://github.com/webosose/luna-service2/blob/5bc38aa348b35f5799f1bf9ed7c6cb513bc5f702/src/ls-hubd/file_parser.cpp#L468). LG's [service naming rules](https://webostv.developer.lge.com/develop/guides/js-service-usage) also apply to package metadata.

Host process tests cover independent leases, malformed state, stop persistence, child deadlines, launch/restore ordering and PID-reuse avoidance. Python and Node fixtures cover chain ownership, cancellation, conflicting foreground observations, stale callbacks, key pairing, unrelated buttons, binary authority, legacy recovery and package isolation. Static ARM cross-compilation is a build check. These checks do not establish TV Home routing, standby/cold boot, audio/media/HDMI or physical emergency behavior. No new owner tests or diagnostic collection are requested by this implementation.

## Retained schema 1 safety corrections

The legacy mount path retains #327 overlay/stock-return handoff checks and #330 read-only checkpoint preflight before installation or activation. Unsafe leaves or nonsticky writable ancestors refuse that path without changing vendor permissions or checkpoint data. These checks do not solve the historical CRIU restore failure. Schema 2 uses its own admission and never depends on checkpoint paths; the earlier checkpoint warning does not apply to fresh compositor-routing bundles. Legacy recovery remains available without new admission. Neither backend has new physical acceptance from this integration.
