"""Conservative, per-filesystem installation budgets; never remove user data."""
import io
import re
import shlex
import tarfile

from . import package
from .errors import UserError

RESERVE = 16 * 1024 * 1024
SUMMARY = 'Storage estimate ({location}): required {required} MiB; available {available} MiB; shortfall {shortfall} MiB.'
UNKNOWN = 'Storage estimate ({location}): required {required} MiB; available and shortfall could not be determined.'


def mib(value, up=True):
    units = (value * 10 + (1048575 if up else 0)) // 1048576
    return f'{units / 10:.1f}'


def unpacked(data):
    """Round archive entries to blocks; include directories and metadata reserve."""
    with tarfile.open(fileobj=io.BytesIO(package.read_ar(data)['data.tar.gz']), mode='r:gz') as archive:
        return sum(max(4096, (member.size + 4095) // 4096 * 4096) for member in archive)


def check(remote, requirements, progress):
    """Add requirements sharing a filesystem, rather than testing each in isolation."""
    groups = {}
    for location, required in requirements.items():
        try:
            reply = remote.run('LC_ALL=C df -Pk ' + shlex.quote(location))
        except (UserError, OSError):
            reply = ''
        rows = reply.strip().splitlines() if isinstance(reply, str) else []
        fields = rows[-1].split() if rows else []
        if len(fields) != 6 or not re.fullmatch(r'[0-9]{1,16}', fields[3]):
            progress(UNKNOWN.format(location=location, required=mib(required + RESERVE)))
            raise UserError('Available TV storage could not be determined. Installation stopped before package submission.')
        key = (fields[0], fields[5])
        group = groups.setdefault(key, {'location': location, 'required': RESERVE, 'available': int(fields[3]) * 1024})
        group['required'] += required
        group['available'] = min(group['available'], int(fields[3]) * 1024)
    failed = []
    for group in groups.values():
        needed, available = group['required'], group['available']
        message = SUMMARY.format(location=group['location'], required=mib(needed),
                                 available=mib(available, False), shortfall=mib(max(0, needed - available)))
        progress(message)
        if needed > available:
            failed.append(message)
    if failed:
        raise UserError('\n'.join(failed), reason_code='tv-storage-full')


def install(remote, bundles, progress, root=False):
    """Budget new bytes alongside existing installs, including staging and rollback copies.

    This is a conservative estimate, not a promise about appinstalld's private
    scratch files or the size of an existing device-specific backup.
    """
    staged = sum(len(data) for data in bundles.values())
    sizes = [unpacked(data) for name, data in bundles.items() if name.endswith('.ipk')]
    expanded = sum(sizes)
    if root:
        requirements = {'/tmp': staged + max(sizes, default=0),
                        '/var/lib': 2 * (staged + expanded),
                        '/media/developer/apps': 2 * expanded}
    else:
        requirements = {'/media/developer': staged + 2 * expanded,
                        '/tmp': max(sizes, default=0)}
    check(remote, requirements, progress)


def local(required, progress):
    import shutil
    import tempfile
    available = shutil.disk_usage(tempfile.gettempdir()).free
    message = SUMMARY.format(location='Computer temporary storage', required=mib(required),
                             available=mib(available, False), shortfall=mib(max(0, required-available)))
    progress(message)
    if required > available:
        raise UserError(message, reason_code='computer-storage-full')
