"""Generate browser fixtures through real CLI/Store/recovery and Android adapters.

Only TV IO and verified support-code prerequisites are simulated by the existing
desktop journey fixture. No status, recovery or result method is replaced.
"""
import json
from cytv import cli
from cytv.errors import TVRejected
from cytv.transport import CredentialPrompt
from android.tests.test_bridge import BridgeTests
from tests.cytv.test_desktop_recovery import DesktopRecoveryTests


def scenarios():
    result = {}
    for scenario in ('home-off', 'retain', 'legacy-unknown', 'cancelled-auth', 'running-worker'):
        fixture = DesktopRecoveryTests()
        fixture.setUp()
        try:
            bridge = BridgeTests().module()
            root = scenario != 'legacy-unknown'
            if root:
                fixture.prepare_root_recovery()
            else:
                fixture.store.checkpoint(fixture.profile, stage='removing')
                original = fixture.remote.luna
                def luna(uri, payload, **kwargs):
                    if uri == 'com.webos.appInstallService/status':
                        raise TVRejected('TV rejected the operation. Run cytv doctor; no automatic retry was attempted.',
                                         {'returnValue':False,'errorCode':-1}, uri)
                    return original(uri, payload, **kwargs)
                fixture.remote.luna = luna
            if scenario == 'running-worker':
                original_run = fixture.remote.run
                def run(command, **kwargs):
                    if 'install_driver.py' in command:
                        return json.dumps({'operation':'d'*32,'state':'running','current':False})
                    return original_run(command, **kwargs)
                fixture.remote.run = run
            class Native:
                def __init__(self): self.events = []
                def emit(self, raw): self.events.append(json.loads(raw))
                def request(self, raw):
                    event = json.loads(raw)
                    self.events.append(event)
                    if event['kind'] == 'secret': return None
                    if event.get('options'): return '2' if scenario == 'home-off' else '0'
                    return 'y'
            native = Native()
            callbacks = bridge.Callbacks(native, directory=fixture.store.root)
            console = bridge.AndroidConsole(callbacks)
            if scenario == 'cancelled-auth':
                def connect(profile, directory, secret, trust, **kwargs):
                    secret(CredentialPrompt('Root SSH password (hidden): ', 'root'))
                    raise AssertionError('Cancelled authentication continued')
            else:
                connect = fixture.connect
            profile = fixture.profile
            code = cli.main(['recover','--host',profile['host'],'--edition',profile['edition'],
                             '--port',str(profile['port']),'--data-dir',str(fixture.root),'--language','en'],
                            payload_root=fixture.payload, connect=connect,
                            ask=callbacks.ask, secret=callbacks.secret, write=console)
            result[scenario] = {'events':native.events,'code':code,'pending':fixture.store.pending(profile) is not None,
                                'edition':profile['edition']}
        finally:
            fixture.doCleanups()
    # Real detached observer + simulated vendor process, then common recovery.
    from tests.cytv.test_no_root_integration import OriginalOperationIntegration
    from cytv.recovery import recover
    fixture = OriginalOperationIntegration()
    fixture.setUp()
    try:
        fixture.remote.cut = True
        try:
            fixture.installer.install(fixture.inventory, 'original-fixture-secret')
        except RuntimeError:
            pass
        assert fixture.store.pending(fixture.profile), 'Host interruption must retain the original operation'
        native = Native()
        callbacks = bridge.Callbacks(native, directory=fixture.store.root)
        console = bridge.AndroidConsole(callbacks)
        fixture.installer.progress = console
        recover(fixture.installer, callbacks.ask, console)
        assert fixture.store.pending(fixture.profile) is None
        assert (fixture.root/'requests').read_text().splitlines() == ['com.local.nativehome','com.gathin.tvhome']
        result['original-continuation'] = {'events':native.events,'code':0,'pending':False,'edition':'no-root'}
    finally:
        fixture.doCleanups()
    return result


if __name__ == '__main__':
    print(json.dumps(scenarios()))
