# Next candidate integration, 2026-11-07

This record covers the maintainer-requested integration of implementation PRs
#370, #371, #372, #375, #377, #379 and #380 after published v1.10.0, into draft candidate #374 on
`release/next`. It selects no version or build and is not release acceptance.
No TV was accessed or changed. Existing uncommitted work in the maintained
checkout was left untouched; integration used a temporary managed worktree.

## Source and conflict resolution

- #372 (`3755b9b1c79b8d31ecccfce991bdc545ae60cf18`) passed selected CI and
  frozen desktop runtime checks before merge commit
  `648b8f06cae6cc64aed33ab3770586f74091667b`.
- #370 required eight formatting-conflict resolutions. Each three-way input was
  formatted with the pinned Prettier configuration before merging. Acorn AST
  comparisons confirm that all four affected product JS files retain the
  original inventory PR's logic. The integration commit is
  `1ef97663ecde153427d00b07b7e1800e9fbc4d1d`.
- #371 required two analogous JS conflict resolutions. Its compositor lease AST
  matches the original PR; the automatic Python merges retain both build-resource
  refactoring and compositor admission changes. The integration commit is
  `437b95c6adea04a7044d37ccb6cb2c1247c49ece`.
- Test-only commit `ad72e9040babcd5e45fa28419c64e0742333c22b` isolates the
  controller-expiry test from concurrent broker expiry handling. #371 includes
  #370 as a dependency at `8b0d98a0b5675db65178cc3382c033a9537b6f1c`, so its
  updated-head CI checks both changes together.

- #375 appeared during collection and was explicitly handed to this coordinator.
  Its cleanup diff was reviewed, including the retained `device_adapter.python_binding`
  recovery export and current cleanup-module consumers. The combined source head
  `90378d0271e6032519f9caee95f688dfc8be78c0` includes all four implementation PRs;
  50 clean-removal, 36 compositor runtime/integration and 19 host-gate tests passed.
- GitHub retained stale base/mergeability data after earlier integration. Explicit
  base merges changed only `release-plan.json`: #371
  `36381b5e02ae406ff861195275b714b7b857138e` and #375
  `dede5b589eba8c8856ca50c1a66a713db25a4efb`. `verify_inputs` confirms each
  has the same build inputs as its previously green product head. No product
  conflict or new behavior was introduced; refreshed-head CI remained mandatory.
- Implementation merge commits already observed: #370 `82313a7e87a8eb2c177725485a3cd84969b2cd52`;
  #371 `63f9b0a2a35edf44738f88e4ab04b05419f87aac`.

## Verification

`npm ci` completed before checks. Host Python checks reused the maintained
`.venv-cytv`; Node was v23.11.0. Final CI links/outcomes are recorded below and in #374.

- #370 after formatting integration: all 70 focused regressions passed:
  `node --test tests/apps/inventory-fallback.cjs tests/apps/native-icon-quality.cjs tests/controller-watchdog.cjs tests/home-control-bridge.cjs tests/home-control-jail.cjs`.
- Compiled Helper compatibility/regressions on current host Node,
  `npm run test:compat`, `npm run lint:compat`, `npm run format:check` and
  `git diff --check` passed. The original PR's exact legacy Node results remain
  scoped to its dated record; this integration does not claim a fresh local
  legacy-runtime run.
- #371 after formatting integration: both JS lease/filter suites and 74 Python
  regressions passed: 36 `test_c1_keyfilter*.py`, 4 recovery-manifest tests,
  15 installer-capability tests and 19 host-gate tests. Formatting checks passed.
- README release metadata checks passed all 3 tests against unchanged v1.10.0
  published metadata.
- After the test-only correction: all 40 native guardian tests passed. Ten
  consecutive repetitions of the controller-expiry test passed. On the combined
  `8b0d98a0` tree, all 70 inventory/controller/broker regressions and both JS
  lease/filter suites passed again.

### Failed and superseded checks

The original #371 CI run and the first #370 formatting-integration CI run failed
`test_stale_independent_channels_and_broker` on macOS: expected
`controller_expired`, observed `external_stop`. Source tracing found two valid
concurrent stop paths: the guardian detects stale controller input, while
`--lease` can first latch `lease_expired` after reading stale controller health.
The fixture kept refreshing the broker through the shared 2-second deadline,
so it asserted one scheduler ordering. The correction stops broker renewal
before that deadline while keeping the broker fresh beyond controller expiry;
it retains the exact expected reason and unhealthy assertion. Production native
code, timing limits, safety latches and release gates are unchanged.

