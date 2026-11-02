#!/usr/bin/env python3
"""Prepare signed OTA assets from published/draft bundles; never execute bundle code."""
import argparse
import base64
import hashlib
import gzip
import io
import json
import runpy
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cytv.package import ar, data_files, read_ar, safe_name

REPO = 'Razdva122/clean-your-tv-lg-webos'
URL = 'https://github.com/' + REPO + '/releases/download/'
APPS = {'home': 'com.gathin.tvhome', 'root': 'com.cleanyourtv.root.preview', 'helper': 'com.local.nativehome'}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', value):
        raise ValueError('Invalid component version')
    return tuple(map(int, value.split('.')))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_versions(versions):
    for key in ('cytv', 'home', 'helper', 'root', 'updater'):
        version(versions[key])
    if 'release' in versions:
        version(versions['release'])
    if 'android' in versions or 'android_version_code' in versions:
        if (not isinstance(versions.get('android'), str)
                or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}(?:-preview)?', versions['android'])
                or type(versions.get('android_version_code')) is not int
                or versions['android_version_code'] < 1):
            raise ValueError('Invalid Android version metadata')


def package_version(raw, kind, expected):
    app = APPS[kind]
    info = json.loads(data_files(raw)['usr/palm/applications/' + app + '/appinfo.json'])
    if info.get('id') != app or info.get('version') != expected:
        raise ValueError(kind + ' package version differs from release metadata')
    version(expected)


def helper_archive_digest(raw):
    """Pin all archive bytes and metadata independently of gzip implementation headers."""
    return digest(ar({
        name: gzip.decompress(data) if name.endswith('.tar.gz') else data
        for name, data in read_ar(raw).items()}))


def verify_helper_transition(current, prior, packages, prior_packages, compatibility):
    """Require either an exact tested runtime pin or the narrow permission repair."""
    expected = {'from_helper':prior['helper'], 'to_helper':current['helper'],
                'rollback_home':prior['home'], 'rollback_sha256':digest(prior_packages['home']),
                'prior_helper_sha256':digest(prior_packages['helper'])}
    if not isinstance(compatibility, dict) or any(compatibility.get(k) != v for k, v in expected.items()):
        raise ValueError('Helper rollback compatibility approval mismatch')
    if version(current['home']) <= version(prior['home']):
        raise ValueError('Helper rollback compatibility requires a new Home candidate')
    if 'candidate_archive_sha256' in compatibility:
        acceptance = compatibility.get('acceptance')
        if (not isinstance(acceptance, str) or not acceptance.strip()
                or helper_archive_digest(packages['helper']) != compatibility['candidate_archive_sha256']):
            raise ValueError('Helper rollback compatibility tested archive mismatch')
        return
    def layout(raw):
        parts = read_ar(raw)
        if set(parts) != {'debian-binary', 'control.tar.gz', 'data.tar.gz'} or parts['debian-binary'] != b'2.0\n':
            raise ValueError('Helper rollback compatibility archive changed')
        result = {}
        for name in ('control.tar.gz', 'data.tar.gz'):
            entries, contents = {}, {}
            with tarfile.open(fileobj=io.BytesIO(parts[name]), mode='r:gz') as archive:
                for member in archive:
                    safe_name(member.name)
                    if member.name in entries or not (member.isfile() or member.isdir()) or member.pax_headers or member.size > 16*1024*1024:
                        raise ValueError('Helper rollback compatibility archive entry invalid')
                    entries[member.name] = (member.type, member.mode, member.uid, member.gid,
                                           member.uname, member.gname, member.linkname, member.mtime)
                    if member.isfile(): contents[member.name] = archive.extractfile(member).read()
            result[name] = entries, contents
        return result
    old_layout, new_layout = (layout(p['helper']) for p in (prior_packages, packages))
    for name in old_layout:
        if old_layout[name][0] != new_layout[name][0]:
            raise ValueError('Helper rollback compatibility archive permissions or entries changed')
    old_control, new_control = old_layout['control.tar.gz'][1], new_layout['control.tar.gz'][1]
    old_version = ('\nVersion: '+prior['helper']+'\n').encode()
    if (set(old_control) != {'control'} or set(new_control) != {'control'} or
            old_control['control'].count(old_version) != 1 or
            old_control['control'].replace(old_version, ('\nVersion: '+current['helper']+'\n').encode()) != new_control['control']):
        raise ValueError('Helper rollback compatibility installation control changed')
    before, after = (data_files(p['helper']) for p in (prior_packages, packages))
    base = 'usr/palm/applications/' + APPS['helper'] + '/'
    repair = base + 'state-permissions.js'
    if repair not in after or digest(after[repair]) != compatibility.get('state_permissions_sha256'):
        raise ValueError('Helper rollback compatibility repair hash mismatch')
    metadata = {base+'appinfo.json', 'usr/palm/services/com.local.nativehome.service/package.json',
                'usr/palm/packages/com.local.nativehome/packageinfo.json'}
    names = {n for n in before if not n.endswith('.png')}
    if names != {n for n in after if not n.endswith('.png')}:
        raise ValueError('Helper rollback compatibility file set changed')
    for name in names - {repair}:
        if name in metadata:
            old, new = json.loads(before[name]), json.loads(after[name])
            if name == base+'appinfo.json':
                for info in (old, new):
                    if not re.fullmatch(r'#[a-fA-F0-9]{6}', info.pop('iconColor', '')):
                        raise ValueError('Helper rollback compatibility icon metadata invalid')
            if old.pop('version', None) != prior['helper'] or new.pop('version', None) != current['helper'] or old != new:
                raise ValueError('Helper rollback compatibility metadata changed')
        elif before[name] != after[name]:
            raise ValueError('Helper rollback compatibility runtime changed: ' + name)


