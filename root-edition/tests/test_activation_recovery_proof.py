"""Execute the installer proof against the real runtime journals and locks."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch
import test_persistent_recovery as recovery_fixture
import device_adapter as d
import update_guard
from cytv.root_activation_recovery import SCRIPT


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.fixture=recovery_fixture.IntegrationTests('test_exit_disables_intent_before_real_routing_restore')
        self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.fixture.c.exit(self.fixture.intent)
        (self.fixture.root/'profile-trial.lock').touch(mode=0o600)
        self.failsafe=patch.object(d,'FAILSAFE',self.fixture.root/'failsafe');self.failsafe.start()
        self.addCleanup(self.failsafe.stop)
        # Keep the real product mutex in this test's private parent directory.
        original=update_guard.product_control
        control=patch.object(update_guard,'product_control',side_effect=lambda root,uid:original(self.fixture.root/'root-state',uid))
        control.start();self.addCleanup(control.stop)

    def proof(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):exec(compile(SCRIPT,'<activation-proof>','exec'),{})
        return output.getvalue().strip()

    def test_restored_journals_authorize_inspection_without_rewriting_them(self):
        files=('persistent-intent.json','persistent-binding.json','profile-trial.json')
        before={p:(self.fixture.root/p).read_bytes() for p in files}
        self.assertEqual(self.proof(),'CYTV_ACTIVATION_RECOVERABLE')
        self.assertEqual(before,{p:(self.fixture.root/p).read_bytes() for p in files})

    def test_flags_unfinished_binding_journal_and_busy_lock_deny_proof(self):
        for path in (d.FAILSAFE,self.fixture.root/'update-block.json',d.TARGET,self.fixture.root/'profile-candidate.stage'):
            with self.subTest(path=path.name):
                path.touch(mode=0o600)
                with self.assertRaises((OSError,RuntimeError,ValueError)):self.proof()
                path.unlink()
        for name,field,value in (('persistent-intent.json','phase','recovering'),
                                 ('persistent-binding.json','restored',False),
                                 ('persistent-binding.json','generation',99),
                                 ('profile-trial.json','state','pending')):
            with self.subTest(name=name,field=field):
                path=self.fixture.root/name;before=path.read_bytes();data=json.loads(before);data[field]=value
                path.write_text(json.dumps(data))
                with self.assertRaises((OSError,RuntimeError,ValueError)):self.proof()
                path.write_bytes(before)
        with update_guard.locked(d.STATE,d.EXPECTED_UID):
            with self.assertRaises(BlockingIOError):self.proof()
        import fcntl
        fd=os.open(d.STATE/'profile-trial.lock',os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.proof()
        finally:os.close(fd)

    def test_changed_stock_readback_denies_proof(self):
        current=self.fixture.read();current['sam_home']='other.home'
        with patch.object(d,'read',return_value=current):
            with self.assertRaises(ValueError):self.proof()
