"""Real active health and original resume capture across pre-submission work."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import package_identity as p
import device_adapter as d
import persistent_health as health
import persistent_recovery
import update_guard
import test_persistent_recovery as runtime_fixtures
import test_package_identity as package_fixtures

class ObservedHealth(Exception):pass

class LiveUpdatePresenceTests(unittest.TestCase):
    def exercise(self,edition,phase,condition='healthy'):
        with ExitStack() as stack:
            runtime=runtime_fixtures.IntegrationTests();runtime.setUp();stack.callback(runtime.tearDown)
            runtime.patches[0].stop()  # Replace its metadata stub with actual private authority.
            package=package_fixtures.IdentityTests();package.setUp();stack.callback(package.tearDown)
            states={**package.states,p.ROOT:runtime.root}
            for target,name,value in ((p,'STATES',states),(d,'APPLICATIONS',package.installed/'usr/palm/applications'),(d,'FAILSAFE',runtime.root/'failsafe'),(health,'ROOT',runtime.root/'health')):
                stack.enter_context(patch.object(target,name,value))
            stack.enter_context(patch('intent_runtime.boot_identity',return_value='boot-a'))
            stack.enter_context(patch('shutdown_state.stopping',return_value=False))
            stack.enter_context(patch.object(health.time,'monotonic',return_value=100))
            health.publish('route-a',1)
            tx=package.tx(phase) if edition=='root' else package.system_tx(phase)
            owner=p.UPDATER if edition=='root' else p.SYSTEM
            package.stores[owner].write('transaction',tx)
            self.assertFalse(d.home_present())  # Pending work still forbids ordinary rearm.
            with self.assertRaises(ValueError):d.require_home()
            if phase in ('restoring-route','suspending'):
                update_guard.reserve(tx['id'],runtime.root,os.getuid())
                self.assertFalse((runtime.root/'update-home-resume.json').exists())
            if condition=='changed':
                meta=package.installed/'usr/palm/applications'/p.ROOT/'appinfo.json'
                meta.write_bytes(meta.read_bytes().replace(b'1.0.0',b'9.0.0'))
            elif condition=='emergency':runtime.c.exit(runtime.store.read())
            exits=[]
            def bound_exit(transaction):exits.append(persistent_recovery.bound_exit(transaction))
            with patch.object(health.time,'sleep',side_effect=ObservedHealth):
                try:health.run('route-a',bound_exit)
                except ObservedHealth:pass
            # Capture through the actual original update reservation/ticket code.
            # Physical profile effects remain the runtime fixture's fixed transport.
            def restore(*, cancel_rearm=True):
                intent=runtime.store.read()
                if intent['phase']!='disabled':runtime.c.exit(intent)
                self.assertEqual(runtime.read(),runtime.baseline)
                return 'restored'
            update_guard.reserve(tx['id'],runtime.root,os.getuid())
            with patch.object(update_guard,'_restore',side_effect=restore):update_guard.suspend(tx['id'],runtime.root,os.getuid())
            ticket=update_guard.ticket(runtime.root,os.getuid())
            self.assertEqual(ticket['desired'],condition=='healthy')
            self.assertEqual(ticket['before']['phase'],'active' if condition=='healthy' else 'disabled')
            self.assertEqual(exits,[True] if condition=='changed' else [])
            self.assertFalse(runtime.store.read()['enabled'])
            if condition=='healthy':self.assertEqual(ticket['before'],runtime.intent)
    def test_delayed_pre_submission_preserves_live_health_until_real_capture(self):
        for edition,phases in (('root',('preparing','downloading','backed-up','restoring-route')),('system',('preparing','downloading','backed-up','suspending'))):
            for phase in phases:
                with self.subTest(edition=edition,phase=phase):self.exercise(edition,phase)
    def test_changed_bytes_and_explicit_off_cannot_preserve_resume_intent(self):
        for edition in ('root','system'):
            for condition in ('changed','emergency'):
                with self.subTest(edition=edition,condition=condition):self.exercise(edition,'downloading',condition)
