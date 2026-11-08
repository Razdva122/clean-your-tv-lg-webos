# Unfrozen next-candidate integration — 2026-11-08

Candidate #425 is collecting implementation PRs after v1.12.1. No new version,
full candidate build, signing approval or physical acceptance is selected here.
All observations below are host/source results, not installation reports. No TV
was contacted or changed by this coordination task.

## Retained first batch

#415/#421/#423/#424 and their issue limits remain in the committed plan.
[CI corrections and combined checks](2026-11-08-candidate-ci-corrections.md)
record the prior integrated checkpoint. Published versions remain unchanged.

## #426: Root inventory diagnostics

Reviewed head `fda84f05` passed selected CI [42453536991](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42453536991)
(all eight Linux/macOS shards, browser, optional Python and OS summaries).
Independent complete-source/privacy review found no blocker. The stale draft
validation hold was cleared under the maintainer's integration instruction.
Merge source: `25881c70`.

Combined with #423, icon-budget/priority-service tests and ten actual child-process
failure classifications pass (eight node:test entries), as do 34 diagnostic
context and 16 release-flow tests. Fixed category/code projection is retained;
raw replies, paths, error strings and app inventories are excluded. Required
catalog failure still blocks; optional inputs remain warnings. Root service,
embedded updater/coordinator and desktop/Android payloads require rebuilds at
freeze. Original #397 installation failure and reporter compatibility remain
unresolved; diagnostic integration is not recovery or a delivered fix.

## #427: retained Home route during startup

Head `5b92afce` passed selected CI [42454004721](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42454004721)
and independent complete-source safety review. Merge source: `f9a5e7e4`.
Combined source passes 17 continuation and 66 clean-removal cases, run in separate
`unittest discover` processes, plus 16 release-flow checks. A custom attempt to
load both selected modules in one process failed because their `sys.path` changes
selected the installer's `provision` instead of runtime `provision`; isolated
discovery corrected that invocation. No product guard was relaxed to hide it.

The original baseline/owned route is retained while fresh startup authority is
armed. The new private continuation record remains recovery/cleanup evidence,
not public diagnostics. Root runtime/infrastructure and embedding payloads need
versioned rebuilds. #422 stays open for exact-package physical Home/emergency,
ordinary power cycles, distinct standby/cold boot and update/rollback acceptance.

## #430: Root recovery refusal diagnostics

Reviewed head `58ab418` passed selected CI [42455080424](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42455080424)
and independent complete-source/privacy review. Merge source: `8e62885c`.
The integrated diagnostic/recovery/context/clean-reinstall selection passes all
74 cases with `PYTHONPATH=tests/cytv`; these tests import their sibling fixtures
by unqualified module name. Invoking the same selection without that test path
first produced a fixture import error, not a recovery behavior result. Sixteen
release-flow tests and diff checks also pass.

Root app/input diagnostic categories from #426 remain alongside the new recovery
stage projection. Eligibility predicates, remote call count/order and existing
permission/error handling remain unchanged. Desktop/console/Android installers
need rebuilding. Original #355 cause, device recovery and the requested genuinely
passive inspection path remain queued and unverified; the issue is not delivered
or resolved by adding future diagnostic evidence.

## #431: actionable removal/reinstallation

Head `1a6bb6fe` passed selected CI [42456340320](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42456340320)
and desktop host checks [42456340315](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42456340315),
plus independent complete-source recovery review. Merge source: `652e0547`.
Combined maintenance/no-root removal/Qt result/recovery-diagnostic/context tests
pass all 110 cases using `QT_QPA_PLATFORM=offscreen PYTHONPATH=tests/cytv`, with
16 release-flow checks. No existing reporter issue is claimed fixed by this
direct maintainer-request PR.

Retry retains the approved target, host pin and durable goal. Unknown process,
shortcut or cleanup evidence still blocks verified-clean completion. Emergency
stops remain. The local `cleanup_inputs_pending` journal field grants no device
mutation authority. Desktop/Android payloads need versioned rebuilds; affected
key-selection, Helper-before-pairing, full-removal/restart/reinstall and EIM
behavior need exact-artifact hardware acceptance. Maintenance/recovery references
and all thirteen guides describe the changes as unreleased.

## #419 / #428: passive IR contribution with safety corrections

The original ferrets6 head `82229cfa` is preserved in #428 ancestry, with credit
to ferrets6 and Mr-Hubiverse. Merge #428 source `5d34dddb` incorporates the
contribution and safety corrections together; GitHub subsequently marked #419
merged, and the collector includes both PRs. The unsafe original head was not
integrated separately ahead of its fixes.

