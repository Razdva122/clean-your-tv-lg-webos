"""Real subprocess checks for the legacy cleanup reader; no TV paths or RPCs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required')
class CleanupChildren(unittest.TestCase):
    def run_reader(self, body):
        source=(Path(__file__).resolve().parents[1]/'cleanup_tail.js').read_text()
        helper=source[source.index('function unavailable('):source.index('async function rpc(')]
        script="""var real=require('child_process'),children=[],cp={spawn:function(command,args,options){
var child=real.spawn(command,args,options);children.push(child);return child;}};
"""+helper+"\n(async function(){"+body+"""
if(children.some(function(child){return child.exitCode===null&&child.signalCode===null&&child.pid;}))throw Error('child not reaped');
process.stdout.write(JSON.stringify({ok:true}));
})().catch(function(error){process.stderr.write(error.stack);process.exitCode=1;});
"""
        result=subprocess.run([os.environ.get('NODE8','node'),'-'],input=script,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'ok':True})

    def test_stdin_stays_open_and_output_drains_through_successful_exit(self):
        self.run_reader("""
var value=await childRead(process.execPath,['-e',
"process.stdin.resume();process.stdin.on('end',function(){process.exit(42);});setTimeout(function(){process.stdout.write('reply');process.exit(0);},30);"],2000);
if(value!=='reply')throw Error('reply lost');
""")

    def test_timeout_nonzero_launch_failure_and_output_limit_fail_closed(self):
        self.run_reader("""
var cases=[['/missing-cytv-child',[],1000,'cleanup-readback-unavailable','client-start-failed'],
[process.execPath,['-e','setInterval(function(){},1000);'],50,'cleanup-readback-unavailable','timeout'],
[process.execPath,['-e',"process.stdout.write('private');process.exit(17);"],1000,'cleanup-readback-unavailable','client-exit'],
[process.execPath,['-e',"process.stdout.write(Buffer.alloc(2097153));setInterval(function(){},1000);"],2000,'cleanup-readback-malformed'],
[process.execPath,['-e',"process.stderr.write(Buffer.alloc(2097153));setInterval(function(){},1000);"],2000,'cleanup-readback-malformed']];
if(process.platform!=='win32')
 cases.push([process.execPath,['-e',"process.kill(process.pid, 'SIGTERM');"],1000,'cleanup-readback-unavailable','client-signal']);
for(var i=0;i<cases.length;i++){
 var item=cases[i],error=null;
 try{await childRead(item[0],item[1],item[2],'inputs-list');}catch(value){error=value;}
 if(!error||error.message!==item[3])throw Error('unverified child accepted');
 if(item[4]){
  var detail=error.cleanup_readback;
  if(!detail||detail.check!=='inputs-list'||detail.reason!==item[4])throw Error('wrong readback detail '+item[4]);
  if(item[4]==='client-exit'&&detail.exit_status!==17)throw Error('lost exit status');
 }else if(error.cleanup_readback)throw Error('misclassified malformed output');
}
""")
