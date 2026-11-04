# Focused PR checks

`Tests` selects the union of affected components with `scripts/ci-scope.py`.
Unknown paths, shared build/dependency files and CI implementation changes still
select every component. A failure in any selected job fails the required
Linux/macOS summaries; an unexpected skip cannot grant a selected gate.

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

The existing `scripts/release-inputs.py` success marker remains the only runtime
reuse mechanism. Its selection fingerprint now includes `tv_runtime`, preventing
reuse across different profile selections. Merged tree, PR/day, OS/image,
Node/Python/dependencies, prior passing run, fork/rerun restrictions and fail-open
to fresh execution on cache/API errors are unchanged. Setup always runs fresh.
README release tests execute once per runner: inside selected setup, or separately
when that runner does not run setup. Release plan shape is always checked.

Full frozen-candidate validation still selects every component and the complete
browser/optional Python gates without PR success reuse. Trusted workflow/policy
changes take effect through normal integration into `main`; this PR cannot change
already-running trusted policy. Hardware acceptance remains a separate gate.

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
legacy dependencies, old Node/ownership wiring, metadata deduplication and required
aggregate failure semantics. Run `python3 -m unittest discover -s tests/setup -p
'test_ci_*.py'` and the existing `test_release_inputs.py` suite when changing routing.
