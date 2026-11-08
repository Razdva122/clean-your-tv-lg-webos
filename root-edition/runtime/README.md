# Root runtime contract

Release 1.6.0 uses Root/infrastructure 0.7.0. See
[Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases) for published
downloads, [release limits](../../docs/RELEASE-1.6.0.md) and
[artifact-bound acceptance](../../docs/history/2026-11-02-release-1.6.0-final-acceptance.md).
Existing System 1.1.2 remains pinned; fresh physical System 1.2.0 and general
supervisor migration are not accepted by the recorded C3 tests.

Install these Python files under `/var/lib/clean-your-tv-root/runtime` as root-owned files without group/world write permission. Python 3.9+ and `/usr/bin/luna-send` are required; Root setup also requires TV Node.js 8+,
Homebrew services and supported ARM32 input. With system Python, invoke
`/usr/bin/python3 /var/lib/clean-your-tv-root/runtime/cli.py COMMAND` as root.
For a managed-runtime installation use its retained verified interpreter binding;
do not substitute a missing system interpreter or change global PATH.
[Optional Python](../../docs/OPTIONAL-PYTHON.md) is provisioned only by setup,
never by status, restore or removal; referenced runtime slots remain retained.

- `status`: read actual system profiles and independent Home setting, journal and recovery integrity.

- `trial`: activate **com.cleanyourtv.root.preview** for at most 60 seconds using a detached rollback guardian. Refuses any unresolved journal, unexpected baseline, missing Home registration or missing recovery provisioning.
- `restore`: conflict-checked removal of only the owned override, rescan, restore stock Home and verify the full original profiles. Retries bounded transport failures. Exit 2 means recovery is unresolved; preserve state for retry/investigation.
- `boot`: restore the previous routing transaction first. A confirmed active intent may then start a fresh protected transaction and open the candidate. Failsafe or interrupted startup disables intent; duplicate callbacks preserve only a healthy matching guardian.
- `enable`: activate persistently after automatic input, guardian and routing checks; requires the old helper to be stopped. Failed readiness restores LG Home. No user confirmation or timed session.
- `confirm TRANSACTION`: diagnostic promotion of that exact live trial. Requires fresh input/guardian heartbeats, effective candidate routing and at least five seconds before rollback. No confirmation means automatic rollback.
- `intent-trial`: diagnostic intent-bound trial, useful for regression checks; separate from user activation.

An absent Settings Service Home key remains an incomplete runtime readback.
Only explicit setup can initialize an absent override to stock LG Home, after
recording intent and checking unchanged profiles and independent readback;
runtime commands never do so. See [setup-only initialization](../../docs/development/ROOT-HOME-READBACK.md).

The independent updater uses root-only internal commands `suspend-update TX`,
`finish-update TX` and `abort-update TX` with its exact 32-character transaction
identity. Suspension preserves the prior confirmed Home preference before
restoring LG Home. After automatic application-health success, finish restores an
enabled preference only when the suspension snapshot, boot and reservation still
match and failsafe is absent. Activation uses the normal guardian/input checks.
There is no manual post-update confirmation. Abort never activates Home.

Private `update-home-resume.json` records the suspension and one activation
attempt; `update-home-cancel.json` records explicit/emergency off without waiting
for the update lock. Reconciliation never replays an uncertain activation. A
fresh reservation starts a new suspension cycle, including a later rollback of
the same update. Successful No-root updates preserve their independent Helper
state instead of using this Root runtime.

For the retained rollback live-authority window, capture/staging order and unresolved
old-CLI forward cancellation, see the [2026-11-01 investigation](../../docs/history/2026-11-01-root-home-settings-intent.md).

A confirmed normal shutdown retains the Home override, generated profile and transaction binding so bootd can select Clean Your TV as its first app. A normal new-session start may continue an exactly owned retained route without removing its override, rescanning profiles, rewriting Home or launching a foreground app. It preserves the original recovery baseline and file identity, rotates transaction/generation/token, and arms fresh input supervision plus an independent guardian before waiting for the normal-init gate. Uncertain ownership, missing predecessor evidence or a surviving predecessor guardian/supervisor/reader refuses continuation and retains conservative recovery. Explicit exit, input failure without a shutdown signal, and failsafe recovery restore LG Home.

The shutdown monitor accepts only fresh transaction/session-bound evidence.
Its local tvpower subscription must observe ON before Active Standby/Power Off;
initial OFF snapshots, unknown replies and lost subscriptions grant no authority.
Only actual pushes refresh the existing five-second evidence window. Returning ON
or losing/invalidating the stream revokes its private volatile `.power` proof.
No reconnect loop or ENODEV exception bypasses input recovery. A restored old
observer defers enabled old-session intent to boot dispatch; escape, failsafe and
package loss still override it. See [evidence and limits](../../docs/development/ROOT-COLD-BOOT.md).


