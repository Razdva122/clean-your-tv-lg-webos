"""Removal fences self-replacement and inventories its private processes."""
import json
import io
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch
import test_remove as fixtures
namespace, APP, SERVICE = fixtures.namespace, fixtures.APP, fixtures.SERVICE


class EngineRemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.args = fixtures.RemovalTests().fixture(Path(self.tmp.name).resolve())

    def process(self, pid, args, *, cwd=None, executable=None):
        path = self.args['proc']/str(pid); path.mkdir()
        (path/'cmdline').write_bytes(b'\0'.join(str(arg).encode() for arg in args)+b'\0')
        (path/'stat').write_text(str(pid)+' (process) '+' '.join(['0']*19+['1234']))
        if cwd is not None: (path/'cwd').symlink_to(cwd)
        if executable is not None: (path/'exe').symlink_to(executable)

    def test_pending_own_package_migration_blocks_removal_without_outer_transaction(self):
        state = self.args['state']; engine = state/'engine-state'; engine.mkdir()
        (engine/'supervisor-migration.json').write_text(json.dumps({'schema':1,'operation':'a'*32,'phase':'submitting'}))
        with self.assertRaisesRegex(ValueError, 'migration'):
            namespace['operate']('disable', **self.args)
        self.assertFalse((state/'cytv-removal.json').exists())

    def test_slot_worker_service_and_policies_are_identified_exactly(self):
        state = self.args['state']; slot = state/'engine-state/slots/a'; slot.mkdir(parents=True)
        self.process(120, ['/usr/bin/python3', '-B', slot/'engine-entry.py', 'worker'])
        self.process(121, ['/usr/bin/node', slot/'system_updater/engine-policy.js', 'verify'])
        self.process(122, [SERVICE], cwd=slot, executable='/usr/bin/node')
        self.process(123, ['/usr/bin/python3', state/'code/service-entry.py', 'service'])
        self.process(124, ['/usr/bin/python3', '/unrelated'+str(slot/'engine-entry.py'), 'worker'])
        self.process(125, ['/usr/bin/node', state/'code/python_boot.js', state, state/'code/service-entry.py', 'service'])
        found = namespace['processes'](state/'code', self.args['proc'])
        self.assertEqual({pid for pid,_,_ in found}, {120,121,122,123,125})
        self.assertEqual({pid for pid,_,worker in found if worker}, {120})

    def test_generation_requires_private_signed_inventory_before_cleanup(self):
        state = self.args['state']; engine = state/'engine-state'; engine.mkdir()
        (engine/'supervisor-generation.json').write_text('{}')
        with patch.dict(namespace, {'generation': lambda state: (_ for _ in ()).throw(ValueError('bad signed generation'))}):
            with self.assertRaisesRegex(ValueError, 'signed generation'):
                namespace['operate']('disable', **self.args)
        self.assertFalse((state/'cytv-removal.json').exists())

    def test_stdin_transport_executes_only_complete_exact_cleanup_source(self):
        from cytv.system_updater_remove import COMMAND, SCRIPT
        source = SCRIPT.encode()
        for raw in (b'', source[:-1], source+b'\n', source.replace(b'APP=',b'BAD=',1)):
            with self.subTest(length=len(raw)), patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw))):
                with self.assertRaises(ValueError):
                    exec(COMMAND, {'__name__':'cleanup_transport_test'})
        result = {'__name__':'cleanup_transport_test'}
        with patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(source))):
            exec(COMMAND, result)
        self.assertTrue(callable(result['operate']))
        self.assertEqual(result['APP'], APP)


if __name__ == '__main__': unittest.main()
