"""Root driver refusal survives nonzero SSH exit without retaining remote prose."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

from cytv import diagnostics, state
from cytv.errors import TVCommandError
from cytv.transport import SSH

ROOT=Path(__file__).resolve().parents[2]
ATTEMPT='b'*32
DETAIL={'schema':1,'attempt':ATTEMPT,'exception_type':'PermissionError','errno':13,
        'frames':[{'file':'deploy.py','line':378}]}


class DriverFailureTests(unittest.TestCase):
    def test_driver_emits_bounded_attempt_bound_failure_before_any_device_effect(self):
        program=r'''
import os,sys
from unittest.mock import patch
sys.path.insert(0,'root-edition')
import deploy
with patch.object(deploy,'require_device',side_effect=PermissionError(13,'PRIVATE error and path')):
    sys.argv=['deploy.py','install','--bundle','PRIVATE-bundle']
    deploy.entrypoint()
'''
        env=dict(os.environ,CYTV_ROOT_INSTALL_ATTEMPT=ATTEMPT,PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,'-c',program],cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,1,result.stderr)
        reply=json.loads(result.stdout)
        detail=reply['root_install_failure']
        self.assertEqual(detail['attempt'],ATTEMPT)
        self.assertEqual(detail['exception_type'],'PermissionError')
        self.assertEqual(detail['errno'],13)
        self.assertTrue(any(frame['file']=='deploy.py' and frame['line']>0 for frame in detail['frames']))
        self.assertNotIn('PRIVATE',result.stdout)
        self.assertLess(len(result.stdout),4096)

    def test_nested_native_cause_survives_standard_report_and_history(self):
        from tests.cytv.test_operations import OperationTests, Remote
        fixture=OperationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        installer=fixture.installer(Remote(),'root')
        fixture.store.begin(installer.profile,'install',stage='setup')
        detail={key:value for key,value in DETAIL.items() if key not in ('schema','attempt')}
        installer.tv_info['status']={'product':{'state':'recovery_required','stage':'root-deploy',
            'failure':{'exception_type':'CalledProcessError','exit_status':1,
                'root_driver':dict(detail,message='PRIVATE',attempt=ATTEMPT)}}}
        error=TVCommandError(1)
        report=json.loads(diagnostics.create_report(fixture.store,'install',installer.profile,
            'install-root',error,tv_info=installer.tv_info,status=installer.tv_info['status']).read_text())
        self.assertEqual(report['status']['product']['failure'].get('root_driver'),detail)
        self.assertEqual(report['first_failure']['status']['product']['failure'].get('root_driver'),detail)
        self.assertNotIn('PRIVATE',json.dumps(report))
        self.assertNotIn(ATTEMPT,json.dumps(report))

    def failure(self, raw):
        remote=SSH.__new__(SSH);channel=Mock();remote.channel=lambda _:channel
        def chunks(channel, timeout):
            for offset in range(0,len(raw),17):yield raw[offset:offset+17]
            raise TVCommandError(1)
        remote.chunks=chunks
        with self.assertRaises(TVCommandError) as caught:remote.run('fixed driver command')
        self.assertTrue(channel.close.called)
        return caught.exception

    def test_failed_ssh_keeps_typed_envelope_and_drops_prose(self):
        error=self.failure(json.dumps({'returnValue':False,'error':'PRIVATE',
            'root_install_failure':dict(DETAIL,frames=[*DETAIL['frames'],{'file':'PRIVATE','line':1}],private='PRIVATE')}).encode())
        self.assertEqual(error._root_driver_failure,DETAIL)
        self.assertNotIn('PRIVATE',str(vars(error)))

    def test_unknown_malformed_and_oversized_failures_stay_generic(self):
        for raw in (b'PRIVATE',b'\xff',b'x'*4097,json.dumps({'returnValue':True,'root_install_failure':DETAIL}).encode(),
                    json.dumps({'returnValue':False,'root_install_failure':dict(DETAIL,attempt='PRIVATE')}).encode()):
            with self.subTest(raw_size=len(raw)):
                error=self.failure(raw)
                self.assertFalse(getattr(error,'_root_driver_failure',None))
                self.assertEqual(error.exit_status,1)
                self.assertNotIn('PRIVATE',str(vars(error)))

    def test_matching_attempt_reaches_report_and_first_failure_without_replay(self):
        from tests.cytv.test_operations import OperationTests, Remote
        import re
        fixture=OperationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        for match in (True,False):
            fixture.store.finish(fixture.installer(Remote(),'root').profile)
            with self.subTest(match=match):
                remote=Remote();run=remote.run;failures=[]
                def fail(command,**kwargs):
                    attempt=re.search('CYTV_ROOT_INSTALL_ATTEMPT=([a-f0-9]{32})',command)
                    if attempt:
                        error=TVCommandError(1)
                        error._root_driver_failure=dict(DETAIL,attempt=attempt[1] if match else ATTEMPT)
                        failures.append(error);raise error
                    return run(command,**kwargs)
                remote.run=fail
                installer=fixture.installer(remote,'root')
                fixture.store.begin(installer.profile,'install',stage='setup')
                before=fixture.store.pending(installer.profile)
                with self.assertRaises(TVCommandError) as caught:
                    installer.root_action('install',bundle='/tmp/fixed-bundle',experimental=True)
                self.assertEqual(len(failures),1)
                self.assertEqual(fixture.store.pending(installer.profile),before)
                report=json.loads(diagnostics.create_report(fixture.store,'install',installer.profile,'install-root',caught.exception).read_text())
                if match:
                    expected={key:value for key,value in DETAIL.items() if key not in ('schema','attempt')}
                    self.assertEqual(report.get('root_driver'),expected)
                    self.assertEqual(report['first_failure'].get('root_driver'),expected)
                else:self.assertNotIn('root_driver',report)
                self.assertNotIn(ATTEMPT,json.dumps(report))
                fixture.store.finish(installer.profile)
