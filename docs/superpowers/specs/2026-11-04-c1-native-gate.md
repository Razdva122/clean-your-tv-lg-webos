# Experimental C1 native Home gate

The maintainer approved this architecture in the originating chat on 2026-11-04.
Implement an explicit experimental routing backend for C1/native webOS 6 Home,
without changing the supported System Profile backend or adding automatic fallback.
This is source/host work only: no TV access, installation, compatibility admission,
release inventory changes or publication are authorized by this implementation.

## Requirements

- Keep the existing Root application ID and browser UI. Add a small static ARM32
  native gate and an independent native recovery process; neither recovery nor the
  gate's decision path starts Node or Python.
- A separately started, read-only existing Magic Remote observer can feed READY,
  PING, ESCAPE, LGHOME and LOST over a private inherited pipe. A closed pipe,
  malformed protocol, stale heartbeat or expired trial restores stock Home.
- The native guardian is already running and has observed input readiness before
  any mount. Mounts are volatile; the original native Home and optional CRIU
  checkpoint directories remain untouched beneath exactly owned bind mounts.
- Refuse foreign, stacked or unknown mounts; never unmount another integration.
  Recovery must check mount identity and propagation peers. Preserve ambiguous
  evidence and refuse update/removal while restoration cannot be proved.
- Return stock Home through its original /usr/bin/com.webos.app.home path, after
  verified release, with a detached bounded SAM request. Preload does not launch
  a foreground app. Errors latch the current attempt off until explicit enable.
- Use a distinct gate journal/status, not fabricated profile/defaultApps fields.
  App suspension while another app is foreground is normal, not a heartbeat fault.
- Admission requires explicit experiment selection, actual C1 model, webOS 6,
  ARM32 ABI, exact native target identity and no unresolved existing installation.
  A missing/denied/timed-out System Profile call is never automatic admission.
- The developer experiment remains opt-in and excluded from normal installation,
  updater and signed feeds until exact-package physical acceptance. Expose a
  concrete build/setup/control path; unsupported lifecycle operations must refuse
  before effects rather than silently use the profile backend.
- Do not patch key filters, disable system Home handling, restart SAM/WAM/the
  compositor, change system profiles or modify the read-only system image.
- Preserve triple-Home emergency escape and fail safe input supervision. Persistent
  intent, boot recovery, explicit Off and package removal must retain stop latches.

## Native interface

Fixed production state: /var/lib/clean-your-tv-root/c1-gate; volatile copy:
/tmp/clean-your-tv-root-gate/gate; target: /usr/bin/com.webos.app.home.
Native helper at private state runtime/c1-home-gate. No runtime path override or
PATH-based executable resolution. Host tests use compile-time fixture paths only.

Commands: --status, --restore, --guard TOKEN INPUT_FD READY_FD SECONDS and --selfcheck.
SECONDS is 0 for explicitly enabled persistence or 1..60 for a bounded trial.
With SAM's JSON launch envelope as its sole argument, perform the gate decision.
Guard consumes the inherited input pipe, publishes ARMED on READY_FD only after
mount/readback, and owns a monotonic two-second input lease. Close READY_FD after
publication. Signals and any input failure release owned routing. SIGKILL cannot
run cleanup: next gate invocation and boot recovery must detect a dead guardian.

The Python adapter writes a root-only fixed-line config before starting a guard:
CYTV-C1-GATE-1\ntoken HEX32\nboot UUID\ndev DECIMAL\nino DECIMAL\nsize DECIMAL\nmtime_ns DECIMAL\n
All entries and their order are exact; native parsing rejects unknown/trailing
content. Native helper owns its active/outcome records and stop latch. Status is
JSON with returnValue, backend=c1-native-gate, state, mounted, healthy, token and
stock_verified; profiles is null. Implementer documents any additional fixed fields
in its native README before the Python adapter consumes them.

## Acceptance boundaries

Host checks cover real native child lifetimes/protocol/timeout behavior, parsing,
mount ownership and inverse ordering with isolated fake mounts. Static ARM build
must be verified as ARM32 and executable. Actual mounts, SAM roles, CRIU, jail
propagation, Home/Back, standby, AC-off boot, media/audio, OTA/rollback and removal
on C1 remain untested and must be documented as such.
