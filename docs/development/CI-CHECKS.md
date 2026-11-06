# Focused PR checks

`Tests` selects the union of affected components with `scripts/ci-scope.py`.
Unknown paths, shared build/dependency files and CI implementation changes still
select every component. A failure in any selected job fails the required
Linux/macOS summaries; an unexpected skip cannot grant a selected gate.

## Parallel test shards

The runtime matrix runs **four shards per selected OS**, with
`fail-fast: false` so a failing shard does not cancel the other evidence.
`scripts/test.sh --shard INDEX/COUNT [components...]` partitions the three large
unittest discoveries (`root-edition/tests`, `tests/setup`, `tests/cytv`) by test
case in deterministic discovery order. Every discovered occurrence belongs to
exactly one shard; new cases are included automatically. Existing repeated
discovery of imported test classes is preserved, not silently deduplicated. Each shard keeps discovery
order and unittest's class/module fixture handling. Shared fixtures run once per
participating shard, so there is some extra setup cost. All other commands,
including JS, native controls/watchdog, smaller Python suites and Linux ownership,
run on shard 1. Browser and ARM Python validation retain their separate jobs.

Without `--shard`, local profiles and the no-argument full suite are unchanged.
Reproduce one CI partition from its own checkout with, for example:

```sh
scripts/test.sh --shard 2/4 setup
scripts/test.sh --shard 2/4 tv installer android preview
python3 scripts/test-shard.py --shard 2/4 -s root-edition/tests --list
```

Use separate checkouts for concurrent local shards: packaging tests write shared
build paths. The shard option is not exported to subprocesses, so tests that
invoke a test profile themselves still exercise that entire profile. Discovery
errors fail every shard before selection; zero discovered tests fail, while an
empty partition of a nonempty suite is valid. Invalid shard arguments fail before
any test command starts.

