# Experimental C1 native gate

This is an unpublished C1 Beta backend for issue [#298](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298).
The common computer installer selects it automatically within the ordinary Root
flow. There is no separate beta installer, user flag or extra backend choice.
This does not establish physical C1 compatibility. The existing profile backend
and its normal bundles remain the path for supported firmware.

## Selection and recovery

Automatic selection requires an actual C1 model, webOS SDK 6, observed ARM32
userland and native Home, and an explicitly absent systemprofile service. A
permission refusal, timeout, malformed reply or a different device does not
select the experiment. Fresh installation is required; existing, partial or
orphaned product/recovery state must be inspected and recovered first. The
installer checks the device again before durable installation reservation and
fingerprints `/usr/bin/com.webos.app.home` before preparing the native attempt.
Before reading that executable or making admission Luna calls, the shared probe
checks each existing optional checkpoint directory and all of its ancestors.
It mirrors native leaf ownership/write-bit and non-symlink parent rules, allowing
a sticky writable ancestor but never a writable checkpoint leaf. A refusal stops
fresh setup before its device-side durable installation reservation and package submission;
it also stops activation before intent/guardian changes. Missing optional
checkpoints are not created. Keep vendor permissions and recovery data unchanged.
This read-only early check is not mount authority: the native guardian still
rechecks identity, paths, topology and owned-journal recovery at the effect boundary.
The computer may already have an upload/pending receipt; retain it for normal
status/recovery rather than clearing it or retrying automatically. This check
does not establish CRIU suppression or make an unsafe layout supported.

The common payload contains normal Root bundles and separate native C1 bundles
for both 1080p and 720p. The common install flow chooses the matching bundle,
installs the existing private application ID and recovery plumbing, then enables
Home control. It identifies this path as C1 Beta before installation and in the
completion result. No Root Updater or System Updater is installed for C1 Beta;
automatic updates are unavailable. The experiment is excluded from stable OTA
feeds. A package install or an enable reply is not physical device acceptance.

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
C1 full removal refuses before effects when other No-root components remain,
because this native path cannot verify their removal. Remove those through the
normal No-root flow first; retain unresolved recovery records and inspect them.

## Build and internal developer commands

The common installer build compiles the helper once with the existing pinned
Zig 0.14.1 dependency and embeds both C1 graphics variants. Its Root builder validates a static ARM EABI5 executable, including its load segments
and absence of a dynamic interpreter. The following low-level commands are for
internal development and deliberate recovery; users install through the common
installer:

```sh
python3 root-edition/build.py --output /absolute/new/bundle \
  --experimental-c1-gate /absolute/c1-home-gate
python3 root-edition/setup_gate.py install --ssh pinned-test-tv \
  --bundle /absolute/new/bundle
```

The second low-level command displays the operation only. `--apply` executes it
on a separately authorized test device. This internal entry also supports
`status`, `trial` (60 seconds), `enable`, `restore` and `uninstall`. Switching an
active trial/persistent mode requires restoration first. The common graphical
and console installers select the backend automatically; they expose no new
backend selector.

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

## Known activation blockers

The [November 4 candidate result](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298#issuecomment-6636248556)
is a failed activation, not acceptance. The reported nonsticky `0777`
`/mnt/lg/cmn_data` still fails native parent checks: a root-owned checkpoint child
does not prevent its writable parent from renaming it. Do not whitelist that
ancestor or change its vendor permissions. The package DATA reader's allowance
for shared writable directories does not authorize durable mount recovery there.

The two checkpoint-directory binds also did not prevent the observed CRIU zygote
restore. The exact cached descriptor/path or namespace mechanism is not established;
this change neither flushes CRIU nor restarts SAM/WAM/zygote. Actual activation
remains blocked until both mount anchoring/recovery and the CRIU execution path
have a verified safe design. The presentation fix addresses only the independent
SAM foreground/Root overlay mismatch. Its compositor response contract still
needs acceptance on the exact C1 firmware; missing or unsupported evidence fails
closed through normal restoration. No new TV run was performed for this change.

## Verification boundary

The [reporter's November 4 probe update](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/298#issuecomment-6629123987)
and [updated handoff](https://gist.github.com/metaljay/8a1e63060c7fe7cc1d90fe34fe97e386)
were reviewed during implementation. Their observed `preload:"full"` is handled.
Their immediate close reply with a 9–10 second process exit requires at least a
15-second close/readback window. The adapter allows 18 seconds for process exit
and a shared 23-second window for presentation handoff. SAM can idle-relaunch Home
after that close; the adapter observes it without a competing explicit launch.
It preserves another foreground app and restores on a stalled handoff. If SAM
continues reporting Home or an empty foreground, a fresh
[`surfacemanager/getForegroundAppInfo`](https://www.webosose.org/docs/reference/ls2-api/com-webos-surfacemanager/)
visible-surface list may instead prove the private Root overlay. Its application ID
and overlay window type must match; an explicit hidden flag or non-primary display
is rejected. The documented single-display response omits `visible` and
`displayId`; visibility follows list membership and omitted display follows the
existing runtime's primary-display convention. Malformed, denied, empty and
oversized responses cannot prove the handoff. Both queries share the original
deadline. Reappearance of the admitted stock executable after close is an error,
even with Root visible, and follows the existing native restore/stop path.
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
