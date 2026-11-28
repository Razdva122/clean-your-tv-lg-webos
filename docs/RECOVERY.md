# Recover TV controls or an interrupted installation

[Finish an interrupted installation](#finish-an-interrupted-installation) ·
[Continue removal after restoring Home](#continue-removal-after-restoring-home) ·
[Finish after verified removal](#finish-after-verified-removal)

> **Experimental compositor routing (#364):** experimental compositor recovery stops routing
> before removing only its own filter. Safety/power stops require explicit
> re-enable. If Home identity changed, the owned filter can be released after
> retirement, but full stock proof remains unverified and recovery evidence is
> retained. Do not delete journals or remove another launcher's state. See
> [capability-based admission](development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).

> **Release 1.9.0:** see [versions, tested scope and recovery limits](RELEASE-1.9.0.md). C1 Beta is fresh-install only, selected automatically in the common installer; normal OTA is unavailable and physical C1 acceptance is pending. Historical results below retain their original artifact scope.

## Return to LG Home

If the installer reports that another Home integration covers LG Home, use
that integration's supported procedure to return to LG Home. Then open
**Diagnostics → Check connection and create a diagnostic report**. The
installer's **Return to LG Home** action is for Clean Your TV recovery.

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

Keep the original profile, keys and pending-operation records. A pending
uninstall describes earlier work. It does not explain the key mismatch or
establish what remains on the TV.

### Connect a No-root TV after a factory reset

Use this only for your own TV on your trusted home network after a factory
reset you performed. Enable **Dev Mode Status** and **Key Server** on the TV.
When the desktop installer reports the changed key, select **Reconnect after
factory reset**, confirm the reset, enter the Developer Mode code, and confirm
the new SSH key as you would for a first connection. Then continue No-root setup.
In the console, use `cytv install --edition no-root --host TV_ADDRESS --reconnect-after-reset`.
Include the saved SSH port with `--port` if it differs from 9922.

CYTV saves the new connection after successful SSH sign-in and keeps the
previous profile, SSH pin and uninstall receipt. The new setup uses its own
records. For other SSH identity changes, keep the existing connection and use
an independently verified source for the new key.

### Review a changed Root SSH identity

For a saved Root connection with a pending uninstall, use the console command
`trust-root-ssh` from an installer build that lists it in `cytv --help`.

1. Identify the intended TV independently and obtain the full OpenSSH-style
   `SHA256:…` fingerprint of the active SSH server host key through a trusted
   local/on-device method or an already trusted access path. For OpenSSH, you
   can run `ssh-keygen -E sha256 -lf /path/to/active-host-key.pub` against the
   server's public host-key file from that trusted access path. Use the host key
   for the algorithm used by the saved connection if the server has several.
   The blocked SSH connection, a network scan, the address and reset history
   cannot establish this fingerprint. Stop if you have no independent source.
2. Run `cytv trust-root-ssh --host TV_ADDRESS` on the computer with the original
   saved profile. Use the saved address and include `--port` if the profile
   uses a port other than 22. Include `--data-dir` if you originally used a
   custom profile directory.
3. Enter the independently verified full fingerprint. Enter an empty line or
   press Ctrl+C to cancel. CYTV checks the key in a fresh SSH handshake and
   records a match without signing in or executing commands. If the key
   changes again, verify its new fingerprint independently and repeat this
   step with the same saved profile.

A successful check records the new SSH identity for this profile and its
original recovery evidence. The original SSH pin and uninstall receipt are
retained. The earlier uninstall and ordinary connections through this profile
remain blocked. Verifying the TV's current SSH host key cannot establish that
the installation named by the old receipt survived the reset. Keep the profile
and receipts for maintainer-assisted recovery. Share the independently verified
method and reset history privately if requested. Keep raw profiles and keys private.

For a Root uninstall stopped at `coordinator-submitted`, keep the original
receipt pending. The installer saved this stage before calling the TV's removal
driver. A command failure at that point leaves the outcome unknown. Even a
successful full removal through another saved connection at the same address
cannot verify the earlier operation.

For maintainer-assisted review, use an independently trusted access path with
the owner's permission. Compare the original receipt's `product_operation` with
the on-device coordinator request for that operation and its removal action.
A matching record can identify the operation for investigation. Confirming
completion also requires its terminal removal result and a current check of
the affected packages, services and startup registrations. If the record is
missing, inconsistent or inaccessible, keep the outcome unknown and retain
the receipt. No repeat uninstall or reset is needed to report that result.

## Interrupted setup or removal

Keep the original TV connection and recovery data. On desktop, start from the
current result screen. To return later, open **Maintenance action**, select the
action you need, and choose **Run selected maintenance action**. Select the same
saved TV when asked. On Android, open **Maintenance** to find
**Review recovery options**, **Installation status**, **Restore LG Home** and
**Uninstall Clean Your TV**.

<a id="interrupted-setup-or-removal-in-110"></a>
<a id="interrupted-no-root-installation-in-the-unpublished-140-candidate"></a>
<a id="root-setup-is-unfinished-and-its-deployment-record-is-missing"></a>

### Finish an interrupted installation

From the unfinished setup result, choose **Review recovery options**, then
**Continue** at **Check recovery options?**. If setup already asked to review an
earlier operation for a saved connection, **Review recovery options** starts
that check on its original connection. Review the result before confirming a
change.

- **No-root:** If the package result could not be verified, choose
  **Check TV status** when offered. Once the wizard verifies what can continue,
  choose **Review recovery options** and confirm **Finish No-root configuration?**
  or **Continue the original No-root operation?** if offered. This finishes the
  verified work using the existing setup. If you cancelled Home activation,
  open **Home Helper** on the TV, choose **Start Helper** and confirm when ready.
- **Root:** If Root and Root Updater are verified, select **Continue setup and
  turn on Home control**, then **Continue** at **Finish Root setup?**. This
  continues with the installed packages. On eligible TVs you can instead select
  **Finish setup with LG Home and Home control off**, then choose **Continue**
  at **Finish Root setup with Home control off?**. If **Check TV status** says
  **Ready to reinstall Root**, choose **Back to start**, then **Set up my TV**
  with the same saved connection and confirm **Reinstall Root?**. C1 Beta uses
  its own [Root Beta recovery](#repair-an-interrupted-root-beta-setup).
- **Removal offered:** If the installer offers **Remove remaining Clean Your TV
  packages?**, continue only if you want to start over. For Root with a missing
  deployment record, removal covers both editions, including No-root Home and
  Helper. Back up preferences before confirming. Start a new setup after
  verified removal.
- **Still blocked:** Keep the saved connection and choose
  **Save diagnostic report…** if available. Follow the current screen if it
  offers a new check.

<a id="next-candidate-original-operation-recovery-and-full-removal"></a>
<a id="original-operation-recovery-and-full-removal-published-v1110"></a>

### Continue removal after restoring Home

To remove the apps, select **Uninstall Clean Your TV** under
**Maintenance action** and confirm on the saved TV. This removes project apps
and files that are present, including after a partial setup.

- If the removal result offers **Return to LG Home**, choose it and confirm.
  The restore result can show **LG Home is restored.** while apps remain.
  Choose **Continue removal** to resume that already approved removal.
  On some older No-root TVs the installer may observe Live TV or an HDMI input
  as the stock screen. Follow the offered action.
- If you chose **Return to LG Home** directly from **Maintenance action**, the
  apps stay installed. Open that menu and choose **Uninstall Clean Your TV**
  only if you want to remove them. On Android after **Restore LG Home**, choose
  **Back to start**, then open **Maintenance** to uninstall the apps separately.
- If the current result asks you to fully restart the TV, disconnect and
  reconnect power and turn it on. When the installer sees it again, choose
  **Continue removal** if offered, or **Try again** to check manually.
  **Cancel** stops waiting. Standby and Quick Start do not count as a full
  restart. If the installer cannot verify the restart, save the diagnostic
  report and keep the recovery data.
- If the TV is busy or disconnected, resolve the condition and choose
  **Try again** when offered. For unverified controls, package results or final
  cleanup, choose **Review recovery options**. Confirm any offered continuation
  separately. If No-root cleanup specifically requires Root, choose
  **Connect using Root** when offered for the same TV. If you already have Root
  access but no saved connection, use it through **Uninstall Clean Your TV**
  in **Maintenance action**. Without existing Root access, keep the recovery
  data for the unfinished cleanup.

### Finish after verified removal

When you see **Clean Your TV removal is verified.**, choose **Close** to finish
or **Set up my TV** to start a new setup on the same TV with the same edition and
connection. A confirmed Root reinstallation offers **Continue Root installation**
after its removal phase. On Android, choose **Back to start** after verified
removal, then **Set up TV** and select the TV again if you want to set it up.

If recovery remains blocked, choose **Save diagnostic report…** from the desktop
result or **Save report** on Android, if offered. To ask for help, use the
[desktop report controls](DESKTOP_INSTALL.md#review-interrupted-setup-or-removal)
or [share the result](FEEDBACK.md).

<a id="unreleased-local-recovery-storage-messages"></a>

### Local recovery storage messages

If a fresh setup cannot write its local files, check write access to the
installer's application data folder or free disk space, then choose
**Try again** if offered. If the installer refuses to read existing recovery
files, keep those files and choose **Save diagnostic report…**. A local
storage error does not establish what happened on the TV.

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

If No-root setup says the TV storage check failed before any package request,
use **Retry storage check** when offered to repeat the read-only check on the
same TV. Confirm installation separately after it passes. Keep the saved TV
connection and save the diagnostic report if the check keeps failing. If the
installer finds an unfinished operation or a reservation conflict, follow its
recovery instructions before starting setup again.

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

If removal asks for a full restart because it could not read the Helper Stop
records, restart the TV and continue the existing removal. The installer checks
the new boot and that Helper has stopped before it submits package requests.

Removal stops Helper, restores LG Home, records each package request before
sending it, waits for its terminal reply and verifies package/file absence.
Only successful verified removal clears pending; start installation separately
afterward. A failed removal keeps its receipt. Already submitted/uncertain
requests, interrupted installs, nested prior operations and unknown journals
retain the existing guards; no request is blindly repeated. Do not edit the
journal or reset Developer Mode to qualify. This change is not in 1.6.0 and
physical EF950V recovery remains unverified.

### Remove No-root after losing the local recovery capsule

If the original No-root installation was interrupted, use **Review recovery
options** with the original saved TV connection. Before offering removal, the
installer checks whether the original local receipt matches the removal plan on
the TV. If the local recovery capsule is missing, removal can still proceed
when that match is verified. Confirm removal separately. The installer keeps
the operation pending if the match cannot be verified or another operation
owns the reservation. Keep the original receipt and save the diagnostic
report if removal stays blocked.

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

## Standalone Root Updater rollback readiness

Use the same trusted Root SSH connection if Root Updater reports
`recovery-required` with `restored profile readiness unconfirmed` after a
successful automatic rollback. In the desktop installer, choose **Maintenance →
Recover Root Updater rollback**, or run:

```sh
cytv recover-root-rollback --edition root
```

The command verifies both installer results, the restored Root package, the
saved profile and LG Home routing. It archives the timed-out journal and
restarts the restored launcher with a fresh 120-second readiness window.
It uses the launcher's authenticated signal and the original Updater's
completion path. Packages and the retained Updater stay installed.

After recovery succeeds, return to Root Updater to check for updates.
If Home was left off, use **Change Home** to enable it when ready.
After a readiness timeout, rerun the command to archive the expired attempt
and open a fresh 120-second window in the same run. A retry during an open
window keeps its original deadline. If the launcher already sent valid
readiness before the deadline, the command finishes that attempt.

## Root System rollback readiness (candidate)

<a id="root-system-rollback-readiness-candidate"></a>

**Available in cytv 0.6.0.** Use this explicit maintenance command only when a
Root System rollback completed every package installer, but the restored launcher
missed its readiness deadline. First check status using the same trusted TV
connection and retain the failed attempt's diagnostic report. In the desktop
installer, choose **Maintenance → Recover Root System Updater rollback**, or run:

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
expired**, with no accepted health receipt and no unknown installer outcome.
In the desktop action, select **Start a new audited attempt after the previous
deadline**, or run:

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

For a Root installation with System Updater 1.2.10, use the complete installer
containing System Updater 1.2.11 to prepare the self-updating supervisor.
For the earlier transition from 1.2.9 to 1.2.10, use the matching v1.22.0
installer. Its replacement also supports source versions 1.1.0 and 1.1.1.
Use the matching installer when resuming an interrupted replacement.

After any current update or rollback has completed, choose **Return to LG Home**
in the installer if Clean Your TV is active as Home. From the command line, use
`cytv restore --edition root` for that step. Then use the same trusted Root
connection and the complete matching installer from
[GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases):

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

Replacement admits only the documented source versions for the matching installer. A completed earlier
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

<a id="repair-an-interrupted-root-0220-recovery-service"></a>

## Repair an interrupted Root recovery service

Use a console installer that includes the following command with the same saved
Root connection and data directory as the original setup.

```sh
cytv repair-root-recovery --edition root
```

This is for a retained compositor Root 0.22.0 installation that timed out during
the recovery-service status check and recorded a clean service exit. The command
requires the original local install receipt, the matching installed package and
the original on-TV provisioning records. It keeps the installed package and
verifies the repaired service before offering to finish setup and enable Home
control in a separate confirmation. If verification fails, keep the original
recovery data and save the diagnostic report.

For a retained compositor Root 0.23.0 install recorded as a native product
operation, the same command verifies the original operation and resumes recovery
provisioning in place. It completes the original product reservation only after
verifying the installed files, the recovery service and stock Home. This path
finishes with LG Home in control. The saved connection and device recovery
records remain available.

## Repair an interrupted Root Beta setup

If Root Beta stopped while preparing its recovery service, use the saved Root
connection with the complete installer and run:

```sh
cytv recover --edition root --root-variant node012-beta
```

Confirm **Repair the existing Root Beta recovery service?** if the installer
offers it. This checks the service and keeps the existing app installed with
LG Home selected. Home activation is a separate action. If the installer cannot
verify recovery or offers a different action, save its diagnostic report and
keep the existing recovery records.

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


## No-root setup activation and a lost computer profile

New No-root setup requests Home On after package/configuration verification.
It binds the current Stop generation into the original operation. A new Stop
before or during activation cancels that activation; the installer keeps the
Stop and reports package verification separately. Open Helper and explicitly
start it when ready. Setup does not infer physical Home acceptance from a launch
acknowledgement. You can turn Home off afterward in Home settings.

Use the complete original saved connection and recovery data when available.
A TV reservation is not stale merely because its computer profile is missing.
If that profile is lost, establish a trusted connection to the same TV and
explicitly choose **Uninstall Clean Your TV**. This starts a new removal goal;
it does not adopt or replay the old install. Resident installer evidence requires
a verified restart after the new baseline before the private sweep. Only final
control/startup, package/registration/file absence and process checks can complete
removal. Start setup separately afterward; never remove an owner file or edit a
journal to qualify.

On Developer Mode jails with execute-only `/tmp`, removal also needs the separate,
not-yet-published [boot-proof correction #498](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/498).
Its host checks are not physical removal acceptance. If removal stops, save the
standard diagnostic report and keep recovery data rather than deleting reservations.