Head `6a4bc912` passed selected CI [42455004348 attempt 2](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42455004348).
The first attempt's sole runtime failure was a dependency download reset during
`test_update_lab` setup. Only failed jobs were retried; existing successful jobs
were retained, with no product workaround. Independent complete-source safety
review found no blocker in the final source.

Combined source passes isolated IR exit/watchdog/Off-On/Stop/deferred-close
controller scenarios, 82 existing resume/watchdog cases, the C IR baseline and
all four Off-On/overflow scenarios, plus 16 release-flow checks. Fresh triple-Home
escape still exits 27; grabbed M-RCU behavior is unchanged. Unexpected persistent
IR read errors without normal poll device-loss flags remain optional defensive
hardening, not a demonstrated regression; do not claim every imaginable failure
is harmless. No permission grant, disableHome setting or automatic emergency
reset is introduced.

Helper/manifests/pins and embedding installers need versioned rebuilds and genuine
published-Home/new-Helper transition approval. Guides mark the approximately
700 ms delay, possible LG Home flash, held Home and unknown plain Developer Mode
access as unpublished. Original LJ550T routing, actual input access, physical
source duplication, key-up/unrelated buttons, power, sound and OTA/rollback still
need affected exact-artifact acceptance; no new TV result is claimed.

## #432: Root cleanup restoration boundaries

Head `ed22bd44` passed selected CI [42457011325](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42457011325)
and independent source/privacy review. Merge source: `e1afcd7c`.
Combined source passes 69 Root clean-removal and 44 diagnostic-context/recovery
projection tests, plus 16 release-flow checks. The producer and host allowlist
fixed cleanup_step values, preserve exact exceptions and retain original inverse,
receipts and failure-before-package-removal ordering. Updater/coordinator and
embedding installers require rebuilt payloads. Original #418 remains needs-info
under its existing saved-error request; do not rerun device recovery to fill a
new diagnostic category. Synthetic packaged export checks are the relevant gate.

## #433: SSH socket causes

Head `2f342b8` passed selected CI [42457129023](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42457129023)
and independent complete-source/privacy review. Merge source: `ef0b110a`.
Combined SSH/report/history, diagnostic context and recovery projection tests
pass all 51 cases; 16 release-flow checks pass. Socket categories are fixed,
sorted, deduplicated and revalidated. Existing authentication/trust/key-file/phase
handling is retained, with no new connection retry, endpoint or TV probe.
Desktop/console/Android installers need rebuilt embeddings. Original #420 stays
needs-info under its existing published-version Doctor/context request; neither
historical missing causes nor native Windows ARM64/TV acceptance are inferred.

## #429: conflict resolution before integration

The original reviewed head `d1a498f5` passed its selected CI. New diagnostic
additions made its tv_summary/document insertion conflict with #430. The merge
resolution retains both complete icon_inventory and root_setup_recovery blocks
and both guide sections; independent follow-up review confirmed all existing
Root inventory/node/capability/privacy fields remained. After #432/#433 entered,
the prepared branch merged the final base without another conflict. Combined
TV/CLI/diagnostic/socket/context/recovery tests pass 131 cases; clock/core/catalog
checks (all thirteen languages), formatting and diff checks pass. No clock or
privacy guard was weakened. The updated head still needs mandatory CI before
integration; this paragraph is preparation evidence, not a merge claim.

## Final #429 integration and handoff checkpoint

Final reviewed head `e8ae8f8c` passed [Tests 42458264627](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42458264627)
(all eight Linux/macOS runtime shards, browser, optional Python and both OS
summaries), [Windows/Intel Mac host runtime 42458264550](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42458264550),
website and integration policy. Merge source: `2e22c62b`. Existing input-equivalence
verification confirms this product merge matches the successful CI head; later
external Markdown/plan edits are metadata. The earlier 131 local combined cases,
clock/core/catalog checks, conflict-resolution review and formatting remain valid.

All thirteen implementation PRs are now incorporated; only draft #425 remains
open. Candidate versions, complete build/signing/acceptance and the mandatory new
Helper transition gate are still unselected/uncompleted. Physical cases are in
the [actual-change checklist](2026-11-08-next-candidate-physical-checklist.md),
and the next coordinator's work/issue limits are in the
[handoff record](2026-11-08-release-candidate-handoff.md). No publication or new
physical-device acceptance is claimed.
