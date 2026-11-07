"""Catalog and activity reads have bounded room; other RPCs stay small."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from updater import luna


class ReplyBoundsTests(unittest.TestCase):
    def reply(self,uri,size):
        children=[];spawn=subprocess.Popen
        activity={'activityId':7,'name':'com.local.nativehome.boot',
                  'callback':{'method':'luna://com.local.nativehome.service/tick'}}
        payload={'details':True,'subscribers':True,'current':False,'internal':False}
        def sender(args,**kwargs):
            self.assertEqual(args,['/usr/bin/luna-send','-n','1',uri,json.dumps(payload)])
            self.assertIs(kwargs['stdin'],subprocess.PIPE)
            code=('import json,sys;value=json.loads(sys.argv[1]);value["padding"]="x"*int(sys.argv[2]);'
                  'sys.stdout.write(json.dumps(value));sys.stdout.flush();sys.stdin.buffer.read()')
            child=spawn([sys.executable,'-c',code,json.dumps({'returnValue':True,'activities':[activity]}),str(size)],**kwargs)
            children.append(child);return child
        try:
            with patch.object(luna.subprocess,'Popen',side_effect=sender):return luna.call(uri,payload,timeout=10)
        finally:
            self.assertTrue(children)
            self.assertTrue(all(child.poll() is not None for child in children),'RPC must reap its client on success and failure')

    def test_negative_reply_keeps_fixed_call_and_code_without_private_error(self):
        spawn=subprocess.Popen
        response={'returnValue':False,'errorCode':-1,'errorText':'Denied method call PRIVATE'}
        def sender(args,**kwargs):
            return spawn([sys.executable,'-c',
                'import sys;print(sys.argv[1],flush=True);sys.stdin.buffer.read()',json.dumps(response)],**kwargs)
        with patch.object(luna.subprocess,'Popen',side_effect=sender):
            with self.assertRaises(RuntimeError) as caught:
                luna.call('luna://com.webos.settingsservice/getSystemSettings',{})
        self.assertEqual(getattr(caught.exception,'luna',None),
            {'call':'home-settings','reason':'permission-denied','error_code':-1})
        self.assertEqual(str(caught.exception),'Bus operation rejected')
        self.assertNotIn('PRIVATE',str(caught.exception.__dict__))

    def test_timeout_keeps_call_and_reaps_client_without_private_data(self):
        spawn=subprocess.Popen;children=[]
        def sender(args,**kwargs):
            child=spawn([sys.executable,'-c','import sys;sys.stdin.buffer.read()'],**kwargs)
            children.append(child);return child
        with patch.object(luna.subprocess,'Popen',side_effect=sender):
            with self.assertRaises(TimeoutError) as caught:
                luna.call('luna://com.webos.applicationManager/dev/listApps',{},timeout=0.05)
        self.assertEqual(caught.exception.luna,{'call':'apps-dev','reason':'timeout'})
        self.assertTrue(all(child.poll() is not None for child in children))

    def test_app_inventories_have_bounded_room_for_real_catalogs(self):
        for uri in ('luna://com.webos.applicationManager/dev/listApps','luna://com.webos.applicationManager/listApps'):
            with self.subTest(uri=uri):
                self.assertTrue(self.reply(uri,90000)['returnValue'])

    def test_large_activity_list_keeps_ownership_fields(self):
        reply=self.reply('luna://com.palm.activitymanager/list',90000)
        self.assertEqual(reply['activities'],[{'activityId':7,'name':'com.local.nativehome.boot',
            'callback':{'method':'luna://com.local.nativehome.service/tick'}}])

    def test_activity_list_above_two_mib_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Oversized bus reply'):
            self.reply('luna://com.palm.activitymanager/list',2097152)

    def test_other_and_near_match_uris_keep_64k_limit(self):
        for uri in ('luna://com.webos.settingsservice/getSystemSettings','luna://com.palm.activitymanager/listExtra'):
            with self.subTest(uri=uri),self.assertRaisesRegex(ValueError,'Oversized bus reply'):
                self.reply(uri,90000)


if __name__=='__main__':unittest.main()