def prepare_manifests(tag, build, packages, prior_build, prior_packages, rollback=None, notes=None, compatibility=None, rollback_hd=None):
    if not re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}', tag) or build['tag'] != tag:
        raise ValueError('Invalid release tag')
    current, prior = build['versions'], prior_build['versions']
    for kind in APPS:
        package_version(packages[kind], kind, current[kind])
        package_version(prior_packages[kind], kind, prior[kind])
        if version(current[kind]) < version(prior[kind]):
            raise ValueError(kind + ' version regression')
    for kind in APPS:
        if current[kind] == prior[kind] and packages[kind] != prior_packages[kind]:
            raise ValueError(kind + ' package changed without version bump')
    if current['helper'] != prior['helper']:
        if compatibility is None:
            raise ValueError('Helper baseline changed; a compatible tested rollback baseline is required')
        verify_helper_transition(current, prior, packages, prior_packages, compatibility)
    if current['home'] == prior['home']:
        if rollback is None:
            raise ValueError('Existing signed rollback required for unchanged Home version')
        prior_home, previous_bytes = rollback
        previous_version = prior_home['home']
        if prior_home['helper'] != current['helper']:
            raise ValueError('Helper baseline mismatch in rollback')
    else:
        previous_version, previous_bytes = prior['home'], prior_packages['home']
    package_version(previous_bytes, 'home', previous_version)
    if version(previous_version) < version('1.2.0'):
        raise ValueError('Rollback predates supported Home profile recovery')
    if version(previous_version) >= version(current['home']):
        raise ValueError('Rollback must be older than Home candidate')
    files = {}
    def home_manifest(v, raw, notes):
        name = APPS['home'] + '_' + v + '_all.ipk'
        files[name] = raw
        return {'schema': 1, 'release': tag, 'home': v, 'helper': current['helper'], 'url': URL + tag + '/' + name, 'sha256': digest(raw), 'notes': notes}
    notes = (notes or ('See the ' + tag + ' release notes for changes.')).strip()[:3800]
    home = home_manifest(current['home'], packages['home'], notes)
    previous = home_manifest(previous_version, previous_bytes, 'Previous published Home ' + previous_version + ' for rollback.')
    name = APPS['root'] + '_' + current['root'] + '_all.ipk'
    raw = packages['root']; files[name] = raw
    root = {'schema': 1, 'edition': 'root', 'application': APPS['root'], 'release': tag, 'version': current['root'], 'runtime': 1, 'updater': 1, 'profile': 1, 'url': URL + tag + '/' + name, 'sha256': digest(raw), 'size': len(raw), 'notes': notes}
    manifests={'root': root, 'home': home, 'previous': previous}
    hd={kind:packages[kind+'-720p'] for kind in ('home','root') if kind+'-720p' in packages}
    if hd:
        if set(hd)!={'home','root'}:raise ValueError('Both HD package variants required')
        for kind in ('home','root'):
            info=json.loads(data_files(packages[kind])['usr/palm/applications/'+APPS[kind]+'/appinfo.json'])
            if info.get('resolution')!='1920x1080':raise ValueError('FHD package resolution mismatch')
        for kind,raw in hd.items():
            package_version(raw,kind,current[kind])
            info=json.loads(data_files(raw)['usr/palm/applications/'+APPS[kind]+'/appinfo.json'])
            if info.get('resolution')!='1280x720':raise ValueError('HD package resolution mismatch')
            old=prior_packages.get(kind+'-720p')
            if old is not None:
                package_version(old,kind,prior[kind])
                old_info=json.loads(data_files(old)['usr/palm/applications/'+APPS[kind]+'/appinfo.json'])
                if old_info.get('resolution')!='1280x720':raise ValueError('Prior HD package resolution mismatch')
            if old is None and version(current[kind])<=version(prior[kind]):raise ValueError('First HD release requires new Home and Root component versions')
            if old is not None and current[kind]==prior[kind] and raw!=old:raise ValueError(kind+' HD package changed without version bump')
            name=APPS[kind]+'_'+current[kind]+'_720p_all.ipk';files[name]=raw
        manifests['root-720p']={**root,'url':URL+tag+'/'+APPS['root']+'_'+current['root']+'_720p_all.ipk','sha256':digest(hd['root']),'size':len(hd['root'])}
        # Preserve an established signed channel on Root/installer-only releases.
        old=prior_packages.get('home-720p');old_version=prior['home']
        if current['home']==prior['home']:
            if rollback_hd is None:
                if prior_build.get('no_root_ota_720p') is not None:raise ValueError('Existing signed HD Home rollback required')
                old=None
            else:
                descriptor,old=rollback_hd;old_version=descriptor['home']
                if descriptor['helper']!=current['helper'] or digest(old)!=descriptor['sha256']:raise ValueError('HD rollback helper/digest mismatch')
        if old is not None and current['helper']==prior['helper']:
            package_version(old,'home',old_version)
            info=json.loads(data_files(old)['usr/palm/applications/'+APPS['home']+'/appinfo.json'])
            if info.get('resolution')!='1280x720':raise ValueError('HD rollback resolution mismatch')
            if not version('1.2.0')<=version(old_version)<version(current['home']):raise ValueError('HD rollback version incompatible')
            name=APPS['home']+'_'+old_version+'_720p_all.ipk';files[name]=old
            manifests['home-720p']={**home,'url':URL+tag+'/'+APPS['home']+'_'+current['home']+'_720p_all.ipk','sha256':digest(hd['home'])}
            manifests['previous-720p']={**previous,'home':old_version,'url':URL+tag+'/'+name,'sha256':digest(old)}
    return manifests, files


