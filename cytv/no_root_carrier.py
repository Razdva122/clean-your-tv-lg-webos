"""Inert same-ID cleanup archives; never a reconstruction of product setup.

Inputs must be authenticated original/current packages. This validates their
layout, not their provenance or retail platform admission. The caller must bind
the carrier to its own removal intent and independently verify final service,
role, group and data absence after the explicit original remove stream.
"""
import io
import json
import re
import tarfile

from . import package

SERVICES = {
    'com.local.nativehome': frozenset(('com.local.nativehome.service',)),
    'com.gathin.tvhome': frozenset(('com.gathin.tvhome.renewal',)),
    'com.cleanyourtv.updater': frozenset(('com.cleanyourtv.updater.service',)),
}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')


def metadata(raw, app):
    """Validate all three package identities and the complete owned service set."""
    if app not in SERVICES or len(raw) > 128 * 1024 * 1024:
        raise ValueError('Unsupported cleanup package')
    members = package.read_ar(raw)
    if set(members) != {'debian-binary', 'control.tar.gz', 'data.tar.gz'} or members['debian-binary'] != b'2.0\n':
        raise ValueError('Unsupported cleanup archive')
    with tarfile.open(fileobj=io.BytesIO(members['control.tar.gz']), mode='r:gz') as archive:
        entries = archive.getmembers()
        if len(entries) != 1 or entries[0].name != 'control' or not entries[0].isfile() or entries[0].size > 8192:
            raise ValueError('Cleanup source contains control scripts')
        fields = {}
        for line in archive.extractfile(entries[0]).read().decode('ascii').splitlines():
            key, separator, value = line.partition(': ')
            if not separator or key in fields or key not in ('Package', 'Version', 'Architecture', 'Maintainer', 'Description'):
                raise ValueError('Unsupported cleanup control metadata')
            fields[key] = value
    version = fields.get('Version', '')
    architecture = fields.get('Architecture')
    if (fields.get('Package') != app or not re.fullmatch(r'[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}', version)
            or architecture != ('arm' if app == 'com.local.nativehome' else 'all')):
        raise ValueError('Cleanup identity, version or architecture is unverified')
    files = package.data_files(raw)
    try:
        info = json.loads(files['usr/palm/applications/' + app + '/appinfo.json'])
        manifest = json.loads(files['usr/palm/packages/' + app + '/packageinfo.json'])
        services = manifest['services']
        if (info['id'] != app or info['version'] != version or manifest['id'] != app
                or manifest['app'] != app or manifest['version'] != version or not isinstance(services, list)
                or any(not isinstance(item, str) for item in services) or len(set(services)) != len(services)
                or not set(services).issubset(SERVICES[app])):
            raise ValueError('Cleanup package identities disagree')
        for service in services:
            declaration = json.loads(files['usr/palm/services/' + service + '/services.json'])
            if declaration.get('id') != service or declaration.get('services') != [{'name': service}]:
                raise ValueError('Cleanup service identity is unverified')
        roots = ('usr/palm/applications/' + app + '/', 'usr/palm/packages/' + app + '/') + tuple(
            'usr/palm/services/' + service + '/' for service in services)
        if any(not name.startswith(roots) for name in files):
            raise ValueError('Cleanup source contains foreign files')
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Cleanup source metadata is incomplete') from error
    return {'id': app, 'version': version, 'architecture': architecture, 'services': services}


def build(app, originals, *, noop, architecture):
    """Preserve the union of known identities; use the LAST validated version.

    The caller supplies oldest-to-current authenticated evidence. A guessed high
    version, version-force flag or arbitrary discovered service is never used.
    noop is the independently built/hash-verified installer support executable.
    """
    if not originals or len(originals) > 8:
        raise ValueError('Cleanup source inventory is incomplete')
    evidence = [metadata(raw, app) for raw in originals]
    current = evidence[-1]
    if architecture != current['architecture'] or not isinstance(noop, bytes) or not noop.startswith(b'\x7fELF'):
        raise ValueError('Cleanup executable architecture is unverified')
    version = current['version']
    services = sorted({service for item in evidence for service in item['services']})
    base = 'usr/palm/applications/' + app + '/'
    native = app == 'com.local.nativehome'
    info = {'id': app, 'version': version, 'type': 'native' if native else 'web',
            'main': 'cleanup-noop' if native else 'index.html', 'title': 'Clean Your TV cleanup',
            'requiredACG': [], 'visible': False, 'noWindow': True, 'noSplashOnLaunch': True}
    files = {base + 'appinfo.json': _json(info),
             base + info['main']: noop if native else b'<!doctype html><html><head><title>Cleanup</title></head><body></body></html>\n',
             'usr/palm/packages/' + app + '/packageinfo.json': _json(
                 {'id': app, 'app': app, 'version': version, 'services': services})}
    for service in services:
        directory = 'usr/palm/services/' + service + '/'
        files[directory + 'services.json'] = _json({'id': service, 'services': [{'name': service}], 'requiredACG': []})
        files[directory + 'package.json'] = _json({'name': service, 'version': version, 'main': 'service.js'})
        files[directory + 'service.js'] = b"'use strict';process.exit(0);\n"
    return package.ipk(app, version, files, executable=(base + 'cleanup-noop',) if native else (),
                       architecture=architecture, shared_directories=True)
