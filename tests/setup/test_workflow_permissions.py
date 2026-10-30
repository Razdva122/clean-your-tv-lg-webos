"""Check release caller permissions and credentials reaching API-using steps."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReleasePermissions(unittest.TestCase):
    def test_assembler_steps_receive_an_authorized_github_token(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text()
        top, jobs = workflow.split('jobs:\n', 1)

        def mapping(text, name, indent):
            block = re.search(r'^' + ' ' * indent + name + r':\n((?:^' +
                              ' ' * (indent + 2) + r'.*\n|^\n)*)', text, re.M)
            if not block:
                return {}
            return dict(re.findall(r'^' + ' ' * (indent + 2) +
                                   r'([\w-]+): (.+)$', block.group(1), re.M))

        checked = []
        for job, body in re.findall(r'^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)', jobs, re.M | re.S):
            if '    steps:\n' not in body:
                continue
            config, steps = body.split('    steps:\n', 1)
            permissions = mapping(config, 'permissions', 4) or mapping(top, 'permissions', 0)
            inherited = {**mapping(top, 'env', 0), **mapping(config, 'env', 4)}
            for step in re.split(r'(?=^      - )', steps, flags=re.M):
                if 'assemble-release.py' not in step:
                    continue
                checked.append(job)
                effective = {**inherited, **mapping(step, 'env', 8)}
                with self.subTest(job=job, step=step.splitlines()[0]):
                    self.assertEqual(effective.get('GH_TOKEN', effective.get('GITHUB_TOKEN')),
                                     '${{ github.token }}',
                                     'Every assembler invocation can call gh; a token in another step is not inherited')
                    self.assertIn(permissions.get('actions'), ('read', 'write'))
        self.assertEqual(checked.count('plan'), 2, 'Inspect source resolution and release planning')
        self.assertEqual(checked.count('assemble'), 2, 'Inspect final assembly and unpublished-draft planning')

    def test_release_caller_allows_callee_job_permissions(self):
        caller = (ROOT / '.github/workflows/release.yml').read_text()
        publish = re.search(r'^  publish:\n(.*?)(?=^  [\w-]+:|\Z)', caller, re.M | re.S).group(1)
        granted = dict(re.findall(r'^      ([\w-]+): (read|write|none)$', publish, re.M))
        callee = (ROOT / '.github/workflows/publish-release.yml').read_text()
        requested = re.findall(r'^      ([\w-]+): (read|write|none)$', callee, re.M)
        levels = {'none': 0, 'read': 1, 'write': 2}
        for scope, level in requested:
            with self.subTest(scope=scope, level=level):
                self.assertGreaterEqual(levels[granted.get(scope, 'none')], levels[level],
                                        'Reusable jobs cannot elevate the caller token, even when skipped')


if __name__ == '__main__':
    unittest.main()
