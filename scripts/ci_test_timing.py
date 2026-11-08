"""Optional unittest timing; preserve discovery order and fixture semantics."""
from collections import Counter
import json
import os
from pathlib import Path
import time
import unittest


class TimingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []
        self.fixtures = []

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()

    def stopTest(self, test):
        self.timings.append({'id': test.id(), 'seconds': time.perf_counter() - self.started})
        super().stopTest(test)


class TimingSuite(unittest.TestSuite):
    # TestSuite owns class/module fixture transitions. Time those hooks without
    # replacing their error/skip/cleanup handling; nested teardown is subtracted.
    def measure(self, result, phase, owner, invoke):
        before = len(result.fixtures)
        started = time.perf_counter()
        try:
            return invoke()
        finally:
            elapsed = time.perf_counter() - started
            nested = sum(row['seconds'] for row in result.fixtures[before:])
            result.fixtures.append({'phase': phase, 'id': owner,
                                    'seconds': max(0, elapsed - nested)})

    def _handleClassSetUp(self, test, result):
        if test.__class__ == getattr(result, '_previousTestClass', None):
            return super()._handleClassSetUp(test, result)
        return self.measure(result, 'setUpClass', unittest.util.strclass(test.__class__),
                            lambda: super(TimingSuite, self)._handleClassSetUp(test, result))

    def _tearDownPreviousClass(self, test, result):
        previous = getattr(result, '_previousTestClass', None)
        if previous is None or (test is not None and previous == test.__class__):
            return super()._tearDownPreviousClass(test, result)
        return self.measure(result, 'tearDownClass', unittest.util.strclass(previous),
                            lambda: super(TimingSuite, self)._tearDownPreviousClass(test, result))

    def _handleModuleFixture(self, test, result):
        if test.__class__.__module__ == self._get_previous_module(result):
            return super()._handleModuleFixture(test, result)
        return self.measure(result, 'setUpModule', test.__class__.__module__,
                            lambda: super(TimingSuite, self)._handleModuleFixture(test, result))

    def _handleModuleTearDown(self, result):
        previous = self._get_previous_module(result)
        if previous is None:
            return super()._handleModuleTearDown(result)
        return self.measure(result, 'tearDownModule', previous,
                            lambda: super(TimingSuite, self)._handleModuleTearDown(result))


def run(suite, output, *, directory, shard, verbosity=1):
    runner = unittest.TextTestRunner(verbosity=verbosity, resultclass=TimingResult)
    started = time.perf_counter()
    result = runner.run(suite)
    report = {'directory': directory, 'shard': shard, 'seconds': time.perf_counter() - started,
              'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
              'tests': result.timings, 'fixtures': result.fixtures,
              'skips': [{'id': test.id(), 'reason': reason} for test, reason in result.skipped]}
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = [f'Unittest timings: {directory}, shard {shard}', 'Slowest tests (including per-test setup/teardown):']
    lines += [f'{row["seconds"]:.3f}s {row["id"]}'
              for row in sorted(result.timings, key=lambda row: row['seconds'], reverse=True)[:20]]
    lines += ['Slowest shared fixture transitions (including cleanups):']
    lines += [f'{row["seconds"]:.3f}s {row["phase"]} {row["id"]}'
              for row in sorted(result.fixtures, key=lambda row: row['seconds'], reverse=True)[:10]]
    lines += [f'Skipped: {len(result.skipped)}; full timings and reasons: {path.name}']
    lines += [f'{count} skipped: {reason}'
              for reason, count in Counter(reason for _, reason in result.skipped).most_common()]
    runner.stream.writeln('\n'.join(lines))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write('\n```text\n' + '\n'.join(lines).replace('```', "'''") + '\n```\n')
    return result
