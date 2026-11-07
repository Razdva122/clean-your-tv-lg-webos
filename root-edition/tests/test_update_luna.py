"""Activity inventory has its own bounded reply budget; other RPCs stay small."""
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
