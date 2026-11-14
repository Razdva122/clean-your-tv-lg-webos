"""Observe only fixed CYTV markers before the manual Root Restore route."""
import json
import os
import stat
from pathlib import Path
import shlex

from .package import ROOT_APP

# Neither these markers nor a host receipt grant recovery authority.
# They only preserve the existing authenticated recovery path.
_ROOT_MARKERS = (
    '/var/lib/clean-your-tv-root',
    '/var/lib/clean-your-tv-installation',
    '/var/lib/webosbrew/init.d/50-clean-your-tv-root',
    '/var/webos-profile/override/clean-your-tv-root.json',
    '/var/luna-service2/manifests.d/' + ROOT_APP + '.recovery.json',
    *('/media/developer/apps/usr/palm/' + kind + '/' + ROOT_APP + suffix
      for kind, suffix in (('applications', ''), ('packages', ''), ('services', '.service'))),
    *('/var/luna-service2-dev/' + kind + '/' + ROOT_APP + '.service' + suffix
      for kind, suffix in (('services.d', '.service'), ('roles.d', '.service.json'),
                           ('client-permissions.d', '.service.json'), ('api-permissions.d', '.api.json'))),
)

# Use the TV's existing Node with the legacy-compatible lstat API. Absence
# requires ENOENT below real, reachable directories. Scan it twice to discard
# a changed ancestor or footprint; this is evidence, not a filesystem fence.
_FOOTPRINT_SCRIPT = r"""
var fs = require('fs'), paths = JSON.parse(process.argv[1]);
function absent(path) {
    var parts = path.split('/'), directory = '', identity = [];
    for (var i = 1; i < parts.length; i++) {
        directory += '/' + parts[i];
        var node;
        try {
            node = fs.lstatSync(directory);
        } catch (error) {
            if (error.code === 'ENOENT') return JSON.stringify([directory, identity]);
            throw error;
        }
        if (i === parts.length - 1) return null;
        if (!node.isDirectory()) throw Error('ancestor');
        identity.push([node.dev, node.ino]);
    }
}
try {
    var first = paths.map(absent), second = paths.map(absent);
    process.stdout.write(first.every(function (path, i) { return path && path === second[i]; })
                         ? 'CYTV_ROOT_FOOTPRINT_ABSENT' : 'CYTV_ROOT_FOOTPRINT_RETAINED');
} catch (_) {
    process.stdout.write('CYTV_ROOT_FOOTPRINT_UNCERTAIN');
}
"""
ROOT_RESTORE_FOOTPRINT = (
    "if test -x /usr/bin/node; then "
    + shlex.join(['env', '-u', 'NODE_OPTIONS', '-u', 'NODE_PATH', '/usr/bin/node',
                  '-e', _FOOTPRINT_SCRIPT, json.dumps(_ROOT_MARKERS)])
    + "; else printf CYTV_ROOT_FOOTPRINT_UNCERTAIN; fi"
)


def local_recovery_retained(directory: Path):
    for name in ('operation.json', 'installation.json', 'clean-removal.json'):
        try:
            (directory / name).lstat()
            return True
        except FileNotFoundError:
            pass
        except OSError:
            return True
    try:
        for receipt in directory.glob('recovery-*.json'):
            # Completion records from unrelated past requests are not current
            # recovery. Pending or unreadable receipts remain on the old path.
            if not stat.S_ISREG(receipt.lstat().st_mode):
                return True
            flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
            fd = os.open(receipt, flags)
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    return True
                value = json.loads(stream.read(4097))
            if not isinstance(value, dict) or value.get('action') == 'restore' and value.get('stage') != 'complete':
                return True
    except (ValueError, OSError):
        return True
    return False