Startup identity combines the kernel UUID with
one private volatile session nonce, rather than clock-dependent `btime`. The
nonce and its lock live beside the normal-start marker in
`/tmp/clean-your-tv-root-boot`; creation is serialized, records are ownership/type
checked and atomically published, and duplicate callbacks reuse the identity.
The supervised C3 AC-off/snapshot test cleared an inert `/tmp` probe. This
lifetime assumption requires verification on other snapshot firmware; kernel UUID
reuse alone does not establish a new session. Corrupt/indirect session records
are rejected, not silently reset.

<a id="native-startup-choices-unpublished-candidate"></a>

## Native startup choices

Boot dispatch only restores/rearms guarded Home routing. It never launches the
launcher over a foreground app. The former boot/wake presentation functions and
worker are removed. The power subscription remains responsible for bounded
shutdown evidence and diagnostic edge counts; a wake count grants no launch.

The native source policy prepares the existing owned EIM input before a later
startup. `startup-policy.json` stores schema 1 and exact boolean `tv`, `youtube`
and `hdmi` preferences. TV groups LG Channels/Live TV and defaults on; YouTube
and HDMI default off. The native-source controls are disabled with an explanation
while Change Home is off. This per-TV state does not extend the legacy launcher
or installed System supervisor profile schema.

A guardian-owned observer consumes foreground and remembered-input settings
subscriptions. It keeps one coalescing bounded worker, rereads real source/input
state and requires matching active intent/session/binding, fresh input/guardian,
owned native receipt/entry and startup preference. It only selects the fixed
Root input, or withdraws that exact owned selection to the recorded displaced
pair. No observer action launches, adds or adopts an app/input. Unknown/transient
foreground cannot authorize selection; a later protected app withdraws our
selection while a different native input remains untouched.

The existing native receipt has a `selecting` phase with fixed `pending` direction
`select` or `restore`. The inverse is durable before the effect. A lost response
is reconciled by matching readback; it cannot authorize blind resubmission.
Off/emergency/update/rollback cleanup retains route-first priority and handles
this owned pending state. Each optional native sequence retains the 1.5-second
budget. Foreground/native reads and the write remain separate platform RPCs;
source changes are rechecked and observed supersession cancels pending work.

See [native startup sources](../../docs/development/ROOT-NATIVE-INPUT.md) and
[standby evidence interpretation](../../docs/development/ROOT-WAKE-DIAGNOSTICS.md).
Published first-screen and delayed-presentation observations remain historical;
CI and installed bytes alone do not accept the new policy on a TV.

Runtime state is `/var/lib/clean-your-tv-root`; owned profile is `/var/webos-profile/override/clean-your-tv-root.json`. Both directories must be root-owned and not group/world writable, and must reside on the same filesystem for crash-safe hard-link publication. Runtime never edits app files, stock libraries, zoom behavior, or the existing no-root launcher.

Recovery provisioning is `recovery-provision.json`: version 1, mode `recovery-only`, absolute `boot_callback`, and `files` mapping absolute callback and every runtime Python path to its SHA-256 hex digest. All files and ancestors must be trusted. The installed callback must invoke the fixed runtime `cli.py boot`. The installer finalizes this manifest only after boot activity registration is verified. A valid manifest establishes installed-byte integrity, not hardware acceptance.

Device-specific assumptions requiring hardware acceptance: webOS systemprofile getProfiles/debug/rescan methods; defaultApps and idleApp schema; settingsservice general.defaultApps readback representing SAM's setting; settingsservice setSystemSettings preserving general.defaultApps; appCategory home registration; stock app `com.webos.app.home`; Linux `/proc` guardian identity; `/var/luna/preferences/webosbrew_failsafe`; filesystem durability; boot activity delivery under reboot and failsafe. Trial requires all three original routing values to name stock Home and idleApp.support true.

[AOD/category preservation and recovery compatibility](../../docs/development/ROOT-AOD-PRESERVATION.md)
describes the version 2 active journal and version 1 restored bridge.

Local tests exercise policy, real file ownership/conflict handling, subprocess timer readiness, abrupt publication process death, provisioning gates, isolated identity and restoration. They do not establish TV boot, remote Home/Back routing or power-loss behavior.

## Existing No-root helper

Trial preflight refuses an existing controller PID marker or running known No-root relay, including ambiguous stale markers. It rechecks before publishing the profile. It never edits the helper's control or blocked files and never relaunches that app. The legacy `stop` command creates the same blocked latch as a user disable, while manual relaunch clears it; an automatic stop/relaunch cannot preserve user intent. Explicitly stopping the old helper is therefore required before this candidate's trial; it remains stopped afterward. Transparent pause/resume requires a separate transaction-aware helper protocol and is not provided here. Do not launch the helper during a Root trial.

During hardware acceptance, use three short Home presses within two seconds to
disable the current No-root helper first (through 0.6.13: hold Home about two seconds). After Root restoration, verify stock routing and explicitly use the existing helper button to re-enable No-root if desired. Neither runtime nor uninstaller removes stale controller markers automatically; investigate stale state rather than blindly deleting it.

<a id="rc15-persistent-candidate"></a>
## Persistent activation

