# Root runtime contract

Published 1.5.2 contains Root 0.6.1; the unpublished 1.5.3 candidate selects
Root 0.6.2. Historical tests retain their exact artifact scope; see the
[current release and acceptance limits](../../docs/RELEASE-1.5.3.md).

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

A confirmed normal shutdown retains the Home override, generated profile and transaction binding so bootd can select Clean Your TV as its first app. Startup recovery still restores the old transaction before arming fresh health protection. Explicit exit, input failure without a shutdown signal, and failsafe recovery restore LG Home.

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

After a healthy guarded restart, the dispatcher makes one optional foreground
request only for normal active hardware startup, LG `homeAutoLaunch=on`, and a
final foreground read showing stock Home, Live TV, or the narrowly verified
native Channels surface described below. An already visible user app
or Clean is left alone. Missing/slow optional APIs do not disable healthy Root.
These calls use a 0.5-second reply deadline (up to another 0.5 second for child
termination cleanup); no operation lock is held over launch, so an explicit off
can complete during an in-flight request. There is no retry after an unknown
launch outcome or duplicate boot callback. Foreground read and launch are separate
platform calls, so a user app switch after that last read can race the one request.
The existing power subscription also recognizes a genuine same-stream ON → OFF →
Active wake, independently of boot callbacks. Initial/reconnected OFF or Active,
unknown/malformed states and duplicate Active snapshots do not request Home.
A single optional worker keeps RPCs off the power reader and guardian heartbeat
path; OFF, processing/uncertain power data, stream loss and teardown revoke its
in-flight eligibility. It never queues stale wakes or retries a launch. This path
requires the same startup session, current active/enabled intent, effective Home
routing, fresh input health and independent guardian; stopping/unconfirmed intent
is left to recovery and is never promoted by wake. Native last-input preference
and unknown/user foreground are preserved. It does not add a new service,
permission, endpoint, durable state or boot hook.

The C3 firmware boot trace and the supervised no-input cold cycle identified
`mgg4.5.channelplus` as the firmware Cover App's boot-launched partner TV surface. Its
reported `systemApp` is false; it is not treated as a system app or as authority
to classify other CP apps. The optional metadata read admits only that exact ID,
`type=web`, `vendor=LifeStream ltd.`, boolean `CPApp=true` and
`internalInstallationOnly=true`, with both `folderPath` and `activeFolderPath`
exactly `/media/cryptofs/apps/usr/palm/applications/mgg4.5.channelplus`.
A developer/alternate path, missing or changed identity fields, any other ID,
and unknown apps remain preserved. Metadata failures never revoke healthy Home
routing. After metadata verification the foreground is read again, preserving an
app selected during that RPC; all input/intent/session/failsafe and native Home
preference checks still apply. This classification is shared by the boot and
proven genuine-wake paths and introduces no watcher or boot-hook change.

As with the existing stock Live TV policy, manually selecting this native TV
surface in the boot or genuine-wake window cannot be distinguished from firmware selection
by the final snapshot; the native Home-on preference permits one boot/wake request
in that case. Third-party/unknown foreground remains protected. Foreground read
and launch remain separate platform calls, so the existing final-read/launch
race is unchanged. This is the same policy boundary as Live TV, not a claim of
complete user-input or launch provenance on arbitrary apps.

Presentation diagnostics classify foreground as Root, stock Home, Live TV,
verified native channel, or other/missing, and record whether a nonempty firmware
first-app ID matched. They do not persist private app IDs or inventories. The
recorded `preserved-foreground` outcomes and empty `firstAppId` are historical
old-candidate observations. Host regressions reproduce that native-TV rejection
and verify the corrected metadata gate; installation/physical acceptance of the
new code is still required separately for RC-START-05 and RC-START-08. Active
intent and installation alone do not establish automatic foreground acceptance.

For the unresolved Root 0.6.1 standby report [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171),
the 1.5.3 candidate adds diagnostic coverage only. Every invoked wake presenter,
including early cancellation/session/intent/health refusal, records its outcome
and fixed last-check stage through the existing private `boot-decision.json`.
The power reader also keeps one root-owned, atomic volatile snapshot per transaction
at `/tmp/clean-your-tv-root-health/<transaction-sha256>.wake`. It records a fixed
stream/transition event, session/transaction, monotonic uptime, revision, primed/on/
asleep flags, observed OFF-edge count and eligible-wake-edge count. Duplicate Active
snapshots do not rewrite it. It never stores firmware replies, arbitrary state
strings, foreground IDs, error messages or app inventories. This file has no role
in authorization or recovery; diagnostic I/O failures leave existing decisions
unchanged. No new durable state, permission, endpoint or reconnect is introduced.
See [standby investigation and record interpretation](../../docs/development/ROOT-WAKE-DIAGNOSTICS.md).

Manual enable and short Home retain their existing behavior. See
[cold-start investigation and acceptance](../../docs/development/ROOT-COLD-BOOT.md).

Runtime state is `/var/lib/clean-your-tv-root`; owned profile is `/var/webos-profile/override/clean-your-tv-root.json`. Both directories must be root-owned and not group/world writable, and must reside on the same filesystem for crash-safe hard-link publication. Runtime never edits app files, stock libraries, zoom behavior, or the existing no-root launcher.

Recovery provisioning is `recovery-provision.json`: version 1, mode `recovery-only`, absolute `boot_callback`, and `files` mapping absolute callback and every runtime Python path to its SHA-256 hex digest. All files and ancestors must be trusted. The installed callback must invoke the fixed runtime `cli.py boot`. The installer finalizes this manifest only after boot activity registration is verified. A valid manifest establishes installed-byte integrity, not hardware acceptance.

Device-specific assumptions requiring hardware acceptance: webOS systemprofile getProfiles/debug/rescan methods; defaultApps and idleApp schema; settingsservice general.defaultApps readback representing SAM's setting; applicationmanager setDefaultApp; appCategory home registration; stock app `com.webos.app.home`; Linux `/proc` guardian identity; `/var/luna/preferences/webosbrew_failsafe`; filesystem durability; boot activity delivery under reboot and failsafe. Trial requires all three original routing values to name stock Home and idleApp.support true.

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
