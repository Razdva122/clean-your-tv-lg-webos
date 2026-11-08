# Unfrozen candidate CI corrections — 2026-11-08

These are host/source checks for PRs #421 and #423, not final-candidate or
physical-TV acceptance. Candidate #425 remains unfrozen, without a new version
or selected full build. No TV was contacted or changed.

## #421: Root permission-refusal catalog

At `d55635a0`, `node root-edition/ui/test-catalogs.cjs` reproduced the Linux/macOS
failure: the newly referenced exact permission-refusal message was absent from
the Root catalogs. Commit `7cd18578` adds that key in all thirteen languages.
The unchanged catalog regression passes with 215 messages, as do
`tests/system_updates/profile.cjs`, `root-edition/ui/test-profile.cjs`, formatting
and diff checks. No matching string, retry limit or health gate changed. See the
[Root readiness source record](2026-11-08-root-ota-permission-readiness.md) on #421.

## #423: native guardian fixture pipe race

[Original failed CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42451742686)
raised `BrokenPipeError` in the no-rearm case after Restore. The retained stop
latch deliberately makes the real C guardian refuse before reading its observer
channels. The parent fixture wrote `READY` after `Popen` returned; a child that
exited first could close both read ends before that write.

The regression now forces that schedule by waiting for the refused child to exit
before returning from the fixture's `Popen` wrapper. It failed at the same READY
write before correction. The fixture now buffers the six-byte READY records while
the parent still holds its read descriptors, before starting the child. No sleep,
retry, ignored pipe error, production deadline or guardian code was added.

The same case now asserts `guard_refused`, unhealthy/stopped state, unchanged
stop-latch bytes and an empty ARMED channel. All 40 `test_keyfilter_guard` cases
pass on macOS with the project virtualenv and real compiled C guardian:

```sh
PYTHONPATH=root-edition/tests python -m unittest test_keyfilter_guard -q
```

The native suite needs host process inspection; a restricted sandbox invocation
could not arm its initial guardian. The host-enabled run reproduced the intended
RED failure, then passed all cases after correction. Formatting and diff checks
passed. Independent read-only review found no blocking issues in either CI fix.
Updated-head GitHub CI is required before integration. The original firmware,
public-feed and packaged icon acceptance remain outstanding on the final artifacts.

## Integration checkpoint

Both corrected heads passed all eight Linux/macOS runtime shards, browser,
optional Python and both OS aggregate checks; website build and integration
policy also passed:

- #421 `7cd18578`: [Tests 42454515821](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42454515821), integrated as `331e9951`.
- #423 `e988828d`: [Tests 42454672347](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42454672347), integrated as `d5f8fb98`.

On combined source `d5f8fb98`, the Root catalog and System profile regressions,
14 icon-budget/priority-service/inventory-fallback tests, 16 release-flow tests
and 3 README metadata tests passed. No unchanged full suite or physical case was
repeated. Candidate #425 collects #415/#421/#423/#424 without selecting a version,
build pin or acceptance. At freeze, rebuild/version shared Home UI, Root Home
and its service, Root Updater's embedded inventory/coordinator, Helper and
embedding installers as appropriate. Final package contents, public-feed/early
launch, budget-exhausting catalog presentation, compatibility and rollback
acceptance remain pending.
