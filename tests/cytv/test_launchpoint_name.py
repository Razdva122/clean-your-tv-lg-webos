"""Host simulation only: no physical LG title/startup acceptance implied."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from cytv.launchpoint_name import rename
from cytv.install_settings import apply_services

APP = 'com.gathin.tvhome'

def point(title='Home', identity=None):
    return {'id':APP, 'launchPointId': identity or APP+'_default', 'title':title}

def reply(*points):
    return {'returnValue':True, 'launchPoints':list(points)}

class LaunchPointTests(unittest.TestCase):
    def test_primary_update_readback_ignores_secondary_shortcuts(self):
        remote=MagicMock()
        remote.luna.side_effect=[reply(point(),point('Other','shortcut')), {'returnValue':True}, reply(point('New'),point('Other','shortcut'))]
        rename(remote,APP,'New')
        self.assertEqual(remote.luna.call_args_list[1].args, ('com.webos.applicationManager/updateLaunchPoint', {'launchPointId':APP+'_default','title':'New'}))
        self.assertEqual(remote.luna.call_count,3)

    def test_rejects_missing_ambiguous_wrong_app_and_secondary_only_before_write(self):
        for points in [[],[point(),point()],[point(identity='shortcut')],[dict(point(),id='other.app')]]:
            remote=MagicMock();remote.luna.return_value=reply(*points)
            with self.assertRaises(ValueError): rename(remote,APP,'New')
            self.assertEqual(remote.luna.call_count,1)

    def test_permission_denied_and_false_success_are_not_retried(self):
        for responses,count in [([reply(point()),{'returnValue':False}],2),
                                ([reply(point()),{'returnValue':True},reply(point())],3),
                                ([reply(point()),TimeoutError()],2),
                                ([reply(point()),{'returnValue':True},reply(dict(point('New'),launchPointId='changed',default=True))],3)]:
            remote=MagicMock();remote.luna.side_effect=responses
            with self.assertRaises((ValueError,TimeoutError)):rename(remote,APP,'New')
            self.assertEqual(remote.luna.call_count,count)

    def test_matching_title_reads_again_without_writing(self):
        remote=MagicMock();remote.luna.return_value=reply(point())
        rename(remote,APP,'Home')
        self.assertEqual(remote.luna.call_count,2)
        self.assertTrue(all(c.args[0].endswith('/listLaunchPoints') for c in remote.luna.call_args_list))

    def test_optional_denial_does_not_fail_install_or_drop_local_name_request(self):
        remote=MagicMock();remote.luna.side_effect=[reply(point()),{'returnValue':False},{'returnValue':True}]
        installer=SimpleNamespace(remote=remote,profile={'edition':'no-root'},tv_info={})
        apply_services(installer,{'tv_name':'New'},lambda *_:None)
        self.assertEqual(installer.tv_info['installation_settings'],{'launchpoint_title':'unconfirmed','tv_name':'requested-in-home'})
        self.assertEqual(remote.luna.call_args.args[1]['params']['cytvSetup']['tv_name'],'New')

    def test_invalid_name_never_reads_or_writes(self):
        remote=MagicMock()
        with self.assertRaises(ValueError):rename(remote,APP,'bad\nname')
        remote.luna.assert_not_called()
