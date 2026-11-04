"""Run only in the disposable container documented in the #307 evidence record."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile

import package  # Current cytv/package.py copied into the isolated build context.


def records(raw):
    with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['data.tar.gz'])) as archive:
        return {entry.name: (entry.mode, entry.uid, entry.gid, entry.mtime,
                             entry.uname, entry.gname, entry.type) for entry in archive}


def main():
    original = Path('/lab/original.ipk').read_bytes()
    assert hashlib.sha256(original).hexdigest() == '0e8477113fd8afc57b5f3bfc7271a3b7de99dcce2fb2516d7e386eff06ec00cf'
    expected = package.data_files(original)
    assert len(expected) == 72
    parts = package.read_ar(original)
    original_tar = gzip.decompress(parts['data.tar.gz'])
    # A single-factor control: prepend one header without rewriting any old record.
    entry = tarfile.TarInfo('usr/palm/services')
    entry.type, entry.mode, entry.mtime = tarfile.DIRTYPE, 0o755, package.IPK_MTIME
    header = entry.tobuf(format=tarfile.USTAR_FORMAT)
    control_parts = dict(parts, **{'data.tar.gz': gzip.compress(header + original_tar, mtime=0)})
    assert gzip.decompress(control_parts['data.tar.gz'])[512:] == original_tar
    single = package.ar(control_parts)
    executable = {name for name, meta in records(original).items() if meta[-1] == tarfile.REGTYPE and meta[0] & 0o111}
    corrected = package.ipk('com.local.nativehome', '0.6.22', expected, executable,
                            helper_state=True, architecture='arm', shared_directories=True)
    assert package.data_files(corrected) == expected
    assert package.read_ar(corrected)['control.tar.gz'] == parts['control.tar.gz']
    for name, meta in records(original).items():
        assert records(corrected)[name] == meta, name
    corrected_records = records(corrected)
    assert len(corrected_records) == 87
    for name in ('usr', 'usr/palm', 'usr/palm/applications', 'usr/palm/services', 'usr/palm/packages'):
        assert corrected_records[name][:3] == (0o755, 0, 0)

    variants = {'original': original, 'services-only': single, 'corrected': corrected}
    observed = []
    for layout in ('missing-services', 'all-exist', 'empty'):
        for variant, raw in variants.items():
            with tempfile.TemporaryDirectory(prefix='opkg307-') as tmp:
                base = Path(tmp); root = base/'root'; root.mkdir()
                parents = [] if layout == 'empty' else ['applications', 'packages']
                if layout == 'all-exist': parents.append('services')
                for name in parents:
                    (root/'usr/palm'/name).mkdir(parents=True, exist_ok=True)
                ipk = base/'package.ipk'; ipk.write_bytes(raw)
                result = subprocess.run(['opkg018-extract', str(ipk), str(root)+'/'],
                                        capture_output=True, text=True, timeout=30)
                actual = {name: (root/name).read_bytes() for name in expected if (root/name).is_file()}
                assert all(actual[name] == expected[name] for name in actual)
                count = 72 if variant == 'corrected' or layout == 'all-exist' else (
                    0 if layout == 'empty' else 72 if variant == 'services-only' else 61)
                assert len(actual) == count, (layout, variant, result.returncode, len(actual))
                if variant == 'corrected':
                    assert result.returncode == 0 and not result.stdout and not result.stderr
                    for name, meta in corrected_records.items():
                        info = (root/name).stat()
                        assert (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid) == meta[:3], name
                item = {'layout': layout, 'variant': variant, 'exit': result.returncode,
                        'files': len(actual), 'service_files': sum(name.startswith('usr/palm/services/') for name in actual)}
                observed.append(item)
                print(json.dumps(item), flush=True)
    assert len(observed) == 9
    print('PASS: real opkg extraction, bytes, existing metadata and corrected directory attributes')


if __name__ == '__main__':
    main()
