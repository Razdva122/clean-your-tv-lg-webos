"""Conservative, per-filesystem installation budgets; never remove user data."""
import io
import re
import shlex
import tarfile

from . import package
from .errors import TV_STORAGE_RAMFS, UserError

RESERVE = 16 * 1024 * 1024
RAMFS_MAGIC = '858458f6'  # Linux statfs filesystem type.
SUMMARY = 'Storage estimate ({location}): required {required} MiB; available {available} MiB; shortfall {shortfall} MiB.'
UNKNOWN = 'Storage estimate ({location}): required {required} MiB; available and shortfall could not be determined.'


def mib(value, up=True):
    units = (value * 10 + (1048575 if up else 0)) // 1048576
    return f'{units / 10:.1f}'


def unpacked(data):
    """Round archive entries to blocks; include directories and metadata reserve."""
    with tarfile.open(fileobj=io.BytesIO(package.read_ar(data)['data.tar.gz']), mode='r:gz') as archive:
        return sum(max(4096, (member.size + 4095) // 4096 * 4096) for member in archive)


def _tmp_is_ramfs(remote):
    try:
        filesystem = remote.run("LC_ALL=C stat -f -c '%t' /tmp", timeout=5)
    except (UserError, OSError):
        return False
    return isinstance(filesystem, str) and filesystem.strip().lower() == RAMFS_MAGIC


def check(remote, requirements, progress, *, allow_tmp_ramfs=False):
    """Add requirements sharing a filesystem, rather than testing each in isolation."""
    groups = {}
    ramfs_tmp = False
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
        if (location == fields[5] == '/tmp' and fields[1:4] == ['0', '0', '0']
                and _tmp_is_ramfs(remote)):
            ramfs_tmp = True
            if allow_tmp_ramfs:
                progress(TV_STORAGE_RAMFS)
            else:
                progress(UNKNOWN.format(location=location, required=mib(required + RESERVE)))
            continue
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
    if ramfs_tmp and not allow_tmp_ramfs:
        raise UserError(TV_STORAGE_RAMFS + ' Installation stopped before package submission.',
                        reason_code='tv-storage-ramfs')
    return ramfs_tmp


def install(remote, bundles, progress, root=False, *, no_root_root_ssh=False):
    """Budget new bytes alongside existing installs, including staging and rollback copies.

    This is a conservative estimate, not a promise about appinstalld's private
    scratch files or the size of an existing device-specific backup.
    """
    staged = sum(len(data) for data in bundles.values())
    sizes = [unpacked(data) for name, data in bundles.items() if name.endswith('.ipk')]
    expanded = sum(sizes)
    root = root or no_root_root_ssh
    if root:
        requirements = {'/tmp': staged + max(sizes, default=0),
                        '/var/lib': 2 * (staged + expanded),
                        '/media/developer/apps': 2 * expanded}
    else:
        requirements = {'/media/developer': staged + 2 * expanded,
                        '/tmp': max(sizes, default=0)}
    # Both No-root connections expand apps under /media/developer/apps. Root
    # SSH stages the IPKs on /var/lib. Vendor scratch on ramfs is unmeasurable.
    return check(remote, requirements, progress, allow_tmp_ramfs=not root or no_root_root_ssh)


def local(required, progress):
    import shutil
    import tempfile
    available = shutil.disk_usage(tempfile.gettempdir()).free
    message = SUMMARY.format(location='Computer temporary storage', required=mib(required),
                             available=mib(available, False), shortfall=mib(max(0, required-available)))
    progress(message)
    if required > available:
        raise UserError(message, reason_code='computer-storage-full')
