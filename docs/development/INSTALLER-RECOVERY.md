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

After verified full-project removal, the installer reconciles older `install`
and `uninstall` receipts in other saved connections at the same host address,
including other editions and ports. It saves their original bytes as
`operation-superseded-<removal-id>-<receipt-hash>.json` and copies the completed
proof as `superseded-removal-<removal-id>.json` before clearing the active slot.
The install admission gate also applies this to completed removals saved by older
installers, so an already confirmed cleanup does not require another TV removal.
This runs under the existing TV lock. A source with a pending operation, an SSH
identity review, incomplete removal, corrupt target receipt, another action or
host, or a receipt written at/after completion does not qualify. Local file
modification times supply chronology for the legacy format: clock rollback or
external rewriting/restoration of proof files can invalidate that ordering.
This is a local reconciliation heuristic, not a new device transaction proof.

After a scoped terminal package removal, cleanup may leave a tree containing
only directories in that package's fixed No-root service slot. This extends the
existing empty Helper application-directory rule to the Helper, Home renewal and
updater service directories. It does not admit package metadata or other app
slots. Each service requires its own package's terminal receipt. The same bounded
inode/owner/directory-only walk runs at sweep, final inventory and resumed
completion; surviving files, links, processes and observed application/service
registrations keep removal pending. `empty_service_dirs_retained` records the
result alongside the existing `empty_helper_dirs_retained` flag. Package install
continues through the vendor endpoint and can repopulate retained directories.

For `process-idle-unverified`, an observed kernel change can settle opaque
individual processes once every remaining project target has its own terminal
removal. This applies to retained Helper and service trees; unrelated installed
apps do not participate in that target test. Final checks still require an
enumerated process list, no observed project/installer process, directory-only
residue, absent project apps and checked controls/registrations. A same-boot retry
does not establish this exception. The existing durable kernel-change field is
kept across interrupted verified-clean completion, including service-only residue.

An inherited install receipt, a closed cancellation observation, or historical
installer directories do not by themselves defeat this terminal cleanup rule.
Current package/configuration requests, original unsettled work and observed
writers still have their own gates. If process observation remains incomplete
after an accepted restart, cleanup blocks with recovery data rather than replacing
the boot baseline and repeatedly requesting another power cycle.

Standard diagnostics export `removal.restart_evidence`: strict booleans for the
boot-probe result and kernel change, process visibility/uncertainty, package and
configuration state, terminal eligibility and retained directory types. Fixed
`phase`, `decision` and `proof_kind` values identify the last branch.
`process_matches` lists fixed categories such as Helper, renewal service or
installer. The process scan checks individual arguments and process links for
project IDs and owned paths. Shell text that refers to project components can
still block removal before a delayed child starts. A single literal print can
proceed through the remaining checks. After an acknowledged startup disable,
the installer gives the specific Helper or renewal service up to 20 seconds
to exit before requesting any package removal. Other process matches keep
the ordinary eight-second window. The private operation receipt stores these under `cleanup_restart_evidence` for later report
exports; they are observations of the latest cleanup attempt, never admission
authority. No PID, process arguments, path, raw kernel ID or proof identity is
exported. `restart-required` also remains visible in the pending-stage projection.

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

## Root component state during full removal

Root, Root Updater and System Updater keep disposable component state in
dedicated private directories. After fencing component writers and restoring
controls, full removal retires their contents by directory ownership. New
receipts and caches inside these directories need no filename registration.
The coordinator keeps the original locks and fence records through final
readback and preserves routing and permission inverses before retiring state.
Archives require component provenance and the recorded directory identity.

Keep shared paths and mounted data outside these directories. The private-tree
sweep rejects mounts, hard links and directories with unexpected ownership or
group or other write access. A regular file inside a trusted directory can be
unlinked regardless of its owner or access bits. Symbolic links are unlinked
without following them. Shared registrations, packages and startup hooks retain
their own verification and cleanup rules. Any future state that changes
behavior outside the private directories needs an explicit restoration step
before the sweep.

Full removal retires temporary uploads tied to the current operation. Other
installer artifacts in shared temporary storage may remain after removal.
The coordinator and finalizer check for processes using installer staging
paths before confirming removal.
