# Small issue follow-ups: Home status, retention and SSH trust

2026-11-07. Implementation [PR #401](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/401),
product source `0fd3b46353b52f5d13d04953851160de839b49dd`, based on `7453287ff28eeaba93ccdb124412f8c47ef8590b`.
The maintainer requested all three bounded changes and their integration into the
unfrozen next candidate [#399](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/399).
This record reports source verification, not another user's installation result.

## Resulting behavior

- [#347](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/347): an open
  Root Settings panel follows a transitional Home state with at most ten further
  serialized status reads, spaced one second after each completed read. Stable
  states stop polling. Exhaustion offers the existing Check status action.
  Closing/hiding, child panels and busy actions cancel polling or invalidate
  stale work. No refresh enables Home or clears explicit Off/emergency state.
- [#348](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/348): fixed
  private summaries distinguish no-op/completion, refused admission, absent sealed
  staging inventory, changed proof and filesystem failure. Actual successful
  unlinks remain counted before fsync or later errors. Syslog/stderr are
  independent best-effort sinks; no new retention record or deletion permission
  is added. Automatic re-entry after interrupted retirement remains unimplemented.
- [#368](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/368): the
  recovery guide, CLI links and all thirteen localized help sections distinguish
  changed pinned SSH identity from initial trust and old pending removal. They
  preserve the original profile, keys and receipts, require independent identity
  verification and describe the remaining reviewed trust-recovery procedure.
  No host-key replacement command or actual device recovery is supplied.

## Verification

Host: macOS ARM64, Node 23.11.0, Python 3.14.2 in the existing project virtualenv.
The worktree used the pinned npm dependencies from `npm ci`.

- Red-first real-module Settings regression failed because no follow-up status
  read was scheduled, then passed with the implementation. Controlled timers
  cover convergence, exhaustion, lifecycle cancellation, stale replies and no
  automatic enable. The settings, startup-source and service-handler tests pass.
- Retention's first diagnostic cases failed on silent refusal/no-op and incorrect
  partial-error counts. A second case failed on changed malformed proof being
  classified as initial refusal. The final real-filesystem suite passes 27 tests,
  including unavailable/failing sinks and private-value exclusion.
- `scripts/test.sh ui` passed, including TV web build/compatibility and theme/UI
  checks. The final static preview was rebuilt after the last busy-state guards;
  `test-settings-browser.cjs` passed against that compiled Root UI with synthetic
  service replies, including transitional-to-active convergence and existing
  emergency/resume/Off scenarios.
- `test_install_driver.py`: 51 passed. `tests/system_updates`: 132 passed.
  `scripts/test.sh setup`: 280 passed. The expected malformed-ZIP fixture emits
  Python's duplicate-manifest warning; it is not a failing check.
- `npm run format:check` and `git diff --check` passed. An independent read-only
  whole-branch review found no actionable issues and separately passed the
  27 retention tests and real-module Settings regression.
- The documentation audit confirmed the thirteen-language set, canonical SSH
  recovery anchor and all fifteen new local links.

The initial [PR CI run 42377436108](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42377436108)
failed macOS shard 2 in the existing No-root observer sender-termination test.
A deterministic real-Harness probe reproduced a strict evidence read overlapping
initial claim construction (size zero before the writer completed), producing
the same `changed-file` stack. Commit `24232343` adds only a bounded sender-start
barrier in that test: sender spawn follows claim persistence. Strict evidence,
terminal-success and sender-termination checks remain intact; production observer
source is unchanged. The exact corrected test passed three times, the observer
module passed all 20 tests, and scoped independent review passed.

Final [Tests 42379007285](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42379007285)
passed all eight Linux/macOS runtime shards, browser and ARM Python on final
head `24232343d3501b1e237f3c1675e14de164b6acb2`. Preview build and Integration
policy passed. The tested virtual merge `bdcdb0bc` includes the earlier four
implementation PRs; its Git tree `6c783dab5565cc79a899a26be6437e14c55895e0`
exactly matches actual integration merge `cef7fcc4116530f2b81524a439a0b8c2ed9c0f58`.
These are implementation/combined-source checks, not a frozen full candidate.

## Packaging and acceptance limits

Versions remain at the published baseline until candidate freeze; no build or
acceptance pin was selected here. Root UI, Root updater, coherent System support
and installer payloads need rebuilt delivery. The shared store is copied into
both updater packages; a retained pinned System supervisor does not acquire the
new diagnostics through a UI-only update. No supervisor migration, Helper change,
new permission, endpoint or persistent diagnostic record is introduced.

Product worker summaries are available in its existing private `worker.log`.
OTA workers discard stderr; their summaries depend on Python syslog and platform
logging configuration. Those sinks/retrieval have not been verified on a TV, and
no durable observation is promised when both are unavailable. See the
[retention reference](../development/UPDATE-STORAGE.md#private-retention-diagnostics).

No TV was contacted or changed. TV model, firmware/webOS and remote for this
implementation run are not applicable. Final package versions, physical Home,
sound, standby, cold boot, OTA, rollback and reporter recovery are untested here.
The original #348 interrupted-retirement follow-up and #368 trust-recovery
procedure remain planned; #347 still needs exact-package physical acceptance.
