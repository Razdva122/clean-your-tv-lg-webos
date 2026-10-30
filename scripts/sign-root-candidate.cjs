'use strict';
// QA artifacts only. Stable publication and No-root compatibility use their own gates.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const policy=require('../system-updater/policy');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function notesFor(m){return (m.preliminary===true?'PRELIMINARY Root QA; package job '+(m.package_job||{}).id+'; full validation not required or established; not final release acceptance. ':'')+'Unpublished Root QA only; source '+m.source+'; build '+m.run_id+':'+m.attempt+'; artifact '+m.artifact.sha256+'. No stable publication or No-root approval.';}
function read(file,limit){const s=fs.lstatSync(file);if(!s.isFile()||s.nlink!==1||s.size>limit)throw Error('Unsafe signing input');return fs.readFileSync(file);}
function signRootCandidate(folder,privateKey,publicKey){
 const output=path.join(folder,'system-update-root.json');
 if(fs.existsSync(output))throw Error('Signed candidate already exists');
 const meta=JSON.parse(read(path.join(folder,'PROVENANCE.json'),65536));
 const manifest=JSON.parse(read(path.join(folder,'manifest.json'),65536));
 if(Object.prototype.hasOwnProperty.call(meta,'preliminary')&&(meta.preliminary!==true||typeof meta.branch!=='string'||!meta.branch||meta.branch.startsWith('refs/')))throw Error('Invalid preliminary provenance');
 if(Object.prototype.hasOwnProperty.call(meta,'direct_tv')){const pem=typeof publicKey==='string'||Buffer.isBuffer(publicKey)?publicKey:publicKey.export({type:'spki',format:'pem'});if(meta.direct_tv!==true||meta.preliminary!==true||meta.workflow!=='.github/workflows/tv-candidate.yml'||meta.public_key_sha256!==sha(Buffer.from(pem)))throw Error('Invalid direct TV provenance or key');}
 if(meta.preliminary===true){const j=meta.package_job;if(!j||!Number.isSafeInteger(j.id)||j.id<=0||j.name!==(meta.direct_tv===true?'build-root-tv':'build (macos-15, cytv-macos-arm64, dist/cytv)')||j.status!=='completed'||j.conclusion!=='success'||j.run_id!==meta.run_id||j.head_sha!==meta.source||j.run_attempt!==meta.attempt)throw Error('Invalid preliminary package job');}
 if(meta.schema!==1||!/^v\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(meta.release)||!meta.versions||'v'+meta.versions.release!==meta.release||!Number.isSafeInteger(meta.run_id)||meta.run_id<=0||!Number.isSafeInteger(meta.attempt)||meta.attempt<=0||!/^[a-f0-9]{40}$/.test(meta.source)||!meta.artifact||!/^[a-f0-9]{64}$/.test(meta.artifact.sha256))throw Error('Invalid candidate provenance');
 if(manifest.edition!=='root')throw Error('Only Root QA signing is permitted');
 policy.validate(manifest);
 if(manifest.release!==meta.release||manifest.notes!==notesFor(meta))throw Error('Candidate provenance differs from manifest');
 const files=manifest.components.map(c=>{const name=c.url.split('/').pop();if(name!==path.basename(name)||name.indexOf('%')!==-1)throw Error('Unsafe candidate asset');const expected=c.name==='root-updater'?meta.versions.updater:meta.versions.root;if(c.version!==expected)throw Error('Candidate version mismatch');const raw=read(path.join(folder,name),64*1024*1024);if(raw.length!==c.size||sha(raw)!==c.sha256||!meta.files||meta.files[name]!==c.sha256)throw Error('Candidate package hash/size mismatch');return name;});
 if(files.length!==3||new Set(files).size!==3||Object.keys(meta.files||{}).sort().join('\n')!==files.slice().sort().join('\n')||fs.readdirSync(folder).sort().join('\n')!==files.concat(['manifest.json','PROVENANCE.json']).sort().join('\n'))throw Error('Unexpected candidate inventory');
 const bytes=Buffer.from(JSON.stringify(manifest)),envelope={payload:bytes.toString('base64'),signature:crypto.sign('RSA-SHA256',bytes,privateKey).toString('base64')};
 policy.verify(envelope,publicKey);
 fs.writeFileSync(output,JSON.stringify(envelope,null,2)+'\n',{flag:'wx',mode:0o600});
 return envelope;
}
module.exports={signRootCandidate,notesFor};
if(require.main===module){
 const key=process.env.UPDATE_SIGNING_PRIVATE_KEY;delete process.env.UPDATE_SIGNING_PRIVATE_KEY;
 try{if(process.argv.length!==3||!key)throw Error('Signing inputs missing');signRootCandidate(process.argv[2],key,fs.readFileSync(path.join(__dirname,'../updater-service/release-public.pem')));console.log('Signed and verified Root QA candidate only; no release or No-root feed published.');}
 catch(_){console.error('Root candidate signing refused; no release was published.');process.exitCode=1;}
}
