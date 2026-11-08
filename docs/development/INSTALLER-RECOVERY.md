<a id="installer-recovery-journey-unreleased"></a>

# Installer recovery journey

`cytv recover` is shared by console, desktop and Android. A pending `install`
delegates to this journey and returns before new installation. The host TV lock
and operation-context snapshot remain in force. `--yes` never approves recovery;
noninteractive execution stops. The inspection and each change have separate
interactive confirmations with No by default. Android carries the confirmation
default as a semantic field and focuses Cancel; desktop uses the existing prompt
default. Existing saved target/edition/port/identity matching remains canonical.

Inspection calls existing `Installer.status()`. Root status may upload/execute
verified support code, so this is not advertised as passive. Only existing
`can_resume_root_setup is True` permits the resume offer. Resume rechecks status,
Root/updater integrity and activation guards itself. An orphan active Root
operation or unknown/incomplete deployment stage blocks even without a host
receipt. Existing current/complete Root removal proof can reconcile its receipt;
no new proof source or orphan adoption is introduced.

No-root supports only existing pending install and pending/removing uninstall
receipts. Except for the pre-submission case below, offering removal requires a positive bounded ten-second
`appInstallService/status` response with an empty apps list and rejects conflicting
or unsupported removal records. The existing uninstall guard repeats that check
at mutation. This remains the existing explicit-removal guard, not an alternative
transaction-terminal authority. Matching files, app absence, diagnostic IDs and
advisory plans never reconcile an uncertain install. See the
[No-root authority limits](NO-ROOT-PACKAGE-AUTHORITY.md).

Published #152 correction: both the recovery offer and `uninstall()` use the
same `require_removal_idle` gate. The global monitor is unnecessary only for a
No-root journal with `action=uninstall`, `stage=pending`, no removal entries and
only `action`, `stage`, `diagnostic_id`, `eim_registered`, `removals` keys. This
is an unstarted package removal, not a completed transaction: published code
writes `removing` before any removal submission, then persists `submitted`
before each request. A retained `previous` install, unexpected fields, malformed
removals or any other stage cannot use the exception. The original journal is
re-read after confirmation. `status()` still does not clear it. The existing
terminal wait, stop/restore and absence guards remain authoritative for the new
removal requests; the original diagnostic export does not expose enough fields
to authorize this exception. The correction does not establish why retail
firmware refuses the global monitor, grant permissions or repair #201's lost
terminal outcomes.

Removal restores LG Home and follows existing verified package removal; it may
reset Home preferences. It stops before fresh setup. Unknown/denied/busy state,
timeout, failed proof or mutation error retains evidence and exports the current
attempt report. No unconditional repeat-Remove, reboot/reset, receipt deletion,
new endpoint, new dependency, permission or TV-state file is added. This feature
does not implement cancellation/adoption of unknown Root workers or resolve
#201/#216. Existing individually pinned handoffs remain separate.

`recovery-plan` is a presentation-only event with fixed `review`, `ready`,
`blocked`, `complete` states and localized summary/next-step strings. It is not
persisted or accepted as a backend argument. Frontends clear it between runs,
never use it to authorize mutations, suppress installation-success guidance after
recovery-only execution and prioritize failure-report export. Current recovery
status is included through the existing allowlisted diagnostic projection; raw
plans/device records/addresses are not added to reports. Legacy primary failures
remain unrecorded when the first-stage diagnostic history has no observation.

Rebuild embedding desktop/Android payloads through the normal candidate process.
No component/release version, build selection or physical acceptance is selected
by this focused change. Public downloads still point to the published release.


For a retained Root activation, current installer diagnostics distinguish the
first unverified receipt/routing/files/product/Updater/rollback/binding boundary
and checks not reached or still pending. See [diagnostic fields and limits](INSTALLER-DIAGNOSTICS.md#retained-root-activation-checks-next-candidate-355).
These observations preserve the existing recovery admission; no extra TV checks
or changes are performed to fill the report, and legacy discarded causes remain
unknown.
