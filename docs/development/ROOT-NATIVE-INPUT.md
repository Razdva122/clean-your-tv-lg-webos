# Root native startup input

Published v1.7.0 includes two native startup-source choices. See the [current controls](../CONTROLS.md#back-app-exits-and-startup) and [artifact-bound scope](../RELEASE-1.7.0.md). The three-source policy below is historical development context; its HDMI option was not shipped. Track the remaining report in [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171).
Historical #204 acceptance remains limited to its original bytes and scenarios.

<a id="behavior"></a>

## Historical three-source policy

After healthy explicit **Change Home** activation, Root registers its existing
app as an owned native External Input Manager (EIM) input. Firmware can select
that remembered MVPD input before its visible application screen. Existing
`supportGIP`, icon, authenticated runtime destination and native APIs are reused;
no firmware patch or new LS2 endpoint/grant is introduced.

Root Settings adds three startup-source switches: **LG Channels / Live TV** on by
default, **YouTube** off, **HDMI** off. They choose which prior sources should
prepare Clean as the first app on the next power-on. Clean itself remains the
selected Home. Sources outside the selected policy keep normal native behavior.
When Change Home is off, all three switches remain visible and muted, genuinely
disabled with an explanation, and skipped by remote focus. Their saved values
remain available after explicit re-enable. Unconfirmed/busy/failed status also
prevents stale source writes without disabling otherwise healthy Home controls.

`startup-policy.json` is root-owned mode0600: schema version1 and exact boolean
`sources` keys `tv`, `youtube`, `hdmi`. It is separate from the legacy launcher and
original installed System supervisor profile schema. Normal in-place operations
retain this per-TV preference file; portable launcher-profile export does not
include it. Corrupt/indirect records are retained and rejected.

A guardian-owned event observer consumes foreground and native remembered-input
settings. It uses one coalescing worker, not a timer or reconnect loop. Each
operation rereads current foreground/input and requires unchanged active intent,
session and binding, fresh input and independent guardian, owned native receipt
and registration, and `general.homeAutoLaunch=on`. Source/native pair mismatch
or observed supersession cancels selection. LG Channels retains exact metadata
checks; unknown/invisible platform transitions cannot authorize selection.

Proactive selection also requires the volatile health-directory `.startup` record
published only after both native subscriptions acknowledge. It binds transaction,
startup session, PID and process-start ticks to the actual guardian. A missing,
closed or replaced observer cannot grant selection; post-ready reconciliation
withdraws our existing preference instead. Close removes eligibility before
cleanup and may wait up to two seconds for the existing operation lock, then
performs one fresh withdrawal. It does not replay an uncertain native RPC.

Native preference is prepared while an eligible app is selected. A later
protected app withdraws only our exact Root selection to its displaced input;
a different native input is preserved. HDMI and YouTube are opt-in. A global
native Home-startup Off can withdraw our selection even under a blank/platform
cover frame. The existing operation lock and 1.5-second optional RPC budget apply.

The candidate has **no late boot/wake application launch fallback**. Boot recovery
only restores/rearms control. Neither observer nor power-edge handling calls
applicationManager `launch`. Unsupported/unknown native selection leaves ordinary
manual Home routing; it does not schedule a later redirect. First-screen behavior
still requires exact-package physical acceptance on each supported firmware.

## Off, emergency and recovery

Turning Change Home off, triple-Home, input fault, failed startup or failsafe
restores Home routes first, then restores a displaced remembered input only while
it remains our Root selection and removes only the receipt-owned entry. Cleanup
never launches another foreground app. A positively classified normal shutdown
retains confirmed Home intent/native ownership for the next boot; it never grants
authority from an unclassified input error.

`native-input.json` retains the fixed Root identity, displaced native pair and
`adding`, `active`, `selecting`, `removing` or `disabled` phase. `selecting` requires
fixed pending direction `select` or `restore`; no other phase accepts that field.
The inverse is durable before retargeting. A lost response leaves that pending
receipt; matching target readback reconciles it without resubmission. Current
policy/withdrawal is then applied, so disabled sources and disconnect cannot
strand a newly confirmed Root selection. Unknown readback remains pending;
explicit recovery/Off retains the existing owned inverse. Fresh source events do
not authorize blind replay of uncertain effects.

System update, rollback and uninstall use the same route-first cleanup before
replacing runtime code. Pending direction is removed before existing cleanup
phases, preserving the older receipt form for rollback. Do not clear ownership,
intent, failsafe or transaction records to force a passing result.

## Evidence and remaining acceptance

On maintainer-owned OLED55C3RLA, firmware 43.21.71 / webOS SDK 11.2.0,
macOS ARM64 host, remote model unknown, an authorized temporary EIM registration
of Root 0.6.2 from full build `41118810865:1` (signed QA `41120901055:1`)
produced one owner-observed cold boot with Clean first and no channel screen.
Native metadata placed Cover App submission at 14.72 seconds, Clean foreground
at 29.11 seconds and boot-done at 37.36 seconds; metadata alone is not visual proof.
The owner observation supplies that result. The trial entry was removed afterward.

A separate bounded native API roundtrip on the same unchanged candidate passed:
add a previously absent owned entry, remember Clean, restore the exact previous
DTV input and remove the trial entry. Foreground and Home intent were unchanged;
the original remembered input and unrelated entries were verified afterward.
This validates the inverse API, not the new implementation's package acceptance.

[Signed C3 QA](../history/2026-10-31-release-1.5.3-signed-root-qa.md) records first-screen, standby, cold-boot, controls, normal Off and triple-Home passes on the exact tested packages. It also records Home preference loss during update/rollback (#202), stale Settings (#206), untested paths and the maintainer's explicit release decision. Close/reopen Settings if stale, then explicitly enable Change Home and wait for Clean status. These results do not establish universal first-screen compatibility or resolve [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171). Uninstall and unrelated external-input combinations remain untested.
