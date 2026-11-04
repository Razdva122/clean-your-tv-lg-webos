# Experimental C1 native gate

This is an unpublished developer backend for issue [#298](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298).
It does not establish C1 compatibility. The normal Root profile backend remains
the default for supported firmware. There is no automatic fallback after a
profile-service failure and no stable-feed delivery of this experiment.

## Architecture and recovery

Admission requires an actual C1 model, webOS SDK 6, a 32-bit ARM runtime and a
fingerprinted native `/usr/bin/com.webos.app.home`. Installation requires a fresh
product state and an already available trusted Python runtime. It installs the
existing private application ID and recovery plumbing, leaving routing disabled.
The developer must separately request a bounded trial or enable operation.

Python owns admission and intent; a separately running static native guardian
owns the temporary Home bind, checkpoint hiding, input lease and inverse journal.
It uses the existing emergency input observer. Loss of the observer, expired
lease, emergency gesture, trial deadline or a handled signal restores only
identified owned mounts and records a durable stop. No system profile service,
stock application ID replacement, SAM/WAM restart or persistent key filter is
used. The native launch gate treats SAM preload as preload and redirects only
healthy foreground launches to the private application.

The helper can restore mounts without Python or the application. SIGKILL cannot
execute cleanup; a later native restore or boot reconciliation must perform the
inverse. Unknown mounts, foreign overlays, incomplete namespace evidence and
unverified stock identity block further changes while retaining recovery state.
The stop latch is never cleared by a periodic retry. Explicitly enabling a new
attempt creates a new token.

State lives under `/var/lib/clean-your-tv-root/c1-gate`; the selected backend and
admission fingerprint are recorded in `home-backend.json`. A verified executable
copy lives under `/tmp/clean-your-tv-root-gate`. These are root-owned private
paths. There are no new network endpoints. Both ordinary Root OTA and the system
updater reject experimental or orphaned backend evidence, including alternate
resume/baseline entry points. Use explicit restore/removal before returning to a
normal installation. Do not delete state or volatile files to bypass a refusal.

## Build and developer entry point

Build the helper as described in the [native protocol](../../root-edition/gate/README.md).
The builder validates a static ARM EABI5 executable, including its load segments
and absence of a dynamic interpreter:

```sh
python3 root-edition/build.py --output /absolute/new/bundle \
  --experimental-c1-gate /absolute/c1-home-gate
python3 root-edition/setup_gate.py install --ssh pinned-test-tv \
  --bundle /absolute/new/bundle
```

The second command displays the operation only. `--apply` executes it on a
separately authorized test device. The same developer entry supports `status`,
`trial` (60 seconds), `enable`, `restore` and `uninstall`. Switching an active
trial/persistent mode requires restoration first. The normal graphical installer
and updater do not expose this backend.

In experimental mode, Settings' Open LG Home and long Back release routing and
leave it off. The normal backend retains its existing one-time visit behavior.
There is no automatic visit/rearm helper in this experiment; explicitly enable
again when needed.

If Python is unavailable, the fixed native recovery command is:

```sh
/var/lib/clean-your-tv-root/runtime/c1-home-gate --restore
```

Do not remove the helper, its journal or the volatile source until native status
confirms `stock_verified:true`, `mounted:false` and `healthy:false`.

## Verification boundary

The [reporter's November 4 probe update](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298#issuecomment-6629123987)
and [updated handoff](https://gist.github.com/metaljay/8a1e63060c7fe7cc1d90fe34fe97e386)
were reviewed during implementation. Their observed `preload:"full"` is handled.
Their immediate close reply with a 9–10 second process exit requires at least a
15-second close/readback window. The adapter allows 18 seconds for process exit
and a shared 23-second window for foreground handoff. SAM can idle-relaunch Home
after that close; the adapter observes it without a competing explicit launch.
It preserves another foreground app and restores on a stalled handoff.
Those are reporter-observed
temporary probes, not acceptance of this native implementation. This backend
deliberately uses a native guardian rather than the proposed shell/Node wrapper
to keep recovery independent of either interpreter.

Host tests exercise actual native processes with fixture mount syscalls, parser
and child deadlines, lease/input failure, pending-journal recovery and exact
owned-alias removal. They do not exercise Linux bind propagation on a television.
Python tests cover admission, intent failure, backend dispatch, package isolation,
restore and updater guards. The ARM binary is cross-compiled; compilation is not
device acceptance.

Handled shutdown signals conservatively latch stop. Automatic persistent return
after normal shutdown is not promised without reliable device shutdown evidence.
Physical acceptance must separately cover stock preloading, Home/Back, triple
Home escape, guardian/observer/application/Python failure, CRIU and mount
namespaces, standby, AC-off boot, sound/media/HDMI, firmware changes and removal.
Record the exact model, firmware, package hashes and actual outcomes. No physical
C1 acceptance has been performed as part of this implementation.