def verify_system_assets(manifests,build,files):
    expected={'root':{'root','root-updater','root-infrastructure'},'no-root':{'home','helper','updater'}}
    apps={**APPS,'updater':'com.cleanyourtv.updater','root-updater':'com.cleanyourtv.root.updater'}
    if set(manifests) not in (set(expected),set(expected)|{'root-720p','no-root-720p'}):raise ValueError('Both system release sets required')
    for key,manifest in manifests.items():
        edition=key.removesuffix('-720p');names=expected[edition]
        graphics='1280x720' if key.endswith('-720p') else '1920x1080'
        if edition=='root' and manifest.get('minimumSupervisorVersion')!='1.1.1':raise ValueError('Root minimum supervisor 1.1.1 required')
        if edition=='no-root' and 'minimumSupervisorVersion' in manifest:raise ValueError('Unexpected No-root minimum supervisor')
        if manifest.get('edition')!=edition or manifest.get('release')!=build['tag'] or manifest.get('schema')!=1 or manifest.get('supervisor')!=1 or {c['name'] for c in manifest['components']}!=names or len(manifest['components'])!=len(names):raise ValueError('Invalid system release set')
        for item in manifest['components']:
            filename=item['url'].rsplit('/',1)[1]
            if item['url']!=URL+build['tag']+'/'+filename or not re.fullmatch(r'[A-Za-z0-9._-]+',filename):raise ValueError('Invalid system release asset')
            raw=files[filename]
            if digest(raw)!=item['sha256'] or len(raw)!=item['size']:raise ValueError('System release asset hash mismatch')
            key={'root-infrastructure':'root','root-updater':'updater'}.get(item['name'],item['name'])
            if not isinstance(build['versions'].get(key),str) or item['version']!=build['versions'][key]:raise ValueError('System component version mismatch')
            if item['name']!='root-infrastructure':
                app=apps[item['name']]
                if item.get('application')!=app or item.get('kind')!='ipk':raise ValueError('System component identity mismatch')
                info=json.loads(data_files(raw)['usr/palm/applications/'+app+'/appinfo.json'])
                if info.get('id')!=app or info.get('version')!=item['version']:raise ValueError('System package version mismatch')
                if item['name'] in ('home','root'):
                    suffix='_720p_all.ipk' if graphics=='1280x720' else '_all.ipk'
                    if filename!=app+'_'+item['version']+suffix or info.get('resolution','1920x1080')!=graphics:raise ValueError('System package resolution mismatch')
            else:
                if item.get('kind')!='infrastructure':raise ValueError('Invalid system infrastructure')
                with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
                    seen=set()
                    for member in archive:
                        safe_name(member.name)
                        allowed = member.name.startswith(('runtime/','updater/','service/')) or member.name in ('support/python_binding.py','support/python_boot.js','support/package_data.py','support/package_identity.py','support/updater/store.py','support/updater/package.py','support/startup_guard.py')
                        if not member.isfile() or not allowed or member.name in seen or member.size>32*1024*1024:raise ValueError('Invalid system infrastructure inventory')
                        seen.add(member.name)
                    if not seen:raise ValueError('Empty system infrastructure')
    return manifests


