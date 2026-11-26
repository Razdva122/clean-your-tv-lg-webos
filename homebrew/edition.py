"""Read-only Root Home admission for a fresh Homebrew installation."""
import json
import os
import select
import subprocess
import sys
import time

from cytv import root_capabilities as home
from cytv.checks import CheckList
from cytv.errors import TVCommandError


class LocalReads:
    """Run only the desktop classifier's fixed queries on this TV."""

    def __init__(self):
        self.embedded_ruled_out = False

    def run(self, probe, *, timeout):
        probes = (home.NATIVE_HEADERS, home.EMBEDDED_HEADERS, home.NATIVE_HOME_MOUNT_PROBE)
        if probe not in probes:
            raise ValueError('unknown capability probe')
        try:
            return self._read(['/bin/sh', '-c', probe], timeout)
        except TVCommandError as error:
            if probe == home.EMBEDDED_HEADERS:
                self.embedded_ruled_out = error.exit_status in (1, home.NATIVE_HOME_UNAVAILABLE)
            raise

    def luna(self, uri, payload, *, timeout, allow_missing_return=False):
        allowed = dict(home.CALLS.values())
        allowed.update({
            'com.webos.service.tv.systemproperty/getSystemInfo': {
                'keys': ['modelName', 'firmwareVersion', 'sdkVersion']},
            'com.webos.service.config/getConfigs': {
                'configNames': ['com.webos.surfacemanager.keyFilters']},
            'com.webos.surfacemanager.home/getCurrentHomeUIState': {},
        })
        if uri not in allowed or payload != allowed[uri]:
            raise ValueError('unknown capability query')
        return self._read(['/usr/bin/luna-send', '-n', '1', 'luna://' + uri,
                           json.dumps(payload)], timeout, json_reply=True)

    @staticmethod
    def _read(args, timeout, *, json_reply=False):
        # Some firmware requires luna-send's stdin to remain open until the reply.
        with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, env={
                                  'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'
                              }) as client:
            output = bytearray()
            deadline = time.monotonic() + min(timeout, 8)
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([client.stdout], [], [], remaining)[0]:
                        raise TimeoutError('capability check timed out')
                    piece = os.read(client.stdout.fileno(), 4096)
                    if not piece:
                        status = client.wait(timeout=max(0, deadline - time.monotonic()))
                        if status:
                            raise TVCommandError(status)
                        return json.loads(output) if json_reply else output.decode('utf-8')
                    output.extend(piece)
                    if len(output) > 65536:
                        raise ValueError('oversized capability reply')
                    if json_reply:
                        try:
                            return json.loads(output)
                        except (ValueError, UnicodeDecodeError):
                            continue
            finally:
                if client.poll() is None:
                    client.kill()


def decision(reader):
    try:
        backend = home.verify(reader, CheckList(), {}, allow_c1=True, allow_compositor=True)
    except home.NoRootAlternativeError:
        return 'external_no_root' if reader.embedded_ruled_out else 'unconfirmed'
    except (home.RootCapabilityError, OSError, ValueError, subprocess.SubprocessError):
        return 'unconfirmed'
    if backend == 'system-profile':
        return 'root'
    return 'external_root' if backend == 'c1-native-gate' else 'unconfirmed'


if __name__ == '__main__':
    if len(sys.argv) != 1 or os.geteuid() != 0:
        raise SystemExit(1)
    print(json.dumps({'decision': decision(LocalReads())}))
