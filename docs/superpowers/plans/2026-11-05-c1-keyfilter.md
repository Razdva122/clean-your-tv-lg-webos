# C1 compositor routing implementation plan

Goal: implement the previously selected Home-key/lifecycle-return path without
Home/checkpoint mounts, while retaining independent input/stop protection and LG
Home restoration. User authorized implementation and explicitly forbids further
C1-owner test requests. No TV operation is part of this work.

Architecture: retain experimental backend name `c1-native-gate` for installer
compatibility, but explicitly select schema 2 / routing `compositor-keyfilter-v1`.
Old schema 1 mount recovery remains readable and uses the old helper/bundle only.
New bundles carry a distinct native health guardian plus Python orchestration,
a private compositor filter and a Root-service subscription broker. Normal
profile bundles and OTA do not select this path.

## Shared interfaces

State: `/var/lib/clean-your-tv-root/c1-keyfilter`, private 0700. Native helper is
`runtime/c1-keyfilter-guard`; fixed filter `runtime/c1-home-filter.js`. Volatile
native state is `/tmp/clean-your-tv-root-keyfilter`, private0700. No runtime path
overrides; compile-time test roots only. Marker `home-backend.json` schema2 has
backend,experimental,native_sha256,admission,routing; admission keeps the exact
legacy C1 model/firmware/ARM32/Home identity shape. Legacy binary is not replaced
in an existing installation; fresh setup only.

Native config: `CYTV-C1-KEYFILTER-1`, then token,boot,dev,ino,size,mtime_ns in the
same ordered key/value syntax as the legacy gate. Native commands: --selfcheck,
--status, --lease, --restore, --home TOKEN and
--guard TOKEN INPUT_FD CONTROL_FD READY_FD SECONDS.
Input observer and lifecycle controller have separate inherited channels. Both
send READY/PING and must remain fresh within2s; ESCAPE/LOST/LGHOME/EOF/invalid data,
trial expiry or handled signals latch stop. --lease is called by the service
broker and renews a separate <=2s broker lease; it cannot clear stop. ARMED TOKEN
is emitted only after both channels and broker are fresh. No mount syscall or
checkpoint access exists in this helper. Guard checks unchanged Home identity.

Native JSON includes returnValue,backend:`c1-native-gate`,routing:
`compositor-keyfilter-v1`,state(stock/armed/stopped/blocked),mounted:false,healthy,
stock_verified,stopped,token,guardian_pid,reason,profiles:null. Raw stock proof only
covers original executable and retired guardian; Python additionally requires
its configd filter entry absent before projecting effective.stock_verified.
--restore latches stop before retirement and observes the recorded PID/start
identity without sending signals to a saved PID. Active/stop records survive uncertainty. Heartbeat
storage is volatile; no fsync/configd write per heartbeat.

Python `c1_keyfilter`: selection(root,uid), probe(), prepare(root,native_sha256,
admission,uid), native(args,root,uid), validate_native(value), status(root,uid),
execute(mode,transaction=None,root,uid), owns schema2 only. Shared legacy
`c1_gate.selection/execute` dispatches schema2; legacy data remains strict. Probe
validates C1 identity and readable configd chain; it does not inspect checkpoint
paths. prepare installs private state/intent; enable verifies recovery, persists
inverse intent before chain write, installs exactly own filter entry and readback,
starts persistent controller+observer+guardian, waits ARMED and publishes active.
Restore stops native lease/controller before removing own chain entry and readback.
Current chain is re-read; foreign entries/edits are preserved. Unknown or modified
owned entries retain evidence and refuse destructive cleanup. Computer receipts
remain retained as normal. No routine rearm or failed-attempt retry.

Filter export to compositor: `init()` and `cytvC1HomeKey(key,pressed,autoRepeat)`;
LS2 subscribe to `com.webos.cleanyourtv.root.lease/c1Lease` with subscribe:true.
Replies include returnValue,subscribed,backend,routing,token,healthy,sequence.
Only strictly shaped fresh sequences arm a <=1500ms in-memory timer; failure,
subscription termination, malformed/repeated sequence or expiry disables override.
Unrelated keys always NextPolicy. Home keydown/up are paired, repeats do not launch.
With healthy lease physical Home requests the fixed `c1Home` endpoint on
`com.webos.cleanyourtv.root.lease`; it invokes only native `--home TOKEN` for
the fresh selected token and launches the fixed private Root ID. With no lease
Home passes to LG. Pending callbacks cannot grant a stale lease. No mount,
configd heartbeat or file access inside filter.

