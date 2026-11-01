# Installer recovery journey (unreleased)

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
receipts. Before offering removal it requires a positive bounded ten-second
`appInstallService/status` response with an empty apps list and rejects conflicting
or unsupported removal records. The existing uninstall guard repeats that check
at mutation. This remains the existing explicit-removal guard, not an alternative
transaction-terminal authority. Matching files, app absence, diagnostic IDs and
advisory plans never reconcile an uncertain install. See the
[No-root authority limits](NO-ROOT-PACKAGE-AUTHORITY.md).

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