The original-run retry and the superseded integration runs were cancelled by
new-head validation or explicitly to free CI capacity. Their failures are not
reported as passing.

## Documentation, packaging and remaining gates

Reviewed the unpublished app-management/install/recovery/compositor sections,
the two source evidence records, build/contribution guidance and the thirteen
translated setup notices included by #371. #370 changes no setup/control steps.
Final compatibility/prerequisite/update/removal and translation review remains
part of candidate freeze. Stable downloads stay at v1.10.0 until versions are
selected; historical hardware evidence is not relabeled.

Changed Home/renewal and Helper source needs synchronized version bumps and new
HD/FHD packages; retaining the published Helper pin will not deliver the native
controller fix. Desktop/Android embedding payloads, Root variants and shared
builders need final artifact validation. Independent updater version/build
impact needs review. Experimental compositor remains fresh-install only, with
no ordinary OTA or automatic rearm. Homebrew Installer remains unreleased.

No final combined candidate build is pinned. Device model, firmware/webOS,
remote, installer-platform/device result, physical Home/Back/emergency release,
audio, HDMI/CEC, standby, cold boot, installation/update/removal and rollback are
untested for these artifacts. Do not carry old acceptance across changed bytes.
Original #207 IR routing and #364 device compatibility remain unresolved and
open; no new reporter device operation is requested by integration.

`acceptance-report` conservatively selects `controls`, `startup`, `ui-controls`
and `update-recovery`; these remain pending physical results, not inferred passes.

The first four implementation PRs were merged before the later follow-ups. #375 merge commit: `21e9ccf284926649aed77f3ba2f470c434828438`.
Selected checks passed on refreshed heads #371 `36381b5e` ([run](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42357316214))
and #375 `dede5b58` ([run](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42357724857));
the earlier green product checks and frozen desktop checks remain linked in #374.

## Final seven-PR reconciliation

PR #377 was integrated after its selected [combined-source tests](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42358921172)
and [frozen desktop checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42358921056)
passed at `b568ed3a54e50139718814c1c383645a1afc5ab7`. Its current-base merge
required no conflicts; 21 auto-recovery, 85 operations and 50 Root clean-removal
tests, the real CLI/Store/Android-event Chrome journey and formatting also passed
locally. The old `479c8b05` run was cancelled to release its branch concurrency
slot and is not green evidence. Merge: `186eb42586ba9c992b5e38a993226f644219aa87`.
[Recovery source evidence](2026-11-07-installer-recovery-completion.md) retains
its own broader checks, overlap and physical limits.

The final collector also found concurrently integrated #379 and #380. Their
changes, PR discussions, reviews, current issue discussions and dated records
were reviewed; their existing inventory summaries and metadata edits were kept.
#379 adds Root removal catalog fallback and bounded first/latest failure detail;
#380 preserves typed No-root observer failures and launches Node through POSIX
unset. These are partial source improvements; original #240/#376 causes and
reporter recovery remain unverified. Both were already merged while their CI
was pending; their selected [#379 CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42359748100)
and [#380 CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42359837874)
subsequently passed. [Root removal evidence](2026-11-07-issue240-removal-catalog.md)
and [observer evidence](2026-11-07-no-root-observer-evidence.md) retain exact scopes.

No implementation CI run above is presented as full frozen-candidate validation
of all seven changes. On the actual combined `186eb425` tree, this command passed:
`LC_ALL=en_US.UTF-8 PYTHON=<project-venv>/bin/python scripts/test.sh installer android setup`.
Results: setup 266 tests; installer 1,025 tests with two platform skips; Android
43 tests; Homebrew runtime/bridge/UI checks and the additional 8/6/6-case groups
also passed. This run includes actual combined recovery/diagnostic interactions,
not a sum of earlier PR results. `verify_inputs` confirms that subsequent
release-branch metadata edits preserve those tested build inputs.

The final inventory contains all seven PRs, no exclusions, no selected version
and no pinned build. Root Updater/shared RPC infrastructure, desktop/Android
payloads and the previously recorded Home/Helper/Root changes require coordinated
versions, rebuilds, exact package/feed verification and rollback acceptance.
Updated recovery guides and all thirteen localized notices remain candidate-only.
The local baseline `prefixed-webkit` shortcut-row failure in the original #370
record remains visible for final candidate browser review. Full versioned build,
complete candidate browser/runtime coverage and affected physical acceptance are
pending. No TV was contacted, no old device evidence was carried, and no failure
or untested path was converted to a pass.
