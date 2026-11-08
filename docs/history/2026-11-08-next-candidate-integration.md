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