def gh(*args):
    return subprocess.check_output(['gh', *args], stderr=subprocess.PIPE)


def release_metadata(tag):
    # Drafts are absent from the tags endpoint. gh resolves them through the list API.
    info = json.loads(gh('release', 'view', tag, '--repo', REPO, '--json', 'databaseId'))
    return json.loads(gh('api', 'repos/' + REPO + '/releases/' + str(info['databaseId'])))


def download(meta, name, folder):
    asset = next(a for a in meta['assets'] if a['name'] == name)
    gh('release', 'download', meta['tag_name'], '--repo', REPO, '--pattern', name, '--dir', str(folder))
    raw = (folder / name).read_bytes()
    if asset.get('digest') != 'sha256:' + digest(raw) or asset['size'] != len(raw):
        raise ValueError('GitHub asset digest mismatch: ' + name)
    return raw


def verify_homebrew_approval(build, committed):
    if build.get('homebrew') is not None and build['homebrew'] != committed:
        raise ValueError('Homebrew approval differs from committed source')


def verify_homebrew_source(build, commit):
    # GitHub reads the immutable source blob, including on shallow workflow checkouts.
    content=json.loads(gh('api', 'repos/' + REPO + '/contents/homebrew/release.json?ref=' + commit))
    verify_homebrew_approval(build, json.loads(base64.b64decode(content['content'])))