Authenticated test-unit receipts include the shard index and count. Another shard
or an old unsharded result cannot satisfy a partition. The existing required
`tests (ubuntu-latest)` and `tests (macos-latest)` summaries still require the
entire runtime matrix to succeed. Frozen-candidate jobs run missing units and may
reuse matching successes, retaining browser, ARM Python and `full-release` gates.
Branch protection is unchanged. See [reuse and metadata](#reuse-and-metadata).

Baseline: [Tests run 42029209178](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42029209178)
on 2026-11-05 took about 32 minutes. Its macOS setup step took 8m19s, followed by
22m43s of runtime; Root unittest alone took 15m11s (1,016 cases). Linux setup took
5m06s and Root unittest 12m14s. These measurements motivate partitioning both
setup and Root tests, not just launching components in parallel. Actual elapsed
time still depends on runner availability, shared fixture overhead and package
network operations. In [run 42049095791](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42049095791),
ARM job package installation alone took 26m11s; test sharding does not address
that independent delay. Record observed PR timings rather than promising a fixed
fourfold end-to-end speedup.

## Runner use, dependency caches and artifact retention

The scope job emits `runtime_os` as JSON for the runtime matrix. Linux remains
present, including for documentation-only changes, so the required summaries
still receive a successful runtime dependency. macOS is allocated only when
`tv`, `tv-runtime` or `installer` is selected. UI-only, Android-only and metadata
changes do not allocate macOS runtime shards. Unknown/shared inputs and explicit
full validation still select both platforms and all four shards. The two required
Linux-hosted summary checks retain their existing names and failure semantics.

The frozen desktop runtime workflow cancels superseded runs for the same PR.
Manual dispatches use independent concurrency groups. Candidate builds, signed
QA and release publication keep their existing non-cancelling behavior.

Build, browser and runtime jobs cache npm downloads and pip downloads/wheels
through the existing setup actions. Keys include the lockfile or the applicable
requirements files; the setup actions also partition caches by platform/runtime.
Clean `npm ci` and declared pip installs still run. The Android build uses the
setup-java Gradle cache keyed by Android build scripts, Gradle properties and
wrapper version. These are dependency caches, not cached acceptance evidence;
small authenticated success receipts provide test reuse separately.
No signing files, device data or workspace build outputs are added to caches.

Retention applies to newly uploaded Actions artifacts:

| Artifact purpose | Retention |
| --- | --- |
| Preliminary desktop/console installers, APK and Android test APK (`test_build`) | 14 days |
| Full frozen candidate installers and Android test APK | 90 days |
| Standalone Homebrew QA candidate (`homebrew_candidate`) | 90 days |
| Homebrew package accompanying a preliminary `test_build` | 14 days |
| Direct Root TV candidate and signed Root QA candidate | 90 days |
| Assembled release archive | 90 days |
| Test-unit evidence receipts | 2 days (same UTC-day identity still required) |
| Theme review preview | 3 days |
| Pages deployment artifact | 1 day (explicit existing action default) |

Repository/organization retention policy can cap these requested durations.
A selected build must remain downloadable through acceptance and publication.
Coordinate long-running acceptance before expiry; expired/deleted artifacts
require a new build and the affected acceptance under `docs/RELEASE-FLOW.md`.
There is no age-based cleanup job: existing archives, selected build pins,
acceptance hashes and release assets are not deleted or changed by this policy.
Preliminary builds remain ineligible for final release acceptance. Public release
assets remain the durable user download destination.

## TV transport boundary

`tv` runs UI source/build checks followed by all device runtime checks.
`tv-runtime` runs the identical device runtime body without the UI source/build
checks. Only the exact `native/service/app-inventory.js` transport leaf currently
selects `tv-runtime`, together with `installer` and `setup`. New files under
`native/service/` still select full `tv`. Mixed changes union their selections:
a launcher, service, input, recovery or unknown change broadens the checks.

The transport's consumers are exercised by the inventory/inputs, compiled Helper,
control, watchdog and packaged Root tests. The browser job and UI/theme tests use
fixed inventories; they do not execute that paired SSAP transport. They therefore
remain selected for UI changes, rather than transport-only changes. Both TV
profiles retain all existing emergency/key-up/control/watchdog checks, Root Node
compatibility, complete Root Python discovery, update/recovery and Linux ownership
checks. Do not narrow these tests based only on a filename or a passing install.

`sync-apps.py` is the legacy `install.sh` inventory entry point and selects
`installer` and `setup`. `lgtv.py` also selects `android`, because Android stages it.
`cytv/tv.py` keeps the existing installer/Android/setup coverage. No product source
or inventory contract changes are part of this CI adjustment.

Selecting both `tv` and `tv-runtime` executes their common body once. No-argument
`scripts/test.sh` retains the full existing suite. Direct TV feedback builds treat
`tv-runtime` as requiring full `tv` safety, never as UI-only work.

## Reuse and metadata

`scripts/ci-test-evidence.py` replaces PR-only success markers with small Actions
artifact receipts. Runtime work uses existing component boundaries: `tv` expands
to `ui` plus `tv-runtime`; UI, Android and preview run only on shard 1. Setup,
installer and device runtime retain all four shards. The workflow invokes
`test.sh` once with **only missing units**, and never with an empty argument list
(which would run everything). Linux ownership verification is part of the primary
`tv-runtime` unit. Pinned legacy Node downloads are needed only for fresh units.

Browser core (legacy build, geometry, settings and development UI) is separate
from full-only theme regressions. The complete candidate runs missing theme work;
it does not rerun matching browser core. Optional ARM Python, including privileged
provisioning checks, is another indivisible unit. Dependencies, actual Chromium/
Playwright and QEMU/sysroot versions are identified before evidence lookup.

A unit key binds the complete nonmetadata source snapshot from `release-inputs.py`,
unit/shard/OS, exact Python/Node/dependencies/compiler, runner image and UTC day.
Setup additionally binds the full Git tree, because it tests README, release-plan
and guide content. No new metadata exemption is introduced. Current release-plan
shape is checked fresh outside reuse. README sanity runs within fresh setup or
separately when setup is reused/unselected, avoiding a second identical local
invocation. Package assembly, signing,
artifact validation and physical acceptance are not replaced by test evidence.

Only a same-repository, nonfork, successful first-attempt PR `Tests` run may produce
a receipt, after its freshly executed checks pass. One JSON artifact per existing
runtime/browser/ARM job lists only those fresh units, never reused units. Lookup
verifies successful latest branch evidence, current run attempt and exact successful
originating job, artifact digest/size/head binding, and the tested checkout via
GitHub commit/tree data. A PR merge must contain the run head as its second parent;
claimed fingerprints alone are insufficient. The complete authenticated source
snapshot is recomputed. Fork consumers and explicit reruns execute fresh tests.

Receipts are bounded data: one flat `receipt.json`, at most 128 KiB compressed /
64 KiB uncompressed, strict schema/JSON and no extraction, links or code execution.
Missing, stale, failed, in-flight, altered or unverifiable evidence executes tests.
Discovery checks at most 100 matching repository artifacts with a 60-second
lookup budget and 20-second API deadlines; exceeding a bound is a miss, not a
weaker proof. Each job logs executed units and
links reused units to their originating jobs, also in its step summary. Evidence
upload/API outages cannot grant success or block otherwise passing checks.

[PR cache isolation](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
prevents release-branch jobs from restoring `refs/pull/N/merge` caches, so receipts
are downloaded through the read-only
[Actions artifacts API](https://docs.github.com/en/rest/actions/artifacts).
No new secret, write permission, workflow, matrix or background service is needed.

Bootstrap requires a genuinely successful producer on the new guarded source.
Old PR cache markers cannot become receipts retroactively. Workflow/helper/test
changes remain build inputs and invalidate old evidence; after integration, an
identical combined source/environment can consume the PR's actual successes.
Trusted publication gates and required job names remain unchanged. Hardware
acceptance remains a separate gate.

## Measurements (2026-11-04)

Baseline: [Tests run 41802316602](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41802316602),
PR #293 source `dc911375661889ab6a4bbdbea1c0332f5c123697`. Linux runtime was
13m49s: setup 3m32s, affected runtime 10m02s. Browser was 3m56s and optional Python
32s. macOS setup alone was 5m49s; its runtime was still running at observation.
These are one run's timings, not a universal estimate.

| Changed paths | Previous selection | Current selection | Observed work difference |
| --- | --- | --- | --- |
| `native/service/app-inventory.js`, `cytv/tv.py`, `sync-apps.py` (focused example) | all six original groups + browser | `tv-runtime installer android setup`; no browser | removes UI source checks, preview suite and fixture-only browser job; device checks unchanged |
| `release-plan.json` (metadata example) | setup | setup | no application runtime/browser; duplicate README test removed on the setup runner |
| `docs/development/CI-CHECKS.md` | none | none | remains no application checks |
| `package-lock.json` or an unknown source | all original groups + browser | all groups + browser | no coverage reduction; common TV body runs once |

Local macOS arm64, Node 23.11.0 and Python 3.14.2 measurements with installed locked npm
and declared Python dependencies: excluded UI suite **6.94s**, excluded preview
suite **23.13s**, both passed (30.07s of measured serial work). The browser saving
is a removed parallel job, not 3m56s subtracted from the runtime critical path.
The expensive setup and complete Root runtime tests remain; this bounded split
intentionally does not promise a large end-to-end speedup. CI changes themselves
select the full matrix. Measure future focused runs after normal integration.

Regression checks compare executable command traces (`tv = ui + tv-runtime`),
verify no duplicate common body, scope outputs, unknown/shared unions, full suite,
legacy dependencies, old Node/ownership wiring, fresh metadata checks and required
aggregate failure semantics. Run `python3 -m unittest discover -s tests/setup -p
'test_ci_*.py'` (including shard coverage/failure checks) and the existing
`test_release_inputs.py` suite when changing routing.
