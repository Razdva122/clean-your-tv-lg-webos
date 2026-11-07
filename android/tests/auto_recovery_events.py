"""Actual CLI/Store/Android events for failed-setup result-screen journeys."""
import json
from unittest.mock import Mock, patch

from android.tests.test_bridge import BridgeTests
from cytv import cli
from cytv.errors import UserError
from tests.cytv.test_desktop_recovery import DesktopRecoveryTests


def scenarios():
    journeys = {}
    for name in ('root-failure', 'root-cancel', 'root-access'):
        fixture = DesktopRecoveryTests()
        fixture.setUp()
        try:
            if name != 'root-access':
                fixture.prepare_root_recovery('install')
            class Native:
                def __init__(self):
                    self.events = []
                def emit(self, raw):
                    self.events.append(json.loads(raw))
                def request(self, raw):
                    return 'y'
            native = Native()
            bridge = BridgeTests().module()
            console = bridge.AndroidConsole(bridge.Callbacks(native, directory=fixture.store.root))
            action = 'uninstall' if name == 'root-access' else 'install'
            connect = (fixture.connect if name == 'root-access' else
                       Mock(side_effect=EOFError if name == 'root-cancel' else UserError('Unconfirmed')))
            with patch('cytv.no_root_cleanup._device', return_value={
                    'schema':1,'root_present':['Root state'],'present':[],'blocked':[]}):
                profile = fixture.profile
                code = cli.main([action,'--yes','--host',profile['host'],'--edition',profile['edition'],
                                 '--port',str(profile['port']),'--data-dir',str(fixture.root),'--language','en'],
                                payload_root=fixture.payload, connect=connect, write=console)
            journeys[name] = {'events':native.events,'code':code,'action':action,'edition':profile['edition']}
        finally:
            fixture.doCleanups()
    return journeys


if __name__ == '__main__':
    print(json.dumps(scenarios()))
