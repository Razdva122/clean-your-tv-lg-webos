# Unit-scoped CI evidence

## User-authorized scope

Inherit actual successful results for unchanged test blocks instead of using one
whole-source fingerprint for every block. Continue the active release task: finish
original full run42366833792, consolidate failures, correct them in one batch,
build one replacement candidate, then pin and prepare final signed TV QA packages
only after success. No stable publication or new TV operation is requested.

## Design

Keep the existing runtime/browser/ARM units, shards, workflows and guarded
release/build equivalence. Add a distinct desktop installer-host unit for the
existing native-platform tests/cytv suites; it cannot attest the broader runtime
installer+Homebrew unit.
Project the authenticated Git snapshot per test unit. The default for product,
shared, unknown, workflow, dependency and CI-framework paths is all units. Narrow
only audited executable test families; preserve installer/Android/browser and
optional-Python fixture cross-edges. Shared fixtures, package initializers and
nonregular modes remain global. Setup still binds the complete Git tree.

Use schema/namespace v2. Artifact discovery names bind kind/OS/shard/environment,
not source, so different-source receipts can supply matching individual units.
Receipt keys bind each projected source, policy version and existing runtime,
runner/dependency/browser/day identity. Recompute projections from authenticated
producer trees and compare both claimed and consumer keys. Preserve same-repo,
first-attempt, latest-result suppression, digest/size, tested-merge provenance,
strict parsing, bounded lookup, fork/rerun, fail-fresh and nontransitive rules.

This conservative first rollout does not claim a whole-product dependency graph:
product/shared changes can still rerun broad coverage. Test-family dependencies
must be audited whenever new cross-family fixture imports are introduced. Old v1
receipts and historical full-run jobs cannot be promoted retroactively. New-policy
full candidates bootstrap fresh; compatible later candidates consume their
actual successful units. The user explicitly requested one merged correction
batch and one full validation, without separate per-change PR CI waits.

## Windows correction

The original Windows failure belongs to a local test adapter using cmd.exe for
POSIX source. Invoke Git's actual POSIX shell explicitly on Windows and /bin/sh
on POSIX; normalize the fixture Python executable to forward slashes. Preserve
binary stdin, large command source, error/status and trailing-newline assertions.
Keep the regression in the existing desktop-runtime check for future PRs;
this correction batch gets its real Windows proof in the one full replacement
run, as explicitly requested by the maintainer.

## Full-candidate producers and stale-result suppression

Existing PR producers retain their latest-overall-successful rule. In addition,
first-attempt full_candidate dispatches from origin release/next may record fresh
validation and installer-host units. Verify the actual cytv.yml workflow/run,
repository/ref/source, full dispatch input at record time, completed full marker
and successful scope/job at consumption. A completed overall failed full run may
supply a successful independent job; cancelled/unknown/rerun/fork sources cannot.
The latest prior dispatch's corresponding job must be completed and successful;
a later failed/running/missing job suppresses older success. Older direct proofs
can remain usable after a newer green reused job; no transitive receipt is made.

Bind desktop OS/image, exact installed dependencies, Git/shell/runtime/compiler
identity as applicable. The Actions API reader must preserve bounded size/time
and fail-fresh behavior on Windows as well as POSIX. Package builds, installed
package/runtime checks and signing are never skipped by installer-host test reuse.

## Verification and risks

Test real Git mutations, unrelated block reuse, owning/cross-fixture invalidation,
unknown/shared/mode/guard invalidation, additions/deletions, all shards and stable
partial receipt discovery. Retain adversarial receipt/run/tree tests. Run the
Windows adapter in the replacement full candidate, following the maintainer’s
explicit request to omit separate per-change CI runs.
No change to package reuse, signing gates, required job names or physical acceptance.
