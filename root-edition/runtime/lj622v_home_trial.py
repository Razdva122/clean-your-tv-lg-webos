"""Manually started, bounded trial of the Home Helper relay on LJ622V."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import selectors
import stat
import subprocess
import sys
import time

try:
    from .profile_plan import CANDIDATE
    from .transport import call
except ImportError:
    from profile_plan import CANDIDATE
    from transport import call


STATE = Path('/var/lib/clean-your-tv-lj622v-trial')
HOME_STATE = 'luna://com.webos.surfacemanager.home/getCurrentHomeUIState'
SHOW_HOME = 'luna://com.webos.surfacemanager.systemui/showHome'
LAUNCH = 'luna://com.webos.applicationManager/launch'
APP_INFO = 'luna://com.webos.applicationManager/getAppInfo'
PROFILES = 'luna://com.webos.service.systemprofile/getProfiles'
CONFIGS = 'luna://com.webos.service.config/getConfigs'
KEY_FILTERS = 'com.webos.surfacemanager.keyFilters'
EMERGENCY_EXIT = 27


class CapabilityError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def log(stage, result, **fields):
    try:
        print(json.dumps({'event': 'root-ribbon-relay', 'stage': stage,
                          'result': result, **fields}), file=sys.stderr, flush=True)
    except OSError:
        pass  # Diagnostic output must not interfere with releasing the remote.


@contextmanager
def check(stage):
    try:
        yield
    except (TimeoutError, subprocess.TimeoutExpired):
        log(stage, 'timeout')
        raise
    except CapabilityError as error:
        log(stage, error.reason)
        raise
    except (OSError, RuntimeError, ValueError):
        log(stage, 'failed')
        raise
    else:
        log(stage, 'verified')


def ribbon_visible(rpc):
    reply = rpc(HOME_STATE, {}, timeout=1, allow_missing_return=True)
    entries = reply.get('homeUIState')
    home = ([item.get('visibility') for item in entries
             if isinstance(item, dict) and item.get('uiType') == 'home']
            if isinstance(entries, list) else [])
    if len(home) != 1 or type(home[0]) is not bool:
        raise CapabilityError('invalid-ribbon-state')
    return home[0]


def restore_ribbon(rpc):
    if ribbon_visible(rpc):
        return
    try:
        rpc(SHOW_HOME, {}, timeout=1, allow_missing_return=True)
    except TimeoutError:
        # This firmware's showHome handler has no explicit return. Never retry a toggle.
        pass
    deadline = time.monotonic() + 1
    while True:
        if ribbon_visible(rpc):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('Stock Home did not become visible; use the released Home key')
        time.sleep(.1)


def require_activation(rpc, input_probe):
    require_ribbon_firmware(rpc)
    with check('root-app'):
        app = rpc(APP_INFO, {'id': CANDIDATE}).get('appInfo')
        if (not isinstance(app, dict) or app.get('id') != CANDIDATE
                or app.get('type') != 'web' or not app.get('version')):
            raise CapabilityError('root-app-unverified')
    with check('ribbon-readback'):
        ribbon_visible(rpc)
    with check('remote-pair'):
        input_probe()


def require_ribbon_firmware(rpc):
    with check('system-profile-absence'):
        profiles = rpc(PROFILES, {'names': ['defaultApps', 'idleApp'], 'subscribe': False},
                       timeout=2, allow_failure=True)
        if not service_absent(profiles, 'com.webos.service.systemprofile'):
            raise CapabilityError('present' if profiles.get('returnValue') is True else 'absence-unconfirmed')
    with check('keyfilters-absence'):
        filters = rpc(CONFIGS, {'configNames': [KEY_FILTERS]}, timeout=2, allow_failure=True)
        configs = filters.get('configs')
        if service_absent(filters, 'com.webos.service.config'):
            return
        if filters.get('returnValue') is not True:
            raise CapabilityError('absence-unconfirmed')
        if not isinstance(configs, dict):
            raise CapabilityError('invalid-configs')
        if KEY_FILTERS in configs and configs[KEY_FILTERS] != []:
            reason = 'present' if isinstance(configs[KEY_FILTERS], list) else 'invalid-configs'
            raise CapabilityError(reason)


def service_absent(reply, name):
    return (reply.get('returnValue') is False and type(reply.get('errorCode')) is int
            and reply['errorCode'] == -1 and reply.get('errorText') == f'Service does not exist: {name}.')


def probe_relay(relay):
    result = subprocess.run([str(relay), '--probe'], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, timeout=2)
    if result.returncode != 0 or result.stdout.splitlines()[-1:] != [b'PROBE_READY']:
        raise RuntimeError('The Magic Remote input and relay output are incompatible')


def run_relay(relay, rpc, duration=60):
    deadline = time.monotonic() + duration
    with ThreadPoolExecutor(max_workers=1) as worker:
        launch = None
        with subprocess.Popen([str(relay)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              bufsize=0) as process, selectors.DefaultSelector() as events:
            events.register(process.stdout, selectors.EVENT_READ)
            ready = False
            pending = b''
            next_ping = time.monotonic()
            try:
                while time.monotonic() < deadline:
                    now = time.monotonic()
                    if now >= next_ping and process.poll() is None:
                        try:
                            process.stdin.write(b'P')
                        except BrokenPipeError:
                            break
                        next_ping = now + .25
                    timeout = max(0, min(deadline, next_ping) - now) if process.poll() is None else 0
                    if events.select(timeout=timeout):
                        data = os.read(process.stdout.fileno(), 4096)
                        if not data:
                            break
                        lines = (pending + data).split(b'\n')
                        pending = lines.pop()
                        if len(pending) > 512:
                            raise RuntimeError('Invalid Home relay output')
                        if b'READY' in lines:
                            ready = True
                            log('input-capture', 'ready')
                        if any(line.startswith(b'EXIT ') for line in lines):
                            break
                        if ready and b'HOME' in lines and launch is None:
                            launch = worker.submit(rpc, LAUNCH, {'id': CANDIDATE}, timeout=2)
                    elif process.poll() is not None:
                        break
                    if launch is not None and launch.done():
                        if launch.exception() is not None:
                            log('root-launch', 'failed')
                            break
                        launch = None
                if process.poll() is None:
                    process.stdin.close()
                try:
                    reason = process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    log('input-release', 'unconfirmed')
                    raise RuntimeError('Home relay cleanup could not be confirmed') from None
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if launch is not None:
                    launch.cancel()
        # Drain any in-flight Luna call before returning control to LG.
    log('relay-exit', 'exited', status=reason)
    if reason == EMERGENCY_EXIT and ready:
        log('input-release', 'emergency')
        with check('ribbon-restore'):
            restore_ribbon(rpc)
        return 'Stock Home visible'
    if launch is not None and not launch.cancelled():
        launch.result()
    if ready and reason == 24 and time.monotonic() >= deadline:
        return 'Trial expired; relay released'
    raise RuntimeError(f'Home relay exited with status {reason}')


def main():
    if os.geteuid() != 0:
        raise ValueError('The trial requires an existing root session')
    meta = STATE.lstat()
    relay = STATE / 'relay'
    binary = relay.lstat()
    if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != 0 or meta.st_mode & 0o077
            or not stat.S_ISREG(binary.st_mode) or binary.st_uid != 0 or binary.st_mode & 0o022):
        raise ValueError('The trial requires a private root-owned relay directory')
    require_activation(call, lambda: probe_relay(relay))
    print(run_relay(relay, call), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        log('controller', 'stopped-after-error')
        raise SystemExit(1) from None