Settings exposes Turn on Home control. Activation automatically records durable
intent after readiness checks; it does not disable watchdog protection. The
internal startup deadline remains a recovery backstop until readiness succeeds.
The independent guardian then uses a renewable two-second input-loop lease. The
supervisor checks the guardian's own pulse. Volatile health files live under a
root-owned `/tmp/clean-your-tv-root-health`; frequent heartbeats do not write flash.

Three short Home presses within two seconds or Home settings → Return to LG Home disable
intent before restoring original routing. A fault does the same. No-root helper
is never automatically resumed. A later explicit enable is required after a fault,
failsafe or emergency exit. Installation alone does not enable Root mode.

Permanent activation was introduced in RC15. The
[1.4.0 acceptance](../../docs/RELEASE-1.4.0-ACCEPTANCE.md) is historical model/build
evidence; [current release limits](../../docs/RELEASE-1.5.3.md) retain the unresolved
standby report. Source bundle metadata is not a compatibility certificate.
The historical provisioning schema name `recovery-only` remains an integrity
receipt format, not a promise that a confirmed boot intent cannot activate Home.


Rooted SDK DATA may have ordinary `0777` modes.
The corrected private readers require independent original package hashes; they
do not repair shared permissions or execute shared source. Missing/conflicting
current, transaction or own-package proof keeps automatic Home rearm inhibited,
while independent private LG Home restoration remains available. Deliver the
changed helper closure through checked fresh setup/rebootstrap, preserving
existing recovery archives and unknown-operation records. Updating Installer
alone does not replace retained private product code. Root remains disabled until
an explicit activation through the normal setup/settings flow. See the
[candidate authority and acceptance record](../../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#cold-boot-data-authority-correction).


<a id="candidate-original-130-ota-contract"></a>
## Original 1.3.0 OTA contract

Audio commands now use the existing `cli.py audio <command>` entry point and
`cli.py audio worker <generation> <boot|watch>`. No additional executable path is
installed. Root service audio requests use validated payloads on the existing
read-only status and mutating enable methods, preserving original LS2 grants.
The optional policy stays off by default; Home off/emergency cancellation is
unchanged. [Compatibility and rollback evidence](../../docs/development/ROOT-OTA-13-COMPATIBILITY.md)
describes the authenticated retained-rollback anchor receipt and offline limits.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="root-candidate-runtime"></a>

Native source selection requires an acknowledged, live guardian observer. Its
root-private volatile `.startup` health record binds the transaction/session to
the actual guardian PID and process-start ticks; it is not durable Home authority.
Loss before activation completes makes post-ready handling withdraw the owned
priority. Close invalidates eligibility first, waits at most two seconds for an
in-flight operation lock, then attempts one fresh guarded withdrawal. No native
RPC replay or late application launch is introduced.


## Retained Home startup continuation (#422)

`boot_gate.py` also owns the root-private `boot-continuation.json` schema-1
record. It holds exact prior/next lifecycle, binding and routing journal snapshots;
it stores private routing/lifecycle data and must not be published as a raw
diagnostic. It is written atomically with
0600 permissions under the existing 0700 Root state directory. Cleanup classifies
it as routing evidence and preserves it in the finite inverse backup before
removal. The immutable runtime file inventory remains unchanged.

The continuation admits only a confirmed enabled prior session, the exact
original profile payload/device/inode/mode/link count, matching effective routes,
and independently absent predecessor protection processes. The original stock
baseline is never inferred from current routing, replaced, or marked restored.
A new transaction prevents stale processes or health files acquiring authority.
Snapshot resumes with surviving/uncertain old processes use conservative recovery;
continuity is not promised for that state.

Before authority changes, a detached bootstrap monitor acknowledges readiness.
Its fixed deadline and private parent-death pipe invoke ordinary recovery even
if the dispatcher dies between record, intent, journal and binding writes. The
record repairs only exact saved states or their ordinary recovery transitions.
An interrupted handoff is recovery-only on subsequent dispatch; it cannot enable
Home. The bootstrap monitor is disarmed only after the fresh guardian and input
reader acknowledge readiness. The ordinary independent 60-second deadline is
never restarted after gate waiting, and its 20-second recovery reserve remains.

Before the normal init marker exists, ordinary startup and a genuine failsafe
cannot yet be distinguished. A recovery-only input supervisor protects this
bounded classification interval: READY/PING do not authorize persistent health,
and triple-Home, input loss and the two-second heartbeat watchdog still recover.
The normal-marker/cleared-failsafe gate waits at most 35 seconds, additionally
limited by the original recovery reserve. Missing marker, uncleared failsafe,
package loss, exhausted budget, observer failure or explicit Off disables and
restores LG. No code clears failsafe or automatically re-enables emergency-stop
state. Only the verified normal gate releases ordinary current-session health;
active intent still requires fresh input and guardian proof.

This is a runtime sequencing correction, with no loading screen or UI launch
restriction. Host simulations and subprocess failure injection do not establish
physical remote, standby, cold-boot, audio, signed update or rollback acceptance.
