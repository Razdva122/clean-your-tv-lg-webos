"""Keep the frozen browser validation complete when running themes in parallel."""
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BrowserShards(unittest.TestCase):
    def test_shards_partition_the_existing_npm_chain_once(self):
        scripts = json.loads((ROOT / 'package.json').read_text())['scripts']
        commands = scripts['test:themes:browser'].split(' && ')
        shards = [
            json.loads(subprocess.check_output(
                [sys.executable, 'scripts/test-browser-themes.py', str(index), '--list'], cwd=ROOT, text=True))
            for index in (1, 2, 3)
        ]
        self.assertEqual(Counter(command for shard in shards for command in shard), Counter(commands))
        for shard in shards:
            self.assertTrue(shard)
            self.assertEqual(shard, sorted(shard, key=commands.index))
        self.assertEqual(sum(shard.count('npm run test:weather:browser') for shard in shards), 1)

    def test_theme_matrix_and_browser_gate_fail_closed(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        themes = re.search(r'^  browser-themes:\n(.*?)(?=^  [^ ]|\Z)', workflow, re.M | re.S).group(1)
        self.assertIn('if: inputs.full_suite', themes)
        self.assertIn('shard: [1, 2, 3]', themes)
        self.assertIn('fail-fast: false', themes)
        self.assertIn('run: BROWSER_CHANNEL=chromium python scripts/test-browser-themes.py', themes)
        browser = re.search(r'^  browser:\n(.*?)(?=^  [^ ]|\Z)', workflow, re.M | re.S).group(1)
        self.assertIn('needs: [scope, browser-core, browser-themes]', browser)
        self.assertIn('if: always()', browser)
        script = browser.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())

        def status(**updates):
            env = {**os.environ, 'CORE': 'success', 'THEMES': 'success', 'FULL': 'true', **updates}
            return subprocess.run(['bash', '-e', '-c', script], env=env, capture_output=True).returncode

        self.assertEqual(status(), 0)
        self.assertEqual(status(FULL='false', THEMES='skipped'), 0)
        for state in ('failure', 'cancelled', 'skipped', ''):
            with self.subTest(state=state):
                self.assertNotEqual(status(THEMES=state), 0)
                self.assertNotEqual(status(CORE=state), 0)