Service broker polls fixed verified native helper --lease <=500ms, deadline<=1s,
only while compositor subscription exists. It validates the selected schema2 marker,
root ownership/private paths and binary hash before exec. No Python dependency.
Never republishes cached healthy result after failure, timeout, stale child or
subscriber generation. Native helper presence alone cannot activate normal Root.
Register c1Lease separately from serialized recovery handlers. Bound subscriber
count; revoke on cancel. Register the fixed `c1Home` request separately; it accepts no command or app ID.
Native `--home TOKEN` checks fresh guardian/input/controller/broker health and
serializes its fixed Root LS2 launch under a separate effect lock against
stop/restore; health polling remains available while the launch runs. Python lifecycle returns use this same barrier. Once restore
returns, a stale token cannot dispatch Root. No generic command/payload arguments
or HTTP exposure.

Lifecycle controller subscribes to SAM getAppLifeEvents, validates bounded events,
and considers stop of prior CARD or stock Home CARD appearance as return hints.
Before every delayed launch: check own token/guard lease, active power, Root
visible surfaces, generation and current content; cancel on new content, power
loss, explicit Off/LG Home, overlay visibility or uncertainty. Root OVERLAY needs
separate visible state, not the Lightkeeper previous-CARD-self heuristic. No Home
process is killed or closed. Triple Home and long Back stop routing; explicit
LG Home stops watcher before launch, with no automatic rearm.

## Work units and verification

- [x] Native unit: new gate/keyfilter.c + host process/parser tests. Red first,
  then verify independent channels, broker lease, stop/PID reuse, trial, signals,
  malformed state and interpreter-independent native restore. No gate.c semantics
  changed unless extracting identical common utilities is justified and tested.
- [x] Python unit: new runtime/c1_keyfilter.py and focused fixture tests. Red
  first; chain ownership/readback, no0777/checkpoint dependency, inactive/active
  projection, interrupted writes, cleanup, event replay/cancellation and recovery.
- [x] Compositor/service unit: private filter JS, service broker, integration and
  Node VM tests for missing service, dropped lease, key pairing, repeated/stale
  reply, unrelated keys, broker binary authority and timeout.
- [x] Root integration: build/bundle/installer/provision/runtime selection, native
  compiler, recovery manifests, LS2 permission and UI proof guards; preserve old
  recovery and normal Root paths. New payload is selected only in fresh C1 setup.
- [x] Documentation: update developer contract and 13 localized guides; state Home
  key/return override (LG Home can briefly appear), experimental/no OTA, no new
  owner tests and no unsupported claim of physical acceptance.
- [x] Independent final review, affected Python/Node/native/build suites; cross
  compile static ARM32 guard. Target the implementation PR at release/next and link #298 without closure;
  reconcile issue status. Do not touch candidate version/inventory/build selection.

## Verified implementation

Host validation on 2026-11-05: complete Root suite 1083 tests passed; installer
suite 765 passed (72 skipped); setup 235 passed; System Updater 132 passed.
Native guardian 40 process tests passed, including launch/restore ordering,
saved-PID avoidance, stale broker startup and idempotent absent-Root close.
Root service/UI Node suites and generated closure/loopback transport checks passed.
The final static ARM32 guardian and C1 bundle were built with pinned Zig 0.14.1
and passed bundle hashes, ELF/load-segment and package identity checks. Exact old
Node runtimes were not configured. No TV operations or physical C1 acceptance
were performed, and no new reporter tests or diagnostics were requested.

Independent review findings were fixed: conflicting SAM/compositor foreground,
source-backed return delay, stored-PID signalling, stale broker pulses, developer
service naming/manifest reachability, legacy OTA inventory, absent-Root close,
and the installer's initial launch crossing Off. New C1 launches use the native
effect barrier; legacy schema 1 recovery ordering remains unchanged.
