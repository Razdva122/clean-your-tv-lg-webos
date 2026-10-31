# Recover TV controls or an interrupted installation

## Return to LG Home

Press Home **three times within two seconds**, releasing between presses. This
stops Home interception and opens LG Home; it preserves preferences. Helper
through 0.6.13 uses holding Home for about two seconds instead.

The emergency stop persists across startup. To resume No-root, open **Home Helper**,
choose **Start Helper** and confirm. To resume Root, turn **Change Home** on in
Home settings. Opening Home alone does not restart a stopped Helper.
**Open LG Home** only visits LG Home once; it keeps the saved Home choice.

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

## Interrupted setup or removal

<a id="interrupted-setup-or-removal-in-110"></a>
<a id="interrupted-no-root-installation-in-the-unpublished-140-candidate"></a>

1. In cytv, select the **same saved TV connection** and choose **Check TV status**.
2. For No-root, use **Recover and reinstall** if offered. Review the separate
   removal confirmation; the default is No. Removal can reset Home preferences.
3. For Root, use **Finish Root setup** only when offered for a verified installation.
4. If recovery fails or the result is uncertain, choose **Save diagnostic report…**
   and stop. Retain that attempt's report and recovery files.

Recovery checks installer state and removal results before offering installation.
An unknown package outcome is not automatically retried. Returning to LG Home
alone does not finish removal. The removal confirmation cannot be bypassed with
`--yes` or approved by noninteractive setup.

### Unreleased: No-root Helper service refusal (#152)

The #152 source correction lets the existing Restore/removal flow request a
stop through Developer Mode SSH when `Helper disable` returns a definite `-1`
rejection. It writes the existing persistent stop latch and stop command, then
requires the controller and relay to be absent before proceeding. Saved Home
preference and watchdog state are retained; this does not automatically restart
Helper. Unknown connection outcomes, unsafe state and a live/orphaned relay
still stop recovery and retain the journal. No new command or confirmation is
needed. Use only an installer containing this correction; v1.5.4 does not have it.
Do not delete state files or repeat a failed removal. Actual EF950V recovery and
Home/Back/emergency behavior require owner-supervised confirmation on new bytes.

Console users: run `cytv status` with the same profile, then
`cytv doctor --report`. [CLI recovery details](CLI.md#interrupted-operations).
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

## Replace the Root System Updater (candidate)

**Release 1.5.0.** The replacement bundle contains
System Updater 1.1.2. The original 1.1.0 can reject a launcher's one-shot readiness
response while its worker holds the installation lock; this can cause an unnecessary rollback.
Signed Root offers retain a minimum supervisor version of 1.1.1 and are rejected
by the original 1.1.0; the new receiver/runtime path needs separate verification. Historical signed baselines remain valid for rollback.

This command supports replacing 1.1.0 or 1.1.1 after authenticating the retained
code, owner package, registration and finished recovery state. Other installed
versions are rejected. Physical acceptance of a particular transition remains
separate from the command's source and fixture checks.

After any current update or rollback has completed, use the same trusted Root
connection and a complete 1.5.0 installer:

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

A completed earlier replacement to 1.1.1 can start a new 1.1.2 operation only
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
