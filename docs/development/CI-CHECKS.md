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
participating shard, so there is some extra setup cost. Serial blocks are assigned
to the existing shards to avoid adding all their work to shard 1:

| Shard | Serial checks, in addition to its Python partitions |
| --- | --- |
| 1 | UI/theme source checks, Android; fresh metadata and Linux ownership checks remain here |
| 2 | Helper/TV compatibility, native controls/watchdog, Root service JS; Homebrew payload/bridge/UI/installer checks; preview |
| 3 | Packaged Root legacy Node prototype and Beta regressions (`tests/root-node-compat.py`, normal and `--beta`) |
| 4 | No-root/system updater JS and complete `tests/system_updates` discovery |

Browser and ARM Python validation retain their separate jobs. Each selected
serial block executes once per OS, with its existing command order and failure
handling. The complete command multiset across shards equals unsharded execution;
there is no concurrent execution inside a checkout. Browser identity is bound to
runtime shard 2 (Homebrew and preview), conservatively retaining shard 1's
existing UI binding; an unknown browser cannot grant reused evidence. `preview`
receipts are selected only on shard 2; UI/Android receipts remain on shard 1.
Changed routing is itself a global fingerprint input, so receipts
for the previous layout cannot attest the new layout.

Without `--shard`, local profiles and the no-argument full suite are unchanged.
For local shard counts below four, serial owners fold modulo the count; `1/1`
therefore retains every block. The Python partition rule is unchanged.
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

The serial redistribution uses [run 42494183249](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42494183249)
(2026-11-08, `62935a34`) as its baseline: runtime jobs were 12m29s/11m45s on the
first Linux/macOS shards versus 6m27s–9m28s/6m53s–8m18s on the other shards.
The first Linux job's executable log showed about 90s of TV/legacy work now shared
by shards 2 and 3, and 38s of Homebrew work moved to shard 2, plus 49s of updater work moved
to shard 4. These are observations from that run, not a fixed speedup promise.
Preview shares Homebrew's browser-equipped shard 2. Routing regressions extend
existing test methods instead of adding discovery occurrences, so the checks for
this scheduling change do not themselves repartition later setup tests.

## Runner use, dependency caches and artifact retention

### Installer test timings and skips

Fresh runtime installer shards and desktop build host tests retain
`cytv-test-timings-*` JSON artifacts for 14 days, including on test failures.
The step summary lists the slowest 20 test occurrences and 10 shared fixture
transitions. JSON includes every executed occurrence, shared class/module setup
and teardown (including cleanups), overall test execution time, and skip reasons.
Per-test durations include that test's setup, body and teardown. Fixture hook
durations include hook overhead; nested module teardown is subtracted from module
setup to avoid double counting. Discovery and dependency installation are outside
the reported execution time. Repeated imported tests are preserved.

Reproduce the report locally with the project Python environment:

```sh
QT_QPA_PLATFORM=offscreen .venv-cytv/bin/python scripts/test-shard.py \
  -s tests/cytv --timings build/test-timings/cytv.json
# Optional: add --shard 2/4 for one partition.
```

`CI_TEST_TIMINGS_DIR=build/test-timings scripts/test.sh installer` enables the
same report through the existing profile. Unset, the local profile is unchanged.
The shell consumes this variable without exporting it to nested test profiles,
so those profiles cannot overwrite the outer report.
Timings are diagnostics, never authenticated success receipts. A reused unit has
no fresh timing artifact. Cancelled processes and discovery failures may have no
JSON report; the existing test gate still fails.

Conditional skips do not imply obsolete coverage. POSIX filesystem/process
fixtures run on Linux/macOS rather than Windows; Qt/wallpaper cases need desktop
build dependencies. Exact legacy Node cases run in Linux runtime jobs, and Linux
root-only Python bootstrap cases run in the privileged optional-Python step.
The legacy UID-501 ownership scenario requires that specific unprivileged host
identity; inspect its actual skip records before changing the fixture. Do not
remove these scenarios merely because another job skips them.

### Evidence lookup cost

Each lookup memoizes successful JSON API responses only for that invocation,
within its existing 60-second budget. The next lookup re-reads mutable run state;
failed requests are not cached. Binary receipts retain their existing size/digest
checks. A receipt with no key matching any still-missing unit is rejected before
provenance requests. Matching keys alone never grant coverage: originating run,
latest-run status, successful job, checkout/tree and projected inputs are still
authenticated. Logs show elapsed lookup time, API request count, memoized response
hits and receipts rejected by keys, without logging raw API responses.

### Runner allocation and retention

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
| Installer test timings and skip reasons | 14 days |
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
to `ui` plus `tv-runtime`; UI and Android run only on shard 1, preview only on
shard 2. Setup,
installer and device runtime retain all four shards. The workflow invokes
`test.sh` once with **only missing units**, and never with an empty argument list
(which would run everything). Linux ownership verification is part of the primary
`tv-runtime` unit. Pinned legacy Node downloads are needed only for fresh units.