def bundles(meta, folder):
    folder.mkdir()
    build = json.loads(download(meta, 'BUILD-INFO.json', folder))
    if build['tag'] != meta['tag_name'] or not re.fullmatch('[a-f0-9]{40}', build['source_commit']):
        raise ValueError('Invalid release provenance')
    commit = json.loads(gh('api', 'repos/' + REPO + '/commits/' + meta['target_commitish']))['sha']
    if commit != build['source_commit']:
        raise ValueError('Release source commit mismatch')
    content = json.loads(gh('api', 'repos/' + REPO + '/contents/release-versions.json?ref=' + commit))
    if json.loads(base64.b64decode(content['content'])) != build['versions']:
        raise ValueError('Release versions differ from committed source')
    if build.get('homebrew') is not None:
        verify_homebrew_source(build, commit)
    versions = build['versions']
    validate_versions(versions)
    home_name = 'clean-your-tv-no-root-' + versions['home'] + '.zip'
    download(meta, home_name, folder)
    with zipfile.ZipFile(folder / home_name) as archive:
        home = archive.read(APPS['home'] + '_' + versions['home'] + '_all.ipk')
        hd_name=APPS['home']+'_'+versions['home']+'_720p_all.ipk'
        home_hd=archive.read(hd_name) if hd_name in archive.namelist() else None
        helper = archive.read(APPS['helper'] + '_' + versions['helper'] + '_arm.ipk')
    root_name = 'clean-your-tv-root-' + versions['root'] + '.tar.gz'
    download(meta, root_name, folder)
    suffix = '/build/root-candidate/' + APPS['root'] + '_' + versions['root'] + '_all.ipk'
    with tarfile.open(folder / root_name) as archive:
        members = [m for m in archive if m.name.endswith(suffix) and m.isfile() and m.size <= 32 * 1024 * 1024]
        if len(members) != 1: raise ValueError('Missing or ambiguous Root package')
        root = archive.extractfile(members[0]).read()
        hd_suffix=suffix.replace('/root-candidate/','/root-candidate-720p/')
        hd_members=[m for m in archive if m.name.endswith(hd_suffix) and m.isfile() and m.size<=32*1024*1024]
        if len(hd_members)>1:raise ValueError('Ambiguous HD Root package')
        root_hd=archive.extractfile(hd_members[0]).read() if hd_members else None
    packages={'home':home,'helper':helper,'root':root}
    if home_hd is not None:packages['home-720p']=home_hd
    if root_hd is not None:packages['root-720p']=root_hd
    return build,packages


def verified_hd_home_rollback(meta, folder, versions, candidate_bytes):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    channel=download(meta,'update-720p.json',folder)
    previous=download(meta,'previous-update-720p.json',folder)
    envelope=json.loads(channel)
    if envelope.get('previous')!=json.loads(previous):raise ValueError('HD rollback feed mismatch')
    code="const fs=require('fs'),p=require('./updater-service/policy'),e=JSON.parse(fs.readFileSync(process.argv[1])),key=fs.readFileSync('updater-service/release-public.pem');process.stdout.write(JSON.stringify({candidate:p.verify(e,key),previous:p.verify(e.previous,key)}));"
    checked=json.loads(subprocess.check_output(['node','-e',code,str(folder/'update-720p.json')],cwd=ROOT,stderr=subprocess.PIPE))
    candidate,prior=checked['candidate'],checked['previous']
    if candidate['home']!=versions['home'] or candidate['helper']!=versions['helper'] or digest(candidate_bytes)!=candidate['sha256']:raise ValueError('HD published candidate mismatch')
    for item in (candidate,prior):
        name=APPS['home']+'_'+item['home']+'_720p_all.ipk'
        if item['url']!=URL+item['release']+'/'+name:raise ValueError('HD published package URL mismatch')
        location=folder/item['home'];location.mkdir(exist_ok=True)
        origin=release_metadata(item['release'])
        if origin.get('draft') is not False or origin.get('prerelease') is not False:raise ValueError('HD rollback origin is not a published stable release')
        raw=download(origin,name,location)
        if digest(raw)!=item['sha256']:raise ValueError('HD published package digest mismatch')
        package_version(raw,'home',item['home'])
        info=json.loads(data_files(raw)['usr/palm/applications/'+APPS['home']+'/appinfo.json'])
        if info.get('resolution')!='1280x720':raise ValueError('HD published package resolution mismatch')
        if item is candidate and raw!=candidate_bytes:raise ValueError('HD published candidate bytes mismatch')
        if item is prior:rollback=(prior,raw)
    if prior['helper']!=candidate['helper'] or not version('1.2.0')<=version(prior['home'])<version(candidate['home']):raise ValueError('HD published rollback incompatible')
    return rollback


