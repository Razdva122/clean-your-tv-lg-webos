# Experimental C1 native Home gate

Source/host experiment only; physical C1 acceptance is not established.
Production paths are fixed: state `/var/lib/clean-your-tv-root/c1-gate`, config
`config`, active journal `active`, retained outcome `outcome`, durable stop latch
`stopped`, volatile executable `/tmp/clean-your-tv-root-gate/gate`, native Home
`/usr/bin/com.webos.app.home`. Optional checkpoint directories are
`/mnt/lg/cmn_data/checkpoint/com.webos.app.home` and
`/tmp/checkpoint/com.webos.app.home`; originals remain below empty-directory binds.

Commands: `--selfcheck`, `--status`, `--restore`,
`--guard TOKEN INPUT_FD READY_FD SECONDS`, or exactly one JSON launch object.
Config is the exact ordered seven-line format in the approved spec. The adapter
must atomically publish a root-owned mode-0600 config. A stop latch blocks its
matching attempt token; a distinct explicitly enabled token starts a new attempt.
Old-boot config remains readable by status/restore; guard/redirect require the
current boot. The uncovered native Home must match config dev/ino/size/mtime_ns.

Observer pipe protocol is newline-terminated ASCII: `READY`, `PING`, `ESCAPE`,
`LOST`, `LGHOME`. No token suffix. The private inherited pipe belongs to one
attempt. READY is required before any bind; PING renews a monotonic two-second
lease. ESCAPE, LOST, LGHOME, EOF, malformed/oversized input, lease/trial expiry
and signals all latch stop and restore owned mounts. Recovery opens stock Home
only after verified restoration. Guardian writes exactly `ARMED TOKEN\n` to
READY_FD after mount readback, then closes it; errors close without ARMED.
SIGKILL cannot run cleanup: the next invocation or boot `--restore` handles it.

All command responses except selfcheck are one JSON object with these fields:

- `returnValue`: boolean; false means refusal or incomplete recovery. Safely
  stopped status returns true.
- `backend`: `c1-native-gate`; `profiles`: null.
- `state`: `armed`, `stock`, `stopped`, or `blocked`.
- `mounted`: boolean, any exact Home/checkpoint bind present.
- `healthy`: boolean, current boot, live PID/start-time identity and fresh lease.
- `token`: lower-case 32 hex config attempt token, or empty if config is invalid.
- `stock_verified`: boolean, no relevant bind, stock identity matches config and
  inspected mount tables are complete/unambiguous.
- `stopped`: boolean, durable matching-token stop latch exists.
- `reason`: stable ASCII diagnostic code, or `none`.
- `guardian_pid`: integer, zero when absent.

Selfcheck returns `returnValue`, `backend`, and `selfcheck:true`; it requires no
config or mounts. Status is read-only and never starts Luna children. Launch
JSON must be an object; bounded strict parsing rejects duplicate/escaped keys,
malformed numbers, trailing data, non-ASCII strings and excessive nesting.
`preload:"full"`, `preload:true`, their `params` equivalents or `launchMode:"preload"` performs no
foreground launch. Healthy foreground redirect uses `com.cleanyourtv.root.preview`.
Failed/missing app launch restores stock. Luna uses fixed `/usr/bin/luna-send`
argv and environment, a separate process group, two-second bound and 16 KiB
output cap; only valid JSON with top-level `returnValue:true` succeeds.
Stock launch is detached and bounded, through SAM's stock application ID only
after `/usr/bin/com.webos.app.home` is uncovered and verified.

The helper precomputes up to 32 owned Home/checkpoint targets and same-namespace
propagated aliases from shared mount peer groups. Before binding, its durable
journal records staged source device/inode/mount root and each original target's
device/inode. After binding, complete mount-table readback records the IDs of
actual owned mounts. On inverse, each primary target is released before its
captured aliases; peer disappearance is accepted only when the original target
inode reappears. Checkpoints are restored before Home. Foreign overlays, stacked
or nested mounts, unknown aliases, unsafe paths, slave/unknown propagation, and
incomplete reads retain evidence and refuse effects. Propagation into another
visible process namespace is unsupported: admission refuses it before binding
with `unsupported_mount_topology`; the helper never calls setns. An inaccessible
namespace table also refuses admission. No foreign mount is unmounted and no
checkpoint snapshot is recursively deleted.

Both state and the volatile staging directory must be root-owned mode 0700,
with trusted non-symlink parents. Config and native records are mode 0600. The
adapter must stage and hash-verify COPY before starting the guard. The staged
source remains unchanged for the attempt; native creates adjacent `.empty1` and
`.empty2` directories when needed. `.lease` is volatile: PING never fsyncs the
durable journal. Durable records are changed at mount/inverse boundaries and
stop/outcome. SIGTERM/SIGINT/SIGHUP/SIGQUIT/SIGUSR1/SIGUSR2/SIGALRM conservatively
latch stop; there is no unverified shutdown exemption.

Limits: launch/Luna JSON 16 KiB, 512 JSON tokens, nesting depth 16; observer lines
15 uppercase characters plus newline; input readiness/lease and Luna children
two seconds; trials 1..60 seconds (0 explicitly persistent); 512 mount entries,
1 MiB mount table, 16 KiB mount line, 1024 distinct visible peer namespaces and
32 planned binds/aliases. Paths in the journal are canonical ASCII Linux paths
without whitespace; unsupported topology or bounds refuse before effects.

Build using the repository-pinned Zig 0.14.1:

```sh
zig cc -target arm-linux-musleabi -Os -static -s root-edition/gate/gate.c -o c1-home-gate
```

`CYTV_GATE_FIXTURE` permits compile-time fixture paths/syscalls in host tests;
production has no runtime path/environment override. Host tests use actual native
processes/parser/child deadlines with isolated fake mount syscalls, not real bind
mounts. Real mount, SAM roles, CRIU/jail propagation, standby, AC-off boot,
media/audio, OTA/rollback and removal require exact-package physical C1 tests.

Run host checks with `python3 -m unittest discover -s root-edition/tests -p
test_native_gate.py`. Fixtures compile only fixed temporary paths; the production
build cannot accept runtime path overrides. macOS sandbox restrictions can prevent
fixture-only `/bin/ps` access; run the host test outside that restriction. The
production guardian reads `/proc/PID/stat` directly and executes no shell.
The separate sanitizer harness covers the production JSON parser with malformed
inputs and 20,000 deterministic byte sequences under ASan/UBSan.

Control lock acquisition is bounded to 1.5 seconds for status/restore; guard startup
refuses a busy lock before effects. Guardian lease publication waits at most
500 ms for a concurrent status reader. ARMED uses a nonblocking atomic pipe write.
After a Luna timeout the process group is killed; reaping has a further 250 ms
bound, so even an uninterruptible child cannot hang the gate decision forever.

Config publication must briefly acquire the native `c1-gate/lock` flock around
its atomic rename, then release before invoking native commands. A Python-only
operation lock is insufficient for that publication. Native mutations recheck
the current config identity while holding the native lock. Guardian cleanup also
reloads and proves its token/PID/start authority; delayed old attempts cannot
write or inverse a new attempt. Off refuses a still-live guardian after its
three-second retirement deadline, retains the journal/mounts and does not report
stock proof. Even an unmounted starting guardian prevents stock_verified until
its cleanup authority has been retired.
