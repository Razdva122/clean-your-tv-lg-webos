import importlib.util,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('screensaver_provision',Path(__file__).parents[1]/'provision.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class ScreensaverProvisionTests(unittest.TestCase):
 def original(self):return {'service':'[D-BUS Service]\nName='+p.NAME+'\nExec=/usr/bin/run-js-service -n '+str(p.SERVICE)+'\n','role':json.dumps({'appId':p.NAME}),'client':'{}','api':'{}'}
 def test_explicit_capability_adds_only_ordinary_launch_and_public_tvpower(self):
  result=p.plan(self.original(),p.WALLPAPER_CAPABILITIES+['screensaver-v1']);role=json.loads(result['role']);clients=json.loads(result['client']);api=json.loads(result['api'])
  self.assertEqual(clients[p.NAME],['activity.operation','application.launcher'])
  self.assertEqual(role['permissions'][0]['outbound'],['com.webos.service.activitymanager','com.palm.activitymanager','com.webos.applicationManager','com.webos.service.tvpower'])
  for method in ('Status','Configure','Preview','Activity','Eligible','Stop'):self.assertIn(p.NAME+'/screensaver'+method,api[p.NAME+'.control'])
  self.assertNotIn('tv.management',json.dumps(clients));self.assertNotIn('launcher.control',json.dumps(clients));self.assertNotIn('all',clients[p.NAME])
 def test_older_capabilities_do_not_gain_new_privileges_or_methods(self):
  for capability in ([],p.RECEIVER_CAPABILITIES,p.WALLPAPER_CAPABILITIES,p.COMPOSITOR_CAPABILITIES):
   result=p.plan(self.original(),capability)
   self.assertEqual(json.loads(result['client'])[p.NAME],['activity.operation']);self.assertNotIn('screensaver',result['api'].decode())
if __name__=='__main__':unittest.main()
