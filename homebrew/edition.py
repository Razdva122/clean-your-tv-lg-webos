"""Read-only Root Home admission for a fresh Homebrew installation."""
import json
import os
import re
import select
import subprocess
import sys
import time

from cytv import root_capabilities as home
from cytv.checks import CheckList
from cytv.errors import TVCommandError


SYSTEM_INFO = 'com.webos.service.tv.systemproperty/getSystemInfo'
SYSTEM_INFO_KEYS = ('modelName', 'firmwareVersion', 'sdkVersion')
MODEL = re.compile(r'(?=.*[0-9])(?=.*[A-Z])[A-Z0-9][A-Z0-9._-]{1,47}')
VERSION = re.compile(r'[0-9]{1,5}(?:\.[0-9]{1,5}){1,2}(?:-[0-9]{1,6})?')


class LocalReads:
    """Run only the desktop classifier's fixed queries on this TV."""

    def __init__(self):
        self.embedded_ruled_out = False
        self.system_info_queried = False
        self.tv = {}

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
            SYSTEM_INFO: {'keys': list(SYSTEM_INFO_KEYS)},
            'com.webos.service.config/getConfigs': {
                'configNames': ['com.webos.surfacemanager.keyFilters']},
            'com.webos.surfacemanager.home/getCurrentHomeUIState': {},
        })
        if uri not in allowed or payload != allowed[uri]:
            raise ValueError('unknown capability query')
        if uri == SYSTEM_INFO:
            self.system_info_queried = True
        reply = self._read(['/usr/bin/luna-send', '-n', '1', 'luna://' + uri,
                            json.dumps(payload)], timeout, json_reply=True)
        if uri == SYSTEM_INFO and isinstance(reply, dict) and reply.get('returnValue') is True:
            for key in SYSTEM_INFO_KEYS:
                value = reply.get(key)
                pattern = MODEL if key == 'modelName' else VERSION
                if isinstance(value, str) and pattern.fullmatch(value):
                    self.tv[key] = value
        return reply

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


def inspect_edition(reader, *, metadata_only=False):
    backend = None if metadata_only else decision(reader)
    # The profile backend may never need system info for admission. Collect
    # the allowlisted metadata at most once with a short, optional read.
    if not reader.system_info_queried:
        try:
            reader.luna(SYSTEM_INFO, {'keys': list(SYSTEM_INFO_KEYS)}, timeout=2)
        except (TVCommandError, OSError, ValueError, subprocess.SubprocessError):
            pass
    return {'decision': backend, 'tv': reader.tv}


if __name__ == '__main__':
    options = sys.argv[1:]
    if options not in ([], ['--metadata-only']) or os.geteuid() != 0:
        raise SystemExit(1)
    print(json.dumps(inspect_edition(LocalReads(), metadata_only=bool(options))))
