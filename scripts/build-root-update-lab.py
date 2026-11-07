#!/usr/bin/env python3
"""Build disposable Root TV fixtures from committed HEAD; never contacts a TV."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
APP = 'com.cleanyourtv.root.updatetest'
UPDATER = 'com.cleanyourtv.root.updaterlab'
FEED = 'http://127.0.0.1:18997/releases/'
TEXT = {'.py', '.js', '.cjs', '.mjs', '.json', '.html', '.css', '.sh'}
# One regex over the original bytes avoids remapping a replacement's shorter prefix.
MAPPINGS = {
    '51-clean-your-tv-root-updater': '59-clean-your-tv-root-updaterlab',
    '50-clean-your-tv-root': '58-clean-your-tv-root-updatetest',
    'com.cleanyourtv.root.updater': UPDATER,
    'com.cleanyourtv.root.preview': APP,
    'clean-your-tv-root-updater': 'clean-your-tv-root-updaterlab',
    'clean-your-tv-root': 'clean-your-tv-root-updatetest',
}
PATTERN = re.compile('|'.join(re.escape(value) for value in sorted(MAPPINGS, key=len, reverse=True)))


def run(*args, cwd=ROOT):
    # The archived source stays isolated; share only the installed build tools.
    node_path = os.pathsep.join(filter(None, [str(ROOT / 'node_modules'), os.environ.get('NODE_PATH')]))
    environment = dict(os.environ, NODE_PATH=node_path)
    return subprocess.run(args, cwd=cwd, env=environment, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()


def clone_head(destination, commit):
    raw = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            relative = Path(member.name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe committed archive member')
            if any(part in {'.git', 'state', 'keys', 'node_modules'} for part in relative.parts) or relative.suffix in {'.key', '.pem'}:
                continue
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
                target.chmod(member.mode & 0o777)
            else:
                raise ValueError('Indirect committed source: ' + member.name)


def transform(source):
    changed = []
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.suffix not in TEXT:
            continue
        original = path.read_text()
        updated = PATTERN.sub(lambda match: MAPPINGS[match.group()], original)
        if updated != original:
            path.write_text(updated)
            changed.append(str(path.relative_to(source)))
    path = source / 'root-edition/updater/fetch.js'
    raw = path.read_text()
    policy = "function allowed(raw){try{var u=new URL(raw);return u.protocol==='http:'&&u.hostname==='127.0.0.1'&&u.port==='18997'&&!u.username&&!u.password&&!u.search&&!u.hash&&(u.pathname==='/releases/latest/download/root-update.json'||/^\\/releases\\/download\\/v\\d{1,4}\\.\\d{1,4}\\.\\d{1,4}\\/com\\.cleanyourtv\\.root\\.updatetest_\\d{1,4}\\.\\d{1,4}\\.\\d{1,4}_all\\.ipk$/.test(u.pathname));}catch(_){return false;}}\n"
    updated,count=re.subn(r'(?ms)^function allowed\(raw\)\s*\{.*?(?=^function feedName\()',lambda _:policy,raw)
    if count!=1:raise ValueError('Expected one pinned URL policy')
    updated,count=re.subn(r"\bhttps\s*=\s*require\(\s*(['\"])https\1\s*\)","http=require('http')",updated)
    if count!=1:raise ValueError('Expected one HTTPS fixture import')
    updated,count=re.subn(r'\breq\s*=\s*https\.get\s*\(', 'req=http.get(',updated)
    if count!=1:raise ValueError('Expected one HTTPS fixture request')
    updated = updated.replace('https://github.com/Razdva122/clean-your-tv-lg-webos/releases/', FEED)
    path.write_text(updated)
    if str(path.relative_to(source)) not in changed:
        changed.append(str(path.relative_to(source)))
    path = source / 'root-edition/update_manifest.py'
    path.write_text(path.read_text().replace('https://github.com/Razdva122/clean-your-tv-lg-webos/releases/', FEED))
    changed.append(str(path.relative_to(source)))
    return sorted(set(changed))


SIGN_AND_BUILD = r'''
'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
const [output,python]=process.argv.slice(1),source=path.join(output,'source');
// Private key exists only in this Node process and is never serialized or logged.
const keys=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
fs.writeFileSync(path.join(source,'updater-service/release-public.pem'),keys.publicKey.export({type:'spki',format:'pem'}),{flag:'wx'});
const built=cp.spawnSync(python,[path.join(source,'root-edition/build_updater.py'),'--output',path.join(output,'updater-bundle')],{encoding:'utf8'});
if(built.status!==0)throw Error(built.stderr||'Updater build failed');
for(const version of ['0.1.1','0.1.2']){
 const manifest=JSON.parse(fs.readFileSync(path.join(output,'manifest-'+version+'.json')));
 const bytes=Buffer.from(JSON.stringify(manifest));
 const envelope={payload:bytes.toString('base64'),signature:crypto.sign('RSA-SHA256',bytes,keys.privateKey).toString('base64')};
 const raw=JSON.stringify(envelope,null,2)+'\n';
 fs.writeFileSync(path.join(output,'offer-'+version+'.json'),raw,{flag:'wx'});
 const label=version==='0.1.1'?'candidate':'rollback-test',name=manifest.application+'_'+version+'_all.ipk';
 const target=path.join(output,'http/releases/download/v'+version);fs.mkdirSync(target,{recursive:true});
 fs.copyFileSync(path.join(output,'packages',label,name),path.join(target,name),fs.constants.COPYFILE_EXCL);
 if(version==='0.1.1'){
  const latest=path.join(output,'http/releases/latest/download');fs.mkdirSync(latest,{recursive:true});
  fs.writeFileSync(path.join(latest,'root-update.json'),raw,{flag:'wx'});
 }
 const verifier=require(path.join(source,'root-edition/updater/fetch.js'));
 verifier.verify(envelope,keys.publicKey);
}
'''


def build(output):
    output = Path(output).absolute()
    if '..' in output.parts or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('Output must not traverse symlinks or parent segments')
    commit = run('git', 'rev-parse', 'HEAD')
    production_key = ROOT / 'updater-service/release-public.pem'
    key_digest = hashlib.sha256(production_key.read_bytes()).hexdigest()
    output.mkdir(exist_ok=False)
    source = output / 'source'
    source.mkdir()
    clone_head(source, commit)
    changed = transform(source)
    (output / 'packages').mkdir()
    for label, version in (('baseline', '0.1.0'), ('candidate', '0.1.1'), ('rollback-test', '0.1.2')):
        bundle = output / 'packages' / label
        run(sys.executable, str(source / 'root-edition/build.py'), '--output', str(bundle), '--version', version)
        run(sys.executable, '-c', 'from deploy import verify_bundle; import sys; verify_bundle(sys.argv[1])', str(bundle), cwd=source / 'root-edition')
        if label != 'baseline':
            run(sys.executable, str(source / 'root-edition/update_manifest.py'), '--bundle', str(bundle), '--release', 'v' + version,
                '--notes', 'Disposable Root update acceptance test ' + version, '--output', str(output / ('manifest-' + version + '.json')))
    run('node', '-e', SIGN_AND_BUILD, str(output), sys.executable)
    run(sys.executable, '-c', 'from updater.bootstrap import verify_bundle; import sys; verify_bundle(sys.argv[1])', str(output / 'updater-bundle'), cwd=source / 'root-edition')
    if hashlib.sha256(production_key.read_bytes()).hexdigest() != key_digest:
        raise ValueError('Production public key changed during lab build')
    evidence = {
        'schema': 1, 'source_commit': commit, 'source_method': 'git archive committed HEAD',
        'source': str(source), 'application': APP, 'service': APP + '.service',
        'updater_application': UPDATER, 'updater_service': UPDATER + '.service',
        'feed': FEED + 'latest/download/root-update.json', 'mappings': MAPPINGS,
        'paths': {
            'root_state': '/var/lib/clean-your-tv-root-updatetest',
            'updater_state': '/var/lib/clean-your-tv-root-updaterlab',
            'profile_override': '/var/webos-profile/override/clean-your-tv-root-updatetest.json',
            'root_hook': '/var/lib/webosbrew/init.d/58-clean-your-tv-root-updatetest',
            'updater_hook': '/var/lib/webosbrew/init.d/59-clean-your-tv-root-updaterlab',
            'system_manifest': '/var/luna-service2/manifests.d/' + APP + '.recovery.json',
        },
        'changed_files': changed, 'production_public_key_sha256': key_digest,
        'lab_public_key_sha256': hashlib.sha256((source / 'updater-service/release-public.pem').read_bytes()).hexdigest(),
        'private_key_persisted': False, 'generic_inventory': {'apps': [], 'inputs': []},
        'ordinary_profile_source': '/media/developer/apps/usr/palm/services/com.cleanyourtv.updater.service/state/profile.json',
        'bundles_verified': ['packages/baseline', 'packages/candidate', 'packages/rollback-test', 'updater-bundle'],
    }
    (output / 'lab-transform.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New directory; parent must exist')
    args = parser.parse_args()
    try:
        print('Built isolated Root TV acceptance fixtures: ' + str(build(args.output)))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'Root lab build failed: ' + str(error) + '\n')