Browser core (legacy build, geometry, settings and development UI) is separate
from full-only theme regressions. The complete candidate runs missing theme work;
it does not rerun matching browser core. Optional ARM Python, including privileged
provisioning checks, is another indivisible unit. Dependencies, actual Chromium/
Playwright and QEMU/sysroot versions are identified before evidence lookup.
Primary runtime fingerprints also probe the actual system Chrome channel used by
preview and installer UI tests. A missing/unavailable browser fingerprint forces
fresh checks and cannot produce a reusable receipt; an unknown value never
matches another unknown value.

A v2 unit key binds an audited projection of the authenticated nonmetadata Git
snapshot, unit/shard/OS, exact Python/Node/dependencies/compiler, runner image and
UTC day. Independent executable test families no longer invalidate every block.
For example, changing `tests/cytv/test_long_ssh_commands.py` invalidates installer
work and setup, while unchanged UI/device/browser/ARM units can retain a matching
success. The complete owning family participates on every shard, because test
additions/deletions can repartition later cases.

This first projection is deliberately conservative: product code, dependencies,
workflows/CI helpers, all setup/framework tests, generic/shared fixtures, package
initializers, unknown paths and nonregular modes remain inputs to every unit.
Audited installer fixtures consumed by Android/browser recovery and the ARM Python
fixture belong to those units too. Theme helpers/fixtures remain global rather
than being guessed from a filename suffix. Cross-family imports must be audited
when dependencies change; ordinary PR routing alone is not dependency evidence.
See `test_units`/`keys` in the evidence helper and its Git-mutation regression matrix.

Setup additionally binds the full Git tree, because it tests README, release-plan
and guide content. No release build-input exemption is introduced. Current
release-plan shape is checked fresh outside reuse. README sanity runs within
fresh setup or separately when setup is reused/unselected, avoiding a second
identical local invocation. Package assembly, signing, artifact validation and
physical acceptance are not replaced by test evidence; this change does not reuse
installer packages across guarded source changes.

Receipts originate from same-repository, nonfork, first-attempt PR `Tests`
runs or explicit full candidates dispatched on `release/next`. They list only
freshly passed units, never reused units. PR lookup requires a successful run and
latest branch evidence. Full-candidate lookup requires the exact candidate
workflow/ref, completed scope/full-release markers, and a completed successful
originating job; another job may have failed. The latest preceding candidate's
corresponding job must also be green. A newer failure, missing job, in-flight run
or rerun prevents falling back to an older success.

Lookup verifies current attempt, artifact digest/size/head binding and tested
checkout through GitHub commit/tree data. A PR merge must contain the run head as
its second parent; full candidates must test their exact run head. Each projected
source is recomputed from the complete authenticated producer tree before
comparing keys. Fork consumers and explicit reruns execute fresh tests.

The four existing desktop build jobs have a separate `installer-host` unit for
`tests/cytv`, distinct from runtime installer/Homebrew coverage. Its fingerprint
includes actual Git, Zig, Python/Node, installed dependencies, Qt platform and
runner/image identities, plus installed Linux desktop libraries. Unknown required
identity prevents reuse and recording. Every package is still built and its
installed-package checks still run.

Receipts are bounded data: one flat `receipt.json`, at most 128 KiB compressed /
64 KiB uncompressed, strict schema/JSON and no extraction, links or code execution.
Missing, stale, failed, in-flight, altered or unverifiable evidence executes tests.
V2 discovery names bind kind/OS/shard/environment and policy version, not the
whole source or selected-unit set. One receipt per existing job contains only its
freshly executed unit keys, so a different-source receipt can supply a matching
subset. Discovery checks at most 100 matching repository artifacts with a 60-second
lookup budget and 20-second API deadlines; exceeding a bound is a miss, not a
weaker proof. Each job logs executed units and
links reused units to their originating jobs, also in its step summary. Evidence
upload/API outages cannot grant success or block otherwise passing checks.

[PR cache isolation](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
prevents release-branch jobs from restoring `refs/pull/N/merge` caches, so receipts
are downloaded through the read-only
[Actions artifacts API](https://docs.github.com/en/rest/actions/artifacts).
No new secret, write permission, workflow, matrix or background service is needed.

Bootstrap requires freshly passed producer jobs on the new guarded source.
Old v1 receipts, PR cache markers and historical full-run jobs cannot become v2
receipts retroactively. Workflow/helper/test changes remain release build inputs;
changes to the projection/trust policy invalidate every unit. After integration,
matching projected inputs/environment can consume actual PR or candidate job
successes, even when another test family changed. The first new-policy full
candidate runs fresh when this batch deliberately skips separate PR suites. A first-attempt candidate can consume
these proofs; explicit reruns remain fresh under the existing trust rule.
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
