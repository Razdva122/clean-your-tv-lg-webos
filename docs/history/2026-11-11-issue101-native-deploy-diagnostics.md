# Native Root deploy failure: source preparation, 2026-11-11

Scope: the new `root-deploy` failure in [issue #101](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/101#issuecomment-6776907085).
This is implementation evidence, not an installation result or release acceptance.
No TV was contacted or changed. The reporting C2's underlying deploy cause remains
unknown; no firmware compatibility or successful reinstallation is claimed.

## Investigation and correction

The clean-predecessor path calls synchronous `native-install`, not the detached
ordinary product worker. Therefore its lack of `worker.log` is expected.
`LocalDevice.native_deploy` captured the child stdout/stderr, propagated only
`CalledProcessError`, and the durable summary retained only its exit code.
An actual isolated child regression reproduces this loss with production bundled
imports/admission and substituted device boundaries.

The child now emits the existing bounded Root failure format with a fresh
invocation selector. The parent accepts only a matching envelope of at most
4096 bytes, then the worker and host report revalidate the fixed exception,
callsite and numeric fields. Commands, exception prose, private paths and the
selector are not retained in the report. Existing mutex inheritance, admission,
package submission and uncertain-outcome/no-replay rules remain unchanged.

Source review did not establish a lease-ID, archived-fence or packaged-import
mismatch. Preliminary installer capability checks are weaker than the complete
bundled compositor probe; passing them does not locate this failure. The report
cannot distinguish probe, backend preparation, selfcheck or later provisioning.
No ownership relaxation, model allowlist, clock change or speculative recovery
is added.

## Observe the retained operation without reinstalling

The internal `scripts/root-native-inspection.py` tool runs the current reviewed
compositor probe from host-supplied modules in memory. It does not stage TV code,
install/activate/remove packages, execute retained modules, modify settings/input,
provision Python, perform smoke writes or clear/rewrite journals. Probe input
queries use read-only descriptors and do not grab the remote.

The host must have exactly one matching original saved Root profile/pending native
installation. Inspection uses its original host pin and `persist=False`; hidden
password entry is optional and local. Source material is captured once before
connecting and bound to the explicitly reviewed SHA-256. The already present
private Python slot is checked against the host's pinned archive using read/hash
operations only. A missing or mismatching slot stops; there is no interpreter
fallback or TV runtime repair. Host cache acquisition/normalization may occur.

The probe opens the existing ownership mutex without creating it, checks the
original `root-deploy` request/lease, and rechecks their contents and mutex/directory
identities plus the deployment journal and retained provisioning failure after observation. Missing, busy, foreign,
unsafe, changed or already activated state refuses the observation. The host
profile, trust and pending bytes must also remain unchanged.

The fixed result describes **current admission**, not the historic child error:
a probe pass alone leaves a later deploy failure unexplained; a probe failure
identifies a current constraint/callsite. The separate optional `retained_recovery`
projection reads the already saved `recovery-failure.json` through checked data
access and the existing canonical sanitizer. It can identify a provisioning phase
or fixed service/startup failure without rerunning it. This is retained data,
**not an attempt-bound historic cause**: the old native path did not bind that
record to its invocation, and an absent, stale or ambiguous record is not a pass. Neither result authorizes continuation, cancellation or
another installation. Newer source (including #454's stock-Home admission fix)
can differ from the failed installer's source; preserve the exact source pin and
that distinction when interpreting results.

This is a maintainer preparation procedure, not a request for another reporter
attempt. Before any separately agreed owner observation, retain a clean checkout
of this reviewed PR head, verify the digest below and use the original operation
from the owner's saved local pending record. Do not replace profiles, replay old
workers, change the clock/firmware or remove evidence to make inspection pass.

Use the prepared project virtualenv (`.venv-cytv/bin/python` on macOS/Linux or
`.venv-cytv/Scripts/python.exe` on Windows) as `python` below.

```text
python scripts/root-native-inspection.py digest
python scripts/root-native-inspection.py inspect --operation ORIGINAL_OPERATION --source-sha256 REVIEWED_SOURCE_SHA256 --interactive-auth
```

Reviewed source digest: `fdaa88267e0ef37a6af747cd8e0413d2fd8eb88cca819f870650b063b6802361`.
The source tool has no implicit action; `digest` does not connect to a TV. Actual
Windows execution, private-runtime acceptance on this C2 and probe outcome remain
untested. After any owner operation follow the installation-result consent rules
before publishing a new result; this preparation grants no publication consent.

## Verification ledger

Missing evidence before this work: the synchronous child cause had no retained
representation, the existing native child test substituted all of `deploy.py`,
and no original-operation native probe existed without replay. Those gaps justify
the focused checks below. Existing unrelated release results are reused, not rerun.

- RED: actual isolated child and worker-summary regressions lost the cause; the
  standard-report regression dropped the nested cause. They pass after correction.
- Initial affected host closure: 143 tests passed, one exact-legacy-Node test skipped
  (`test_root_driver_failure`, `test_root_native_inspection`, `test_diagnostic_context`,
  `test_diagnostics`, `test_contract_report`, `test_root_gate`, `test_clean_reinstall`,
  `test_root_gate_operations`, `test_root_passive`, all under `tests.cytv`).
- Review found a timeout allowlist mismatch and source reread after pin validation.
  Both reproduced before correction. Final native inspection/direct-driver command:
  11 tests passed. Current snapshot is captured before connection and no module is
  reread after runtime verification. Host pin/pending preservation, wrong selector,
  missing/busy mutex, changed request, privacy and no provisioning/upload are covered.
- After inspecting `provision.finalize`, one additional missing evidence source was
  identified: its already retained failure record. A new regression failed before
  adding that projection, then seven inspection tests passed, including producer
  and host privacy filtering. That is the changed input requiring the final
  affected inspection check; unchanged Root production checks remain reusable.
- Selected CI for `a0020bc0` passed all required Linux/macOS runtime shards, browser,
  optional Python and policy checks ([run 42889380815](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42889380815)).
  The later retained-data projection changes only the internal inspection; its
  final PR checks remain a separate gate, without a candidate build or TV run.
- Final isolated child/durable-request regression: three tests passed. The stored
  nested cause survives and a second call reads the same request without replay.
- Root dependency closure: 173 tests passed (`test_native_failure`, `test_clean_removal`,
  `test_install_driver`, `test_c1_gate_update_guards`, `test_setup_deploy` with
  `PYTHONPATH=root-edition:root-edition/tests`). These include real package builders,
  coordinator exclusion and existing native mutex inheritance.
- Independent source review and follow-up found no remaining blocking code issue
  after the two corrections. The source digest above was independently checked.
  `git diff --check` passed. Subsequent test-only strengthening also verifies that
  the nested cause survives standard-report first-failure history (five driver
  tests passed); it changes no product inputs or source pin.

No full candidate, signing, installation, rollback or device test was dispatched.
Final release build selection and affected device acceptance remain coordinator
work. Home routing, physical remote/key-up/emergency, audio, standby, cold boot,
OTA/rollback and original C2 recovery are untested by this task.
