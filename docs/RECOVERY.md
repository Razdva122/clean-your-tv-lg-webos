# Recover TV controls or an interrupted installation

> **Experimental compositor routing (#364):** experimental compositor recovery stops routing
> before removing only its own filter. Safety/power stops require explicit
> re-enable. If Home identity changed, the owned filter can be released after
> retirement, but full stock proof remains unverified and recovery evidence is
> retained. Do not delete journals or remove another launcher's state. See
> [capability-based admission](development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).

> **Release 1.9.0:** see [versions, tested scope and recovery limits](RELEASE-1.9.0.md). C1 Beta is fresh-install only, selected automatically in the common installer; normal OTA is unavailable and physical C1 acceptance is pending. Historical results below retain their original artifact scope.

## Return to LG Home

Press Home **three times within two seconds**, releasing between presses. This
stops Home interception and opens LG Home; it preserves preferences. Helper
through 0.6.13 uses holding Home for about two seconds instead.

The emergency stop persists across startup. To resume No-root, open **Home Helper**,
choose **Start Helper** and confirm. To resume Root, turn **Change Home** on in
Home settings. Opening Home alone does not restart a stopped Helper.
**Open LG Home** only visits LG Home once; it keeps the saved Home choice.

Updating packages does not restart a stopped No-root Helper. After updating to
a release containing a fix for the fault, use **Start Helper** above to resume
Home control explicitly. Do not delete `blocked`/`stopped` markers manually or
expect an update to clear an emergency stop.

If controls fail again, leave LG Home active and save diagnostics. Do not repeatedly
clear stop flags after a fault. A Quick Access assignment to Home offers another
way to open it, but does not restart Helper.

<a id="no-root-watchdog-recovery-unpublished-candidate"></a>

## No-root watchdog recovery (Helper 0.6.20)

Helper 0.6.20 can recover a transient relay/controller watchdog timeout,
including the standby timing reported in #155, with at most five attempts in ten
minutes. Stop and triple Home remain persistent stops and require explicit
**Start Helper**. Repeated faults or failed input cleanup also leave Helper
stopped. Physical No-root acceptance remains unverified for the exact Helper transition; see
[recovery behavior and limits](HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

<a id="ssh-identity-changed"></a>

## SSH identity changed after a reset or SSH change

If a report shows `ssh-identity-changed` / `BadHostKeyException` at
`ssh-connect`, the presented SSH host key differs from the saved trusted key.
CYTV stopped before authentication and before inspecting or continuing recovery
on the TV. This differs from first-use **Connect and remember this TV?**:
that prompt cannot approve replacement of an existing pin. A factory reset or
reroot may explain a new key, but does not verify the TV's identity.

Keep the original saved connection/profile, SSH keys, trust records, diagnostic
reports and pending-operation receipts privately. A retained
`uninstall / coordinator-submitted` describes earlier work; it is not the cause
of the host-key mismatch or proof of what removal completed. Do not clear
`known_hosts`, delete/recreate the profile or pending records, disable host-key
checks, or repeat removal, installation, reset or rooting to bypass this stop.

Before maintainer-assisted trust recovery, the owner must independently establish
that the endpoint is the intended TV and verify its current host-key fingerprint
through an already trusted access path or a trusted local/on-device method.
Record which independent method was used, the verified fingerprint and the
owner-confirmed reset/SSH-change history for private maintainer review. A key
presented by the blocked network connection, an address or a reset history alone
is insufficient. Do not upload keys, profiles or raw diagnostics publicly.

CYTV currently supplies no supported automatic host-key replacement or re-trust
command. Even after independent identity verification, maintainers still need a
reviewed, profile-preserving trust-recovery procedure before recovery can resume.
Keep the pending operation intact until that procedure and the subsequent trusted
inspection establish the allowed next action.

## Interrupted setup or removal

<a id="unreleased-local-recovery-storage-messages"></a>

### Local recovery storage messages

These messages are included from published v1.12.1 onward; v1.12.0 did not include them.

A local recovery storage refusal concerns the computer or Android app storage,
not a TV package-status reply. It can mean that a directory's ownership or
permissions did not pass verification, before the recovery file was read. It does
not by itself mean that saved data disappeared. Keep the original files and
permissions unchanged and save a diagnostic report for review; do not publish
private paths, profiles or recovery capsules. New reports distinguish these
categories without exposing paths or account names; see
[local diagnostic fields and limits](development/INSTALLER-DIAGNOSTICS.md#local-recovery-storage-next-candidate-201).
An older incompatible observer still uses separately confirmed removal through
the existing recovery journey. A clearer message does not permit replay or prove
the original package outcome.

<a id="next-candidate-original-operation-recovery-and-full-removal"></a>

### Original-operation recovery and full removal (published v1.11.0)

These instructions apply to published v1.11.0 and later. For removal, select **Uninstall Clean Your TV** on desktop or
Android (`cytv uninstall`) using the saved TV connection. Confirm the removal
once. A failed or partial installation does not need to complete first: remove
known project apps/files that are present and skip items that are absent.

1. CYTV stops project controls and removes present project packages and files.
2. When asked, disconnect the TV from power, reconnect it and wait for the TV and
   network to return. Standby and Quick Start are not a full restart. CYTV does
   not restart the TV automatically.
3. Select **Try again**. This repeats the same approved removal goal on the same
   saved connection, without a recovery wizard or another initial confirmation.
   The installer checks the actual boot change and remaining files, then performs
   the final sweep. Success requires both removed and verified-clean results.

If the connection is interrupted, check it and select **Try again**. Existing
installation history remains available; an old generic failure is not assigned
an invented cause. If the OS denies access, use the requested Root connection.
If another operation is actually running, wait for it to finish and try again.
A failed check stays visible; it is never converted to green completion. Keep
keys and original reports, and do not reinstall or clear Android app data to
retry removal. Missing files are skipped; absence is not itself an error.

In v1.11.0 and later, failed or interrupted setup offers recovery directly. If No-root setup cannot continue, confirm full removal once. Removal automatically retries transient connection loss and a busy CYTV worker up to three attempts. If Root access is required, choose **Connect using Root** for the same TV; verified Root cleanup also finishes its blocked No-root removal. A failed Root activation attempts to restore and verify LG Home without repeating activation. Cancellation with unfinished work keeps a diagnostic report and recovery actions. Emergency-stop state remains unchanged.

**v1.13.0:** verified full removal leaves the TV ready for a new Root or No-root installation. Minimal inactive removal receipts prevent old work from resuming; do not delete them manually. Finish recovery first if removal or its current checks are incomplete.

**Next installer update (not yet published):** on older TVs without a separate
LG Home app, No-root removal can use a freshly verified LG stock screen and may
switch to Live TV. Keep the TV on and follow any restart request. Continue with
**Try again** using the original saved connection; do not delete journals, clear
Android app data or reset the TV. The updated Root remover also verifies a
matching completed cleanup when the local recovery record still shows pending;
matching history alone does not establish current absence.

Returning to LG Home alone remains separate from removal. Emergency controls
above stay available. For setup recovery, eligible Root can still finish with
LG Home and Home control off; that goal does not require activating Clean Home.
Physical Home, sound, standby and cold boot are separate observations. A restart
used by removal does not certify any of those checks. Candidate source tests do
not establish compatibility or successful recovery on a reporter's TV. See the
[maintained failure-injection matrix](development/INSTALLER-RECOVERY-MATRIX.md).

The version-specific recovery sections below describe their published scope.
The Remove action is available even when earlier setup is incomplete.

<a id="interrupted-setup-or-removal-in-110"></a>
<a id="interrupted-no-root-installation-in-the-unpublished-140-candidate"></a>

In 1.6.0, use cytv (desktop or Android) to select the **same saved
TV connection** and choose **Review recovery options**. Console: `cytv recover`.
If setup finds a retained operation, it enters this journey and stops before a
fresh installation.

1. Confirm **Check recovery options?** (default **No**). Inspection does not
   reinstall/remove packages. Root inspection may stage and execute verified
   support code; it is not a passive TV read.
2. A verified Root installation can offer **Finish Root setup?** with a separate
   default-No confirmation. Existing Root/updater checks run again before activation.
3. No-root can offer **Remove remaining Clean Your TV packages?**, separately
   confirmed with No by default. In 1.6.0 the package-service idle guard must
   succeed before this offer and again before removal. The 1.7.0 exception
   for an unstarted removal is described below. Removal restores LG Home
   and may reset Home preferences. **New installation never starts automatically.**
4. Unknown, denied, busy, incomplete or conflicting state stops the journey and
   offers a diagnostic report. Keep local/TV journals and the saved connection;
   do not repeat removal, delete receipts or reset Developer Mode to force setup.

`--yes` cannot approve recovery checks or changes; noninteractive recovery stops.
A displayed plan is advice only, never authorization or a saved resume token.
Legacy operations can remain blocked. This does not supply missing terminal
installer evidence for #201 or certify recovery on #216's TV.

<a id="failed-root-activation-unreleased"></a>

### Failed Root activation

The published 1.9.0 installer can offer **Finish Root setup?** for a retained profile-backend
activation after LG Home has been restored. Use the same saved connection and
**Review recovery options** (`cytv recover`). The separate default-No confirmation
still applies. Before offering or continuing, checks must prove disabled intent,
restored routing/binding, stock LG Home, no failsafe/update block, matching installed
files and verified Root Updater recovery. A linked product installation must also
be complete and current. Unknown, busy or conflicting evidence keeps setup blocked.
The original activation receipt is archived locally before the explicit attempt;
packages are not reinstalled and no recovery journal or failsafe flag is deleted.

For an explicit replacement after a failed profile-based Root activation, choose
**Set up my TV** with the original saved connection, then **Reinstall Root**.
The installer validates its new bundle, performs verified full removal and then
installs its own runtime and activates Root. This is a new, confirmed installation;
recovery inspection does not automatically replace packages. If cleanup needs a
restart or cannot be verified, replacement stops and the saved removal remains
available. Preferences are removed, so back them up first. See
[Root reinstallation](MAINTENANCE.md#root-reinstallation-through-the-installer-unreleased-355).
C1 Beta recovery is unchanged. This retry path does not update the retained TV runtime.

This improves recovery and diagnosis; it does not establish the original cause or
successful recovery of [issue #334](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/334).
The updated Root runtime records a fixed health-context refusal before supervisor
recovery. Existing runtime logs cannot be upgraded retroactively: retain the
original evidence and do not edit installed runtime files or integrity receipts.

<a id="candidate-finish-verified-root-setup-with-home-control-off"></a>

#### Finish verified Root setup with Home control off

If activation keeps failing on the retained runtime, do not repeatedly select
**Finish Root setup?**. The installer offers a separate default-No choice,
**Finish setup with LG Home and Home control off**, directly in the recovery menu,
followed by **Finish Root setup with Home control off?** (default No).
It is offered only for eligible pending profile-backend setup that passes the same
strict disabled/restored routing, binding, file, completed product and Root Updater
checks. Confirmation repeats those checks. C1 Beta and unknown state are excluded.

This action archives the original activation receipt on the computer and resolves
only that local pending activation. LG Home, installed packages, TV recovery
journals, rollback baseline and Home-off preference are preserved. It does not
repair activation, update runtime files or prove Home-button operation. Keep the
original diagnostic reports and saved connection.

After this separate completion, use **Enable updates for all TV components**
(`cytv enable-system-updates --edition root`) only if no compatible System Updater
is already prepared. Existing supervisor state must use its matching recovery;
do not repeat bootstrap over it. Open Home Root manually, then **Settings →
Software updates → Update all** for a verified signed complete set. Preparation
and update still enforce their original compatibility, transaction, baseline and
rollback checks; stop on refusal and retain evidence. A launcher-only IPK cannot
update the private runtime. This flow is published, but physical recovery on the reporting TV remains unconfirmed. [Update requirements](UPDATES.md).

Current reports include a passive retained-runtime snapshot: project component
versions, runtime release metadata and fixed health-refusal categories. A legacy
`generic` refusal has no predicate detail. `historical-tail` is historical evidence;
`since-enable` bounds newly appended records around the host enable command but
cannot identify their first causal failure or exclude another TV-side writer.
No activation is run to fill a report. Missing/unsafe/unavailable reads remain
explicit and never grant recovery permission.

In 1.6.0, retain the original failed-attempt report.
New reports separate a saved first error from later checks and include a filtered
Doctor/status result. Successful setup/status/restore also offer an export. This
does not add a recovery path or make missing historical evidence available.
[Diagnostic fields and limits](development/INSTALLER-DIAGNOSTICS.md).

Recovery checks installer state before offering an allowed recovery action.
An unknown package outcome is not automatically retried. Returning to LG Home
alone does not finish removal. The removal confirmation cannot be bypassed with
`--yes` or approved by noninteractive setup.

<a id="unreleased-uncertain-no-root-package-operations-201"></a>

### Uncertain No-root package operations (#201)

**Check TV status** keeps the pending install/removal journal even if app versions
and hashes match or manually removed apps are absent. Those observations do not
prove installer completion. If **Review recovery options** fails at `package-status`
or app-list verification, stop and retain diagnostics and recovery files. There
is no supported file-only bypass; do not delete the receipt, reset Developer Mode
or repeat removal to force installation. Restore/LG Home availability does not
establish package completion. This restriction is a source correction, not a
verified recovery fix for either reporter's TV.

The installer calls `applicationManager/dev/listApps`; an SSH probe of
`applicationManager/listApps` is a different method. Further recovery design
requires the [exact endpoint and terminal-authority evidence](development/NO-ROOT-PACKAGE-AUTHORITY.md#remaining-evidence).

<a id="no-root-removal-stopped-before-package-submission-unreleased"></a>

### No-root removal stopped before package submission (1.7.0)

With the 1.7.0 installer, choose **Review recovery options** for the
same saved TV connection (`cytv recover` on the console). A No-root removal
that stopped before its first package request can offer removal without the
global package-status permission. The original local journal must still say
`uninstall / pending`, with no removal entries, inherited operation or unexpected
fields. The installer checks that journal again after the separate default-No
removal confirmation. The diagnostic export alone cannot establish eligibility.

Removal still stops Helper, restores LG Home, records each package request before
sending it, waits for its terminal reply and verifies package/file absence.
Only successful verified removal clears pending; start installation separately
afterward. A failed removal keeps its receipt. Already submitted/uncertain
requests, interrupted installs, nested prior operations and unknown journals
retain the existing guards; no request is blindly repeated. Do not edit the
journal or reset Developer Mode to qualify. This change is not in 1.6.0 and
physical EF950V recovery remains unverified.

<a id="recovery-explanations-and-direct-review-unreleased"></a>

### Recovery explanations and direct review (1.7.0)

After a failed **Remove**, an original No-root journal proving no package removal
was submitted offers **Review recovery options** for the same saved TV. This
opens inspection, with No by default; removal still needs a separate confirmation.
It never retries the failed removal automatically. The #256 pre-submission gate
above is shared by this explanation and actual removal, and is checked again
before changes. Other failures retain their existing recovery/report flow.

A definite refusal of `package-status` is shown as **TV refused the package status
check**, rather than an unspecified recovery error. Save the report; repeating
the rejected check or clearing records does not establish the package outcome.
The error code alone does not establish an ACL cause or firmware incompatibility.

The report's additive `recovery` section identifies `removal-not-submitted`,
`inherited-operation`, `interrupted-install`, `removal-started` or `unknown-journal`.
It includes only fixed next-action codes and Home/Helper removal receipt states.
`review-recovery` means inspect the original saved connection, not permission to
remove. `retain-evidence` means keep records for diagnosis, not a claim that no
future guarded recovery is possible. Missing original failures remain missing.
These 1.7.0 explanations were not in 1.6.0 and do not resolve #201's unknown
historical package outcomes or confirm recovery on #259's TV.

### No-root Helper service refusal (#152)

In 1.6.0, the #152 correction lets the existing Restore/removal flow request a
stop through Developer Mode SSH when `Helper disable` returns a definite `-1`
rejection. It writes the existing persistent stop latch and stop command, then
requires the controller and relay to be absent before proceeding. Saved Home
preference and watchdog state are retained; this does not automatically restart
Helper. Unknown connection outcomes, unsafe state and a live/orphaned relay
still stop recovery and retain the journal. No new command or confirmation is
needed. Use a 1.6.0 installer containing this correction; v1.5.4 does not have it.
Do not delete state files or repeat a failed removal. Actual EF950V recovery and
Home/Back/emergency behavior require owner-supervised confirmation on new bytes.

Console users: run `cytv recover` with the same profile. Save its report if
blocked; `cytv doctor --report` remains available for connection diagnostics. [CLI recovery details](CLI.md#interrupted-operations).
Status, restore and removal do not download Python; referenced recovery runtimes
are retained. For Root routing recovery, use the
[Root restore commands](../root-edition/ROLLOUT.md#controls-and-recovery).

## Root System rollback readiness (candidate)

<a id="root-system-rollback-readiness-candidate"></a>

**Available in cytv 0.6.0.** Use this explicit maintenance command only when a
Root System rollback completed every package installer, but the restored launcher
missed its readiness deadline. First check status using the same trusted TV
connection and retain the failed attempt's diagnostic report.

```sh
cytv recover-system-rollback --edition root
```

The command verifies the original supervisor pins, restored components, private
recovery receipts and saved profile digest. It refuses unknown installer outcomes,
incomplete package rollback, conflicting operations or changed evidence. It does
not reinstall packages or replace pinned code or keys. It opens the restored Root
launcher and gives it a fresh, bounded **120-second** window to send its genuine
authenticated readiness signal; no health receipt is manufactured.

A private durable audit records the attempt and its outcome. Retrying the normal
command resumes only the same unexpired attempt and never extends its deadline.
A failed or uncertain attempt keeps its evidence. After diagnosis, an explicit
new attempt is available only after the previous **120-second deadline has
expired**, with no accepted health receipt and no unknown installer outcome:

```sh
cytv recover-system-rollback --edition root --new-recovery-attempt
```

Before opening a fresh UUID and readiness window, this action archives the entire
previous audit under its UUID and hash. It does not delete the failure or start
serial retries automatically. A completed recovery stays idempotent; the flag
does not roll it over into another attempt. The normal confirmation defaults to
No; accepting it does not bypass the state checks. If recovery cannot finish,
stop and retain diagnostics and journals for review; do not delete state or
repeatedly retry. The original completion path preserves
an explicit Home-off choice. Successful readiness recovery does not prove
controls, audio, standby or cold boot; check actual behavior separately. [Connection flags and CLI details](CLI.md#candidate-root-system-rollback-readiness).

<a id="replace-the-root-system-updater-candidate"></a>

## Replace the Root System Updater

In 1.6.0, the replacement bundle targets System Updater 1.2.0;
1.5.4 used 1.1.2. The original 1.1.0 can reject a launcher's one-shot readiness
response while its worker holds the installation lock; this can cause an unnecessary rollback.
Signed Root offers retain a minimum supervisor version of 1.1.1 and are rejected
by the original 1.1.0; the new receiver/runtime path needs separate verification. Historical signed baselines remain valid for rollback.

This command supports replacing 1.1.0 or 1.1.1 after authenticating the retained
code, owner package, registration and finished recovery state. Other installed
versions, including1.1.2, are rejected. Existing1.1.2 stays pinned with its old
channels; no general migration is provided. Do not reinstall or delete state to
force replacement. Physical acceptance of a particular transition remains
separate from the command's source and fixture checks.

After any current update or rollback has completed, use the same trusted Root
connection and the complete matching installer from [GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases):

```sh
cytv replace-system-updater --edition root
```

The confirmation defaults to No. This replaces only the System Updater package;
it preserves Root, Root Updater, launcher storage, the full profile and the saved
Home choice. It verifies the finished old transaction and installed bytes,
captures a durable baseline, preserves the old service state in a private archive,
and provisions the verified replacement from that baseline. It refuses foreign
pending work and unknown installer outcomes. Any existing legacy Root Updater
transaction or backup also blocks replacement, even if marked complete; preserve
it for review rather than deleting it to force replacement. It does not patch
retained pinned code in place or replay an uncertain remove/install request.

Published v1.13.0 includes fresh System Updater 1.2.7; v1.12.1 included 1.2.6. Only installed 1.1.0/1.1.1 sources are admitted by the explicit replacement. Retained 1.1.2 and 1.2.x have no general replacement path. A completed earlier
replacement to 1.1.1 can start a new target operation only
after the installer authenticates its saved bundle, baseline, original archive,
terminal removal and current owner, and confirms that later recovery has finished.
The original completed journal is durably archived with its existing evidence;
no private pins or unfinished journals are cleared. Interrupted replacements
still require the same installer bundle and coordinator source.

An interrupted replacement retains its operation and archive. Continue only with
the same command and installer bundle, or save diagnostics and stop if its outcome
is uncertain. Do not remove journals or archives to force setup. A failed readiness
transaction must be recovered first; replacement does not bypass it. Verify the
new System Updater version and actual Home/controls after completion.

## Private Python and low /var space

Root Python preparation checks ABI, directory safety and free space separately.
The initial threshold is **320 MiB**; later staging can require more. Reusing an
existing runtime still requires verification. Freeing space cannot fix ABI or
ownership failures; do not lower thresholds or change ownership broadly.

On an already rooted TV, these SSH commands inspect space without deleting data:

```sh
df -Pk /var/lib
du -xsk "/var/lib/wam/Default/Session Storage"
```

Check the filesystem containing `/var/lib`. `/var/palm` can be a separate mount;
`du -x` avoids counting other mounted filesystems. Removing apps may free a
different partition.

For cache cleanup, use cytv's explicit Root maintenance action and read
[WAM cleanup](WAM-CLEANUP.md). It only requests native `cache` and `codecache`
cleanup; it does not clear Session Storage, reboot or resume installation.
**Session Storage contains app session state**: deleting it can lose sessions or
unsaved work. A safe manual procedure must prevent WAM writers and respawns;
closing visible apps alone is insufficient. Leave Local Storage, Service Worker,
databases, Python slots and recovery records alone. Recheck space after cleanup;
reclaimed space does not prove Root or Python installation succeeded.

## No-root source installations

For one-script installs, run commands from the repository folder and expose the
local webOS CLI:

```sh
export PATH="$PWD/build/tools/node_modules/.bin:$PATH"
```

Replace `lgtv` below with your device name. The script default is
`clean-your-tv-<IP-with-dashes>`, such as `clean-your-tv-192-168-1-50`, unless you
set `DEVICE`. Manual installs use `lgtv`.

To open Helper explicitly:

```sh
ares-launch -d lgtv com.local.nativehome
```

If a quick power cycle leaves tiles unresponsive, use triple Home and check arrows
on LG Home. Report the Helper version and whether it happens with Helper stopped.
Test standby and cold boot separately. [Compatibility and known limits](COMPATIBILITY.md).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="no-root-controls-and-recovery"></a>