def prepare_homebrew(build, prior_build, current_download, prior_download):
    """Keep latest/download stable, preserving the accepted original immutable URL."""
    gate=runpy.run_path(str(ROOT/'scripts/homebrew-manifest.py'))
    current=build.get('homebrew'); prior=prior_build.get('homebrew')
    if current is None and prior is None: return {}
    approval=current if current is not None else prior
    fetch=current_download if current is not None else prior_download
    metadata=fetch(gate['MANIFEST_NAME'])
    value=json.loads(metadata);name=value['ipkUrl'].rsplit('/',1)[1]
    safe_name(name)
    raw=fetch(name)
    gate['verify_accepted'](raw,metadata,approval)
    if current is not None and prior is not None:
        new=version(current['version']);old=version(prior['version'])
        if new<old or (new==old and current!=prior):raise ValueError('Homebrew version regression or unversioned change')
    build['homebrew']=approval
    # Carried installer payload versions remain independent of this product release.
    return {gate['MANIFEST_NAME']:metadata,name:raw}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}', args.tag): raise ValueError('Invalid release tag')
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    meta = release_metadata(args.tag)
    if meta['prerelease']: raise ValueError('Stable feed cannot use a prerelease')
    releases = json.loads(gh('release', 'list', '--repo', REPO, '--limit', '100', '--json', 'tagName,isDraft,isPrerelease'))
    tags = [r['tagName'] for r in releases if not r['isDraft'] and not r['isPrerelease'] and re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}', r['tagName']) and version(r['tagName'][1:]) < version(args.tag[1:])]
    if not tags: raise ValueError('Previous stable release required')
    stable_tags = [r['tagName'] for r in releases if not r['isDraft'] and not r['isPrerelease'] and re.fullmatch(r'v\d{1,4}\.\d{1,4}\.\d{1,4}', r['tagName'])]
    if any(version(t[1:]) > version(args.tag[1:]) for t in stable_tags):
        raise ValueError('A newer stable release already exists; refusing to move latest backwards')
    previous_tag = max(tags, key=lambda t: version(t[1:]))
    prior_meta = release_metadata(previous_tag)
    with tempfile.TemporaryDirectory(prefix='cytv-release-') as tmp:
        tmp = Path(tmp)
        build, packages = bundles(meta, tmp / 'current')
        graphics={'1920x1080':{'launcher':'launcher.ipk','root':'root'},'1280x720':{'launcher':'launcher-720p.ipk','root':'root-720p'}}
        if build.get('graphics')!=graphics or not {'home-720p','root-720p'}<=packages.keys():raise ValueError('Both graphics release bundles and metadata required')
        prior_build, prior_packages = bundles(prior_meta, tmp / 'previous')
        rollback = None
        if build['versions']['home'] == prior_build['versions']['home']:
            raw = download(prior_meta, 'previous-update.json', tmp / 'previous')
            envelope_file = tmp / 'previous/previous-update.json'
            code = "const fs=require('fs'),p=require('./updater-service/policy');process.stdout.write(JSON.stringify(p.verify(JSON.parse(fs.readFileSync(process.argv[1])),fs.readFileSync('updater-service/release-public.pem'))));"
            prior = json.loads(subprocess.check_output(['node', '-e', code, str(envelope_file)], cwd=ROOT))
            rollback_meta = release_metadata(prior['release'])
            rollback_dir = tmp / 'rollback'; rollback_dir.mkdir()
            raw = download(rollback_meta, Path(prior['url']).name, rollback_dir)
            if digest(raw) != prior['sha256']: raise ValueError('Signed rollback digest mismatch')
            rollback = prior, raw
        rollback_hd=None
        if build['versions']['home']==prior_build['versions']['home'] and prior_build.get('no_root_ota_720p') is not None:
            rollback_hd=verified_hd_home_rollback(prior_meta,tmp/'hd-rollback',prior_build['versions'],prior_packages['home-720p'])
        approval_path = ROOT / 'native/helper-rollback-compatibility.json'
        compatibility = json.loads(approval_path.read_text()) if approval_path.exists() else None
        manifests, files = prepare_manifests(args.tag, build, packages, prior_build, prior_packages, rollback, meta.get('body'), compatibility, rollback_hd=rollback_hd)
        system = json.loads(download(meta, 'system-manifests.json', tmp / 'current'))
        system_files = {}
        (tmp / 'system-assets').mkdir()
        for manifest in system.values():
            for item in manifest['components']:
                name = item['url'].rsplit('/', 1)[1]
                if name not in system_files:
                    system_files[name] = download(meta, name, tmp / 'system-assets')
        if 'home-720p' in packages and set(system)!={'root','no-root','root-720p','no-root-720p'}:raise ValueError('Both graphics system release sets required')
        manifests['graphics']=graphics
        manifests['system'] = verify_system_assets(system, build, system_files)
        for variant,manifest in system.items():
            for item in manifest['components']:
                kind=item['name']+('-720p' if variant.endswith('-720p') and item['name'] in ('home','root') else '')
                if kind in packages and system_files[item['url'].rsplit('/',1)[1]]!=packages[kind]:raise ValueError('System release package differs from exact bundle: '+kind)
        files.update(system_files)
        files.update(prepare_homebrew(build, prior_build,
            lambda name: download(meta, name, tmp/'current'),
            lambda name: download(prior_meta, name, tmp/'previous')))
        manifest_file = tmp / 'manifests.json'; manifest_file.write_text(json.dumps(manifests))
        for name, raw in files.items(): (output / name).write_bytes(raw)
        subprocess.run(['node', str(ROOT / 'scripts/sign-release-feeds.cjs'), str(manifest_file), str(output)], check=True)
    build['feed_signing'] = {'workflow_run': os.environ.get('GITHUB_RUN_ID'), 'workflow_commit': os.environ.get('GITHUB_SHA')}
    build['automatic_update_feeds'] = 'Legacy and both edition system feeds generated and signed by GitHub Actions from exact release bundles; versions, signatures, packages and rollback verified before publication.'
    root, home, prior = manifests['root'], manifests['home'], manifests['previous']
    build['system_ota'] = {edition: {'release': args.tag, 'components': manifest['components'], 'feed_sha256': digest((output / ('system-update-'+edition+'.json')).read_bytes())} for edition, manifest in manifests['system'].items()}
    build['root_ota'] = {'version': root['version'], 'release': args.tag, 'ipk': Path(root['url']).name, 'sha256': root['sha256'], 'feed_sha256': digest((output / 'root-update.json').read_bytes())}
    build['no_root_ota'] = {'version': home['home'], 'helper': home['helper'], 'sha256': home['sha256'], 'previous_version': prior['home'], 'previous_sha256': prior['sha256']}
    build['no_root_ota_720p']=None
    if 'home-720p' in manifests:
        home_hd,prior_hd=manifests['home-720p'],manifests['previous-720p']
        build['no_root_ota_720p']={'version':home_hd['home'],'helper':home_hd['helper'],'sha256':home_hd['sha256'],'previous_version':prior_hd['home'],'previous_sha256':prior_hd['sha256'],'feed_sha256':digest((output/'update-720p.json').read_bytes())}
    (output / 'BUILD-INFO.json').write_text(json.dumps(build, indent=2) + '\n')
    hashes = {}
    for asset in meta['assets']:
        if asset['name'] == 'SHA256SUMS': continue
        value = asset.get('digest', '')
        if not re.fullmatch('sha256:[a-f0-9]{64}', value): raise ValueError('Missing asset digest: ' + asset['name'])
        hashes[asset['name']] = value[7:]
    hashes.update({p.name: digest(p.read_bytes()) for p in output.iterdir()})
    (output / 'SHA256SUMS').write_text(''.join(hashes[n] + '  ' + n + '\n' for n in sorted(hashes)))
    print('Prepared ' + args.tag + ': Root ' + root['version'] + ', Home ' + home['home'] + ', rollback ' + prior['home'] + ' from ' + previous_tag)


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as error:
        # Never echo command environments or key material, including on signing failures.
        sys.exit('Release preparation failed: ' + (str(error) if not isinstance(error, subprocess.CalledProcessError) else 'command failed; see preceding validation output'))
