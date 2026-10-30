'use strict';
const assert=require('assert'),crypto=require('crypto');
let policy;try{policy=require('../../system-updater/policy');}catch(e){assert.fail('independent system update policy is missing');}
const base='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.2.3/';
function manifest(edition='no-root'){return {schema:1,edition,release:'v1.2.3',supervisor:1,notes:'Signed',components:(edition==='root'?[['root','com.cleanyourtv.root.preview'],['root-updater','com.cleanyourtv.root.updater'],['root-infrastructure',null]]:[['home','com.gathin.tvhome'],['helper','com.local.nativehome'],['updater','com.cleanyourtv.updater']]).map(([name,application])=>Object.assign({name,version:'1.2.3',kind:application?'ipk':'infrastructure',url:base+name+(application?'.ipk':'.tar.gz'),sha256:'a'.repeat(64),size:22},application?{application}:{}))};}
assert.equal(policy.validate(manifest()).components.length,3);assert.equal(policy.validate(manifest('root')).edition,'root');
for(const change of [m=>m.components[0].application='org.foreign',m=>m.components[0].url=base+'../evil.ipk',m=>m.components[0].url=base+'evil.ipk?q=x',m=>m.components.pop(),m=>m.components.push(m.components[0]),m=>m.components[0].command='reboot',m=>m.release='v9.9.9',m=>m.supervisor=2,m=>m.components[0].size=1e12]){const m=manifest();change(m);assert.throws(()=>policy.validate(m));}
const {privateKey,publicKey}=crypto.generateKeyPairSync('rsa',{modulusLength:2048});const raw=Buffer.from(JSON.stringify(manifest()));const envelope={payload:raw.toString('base64'),signature:crypto.sign('RSA-SHA256',raw,privateKey).toString('base64')};assert.equal(policy.verify(envelope,publicKey).release,'v1.2.3');envelope.payload=Buffer.from(JSON.stringify(manifest('root'))).toString('base64');assert.throws(()=>policy.verify(envelope,publicKey),/signature/);
console.log('System update policy tests passed');

// Run the real CLI against offline HTTPS fixtures.
async function offerFixture(status,body,error){
 const vm=require('vm'),fs=require('fs'),path=require('path'),EventEmitter=require('events');
 const callbacks={},output={stdout:'',stderr:'',exitCode:0},directory=path.resolve(__dirname,'../../system-updater');
 const request=new EventEmitter();request.destroy=()=>{};
 const fakeHttps={get(options,respond){queueMicrotask(()=>{
  if(error==='timeout')return;
  if(error){request.emit('error',Object.assign(Error('/private/internal network detail'),{code:error}));return;}
  const response=new EventEmitter();response.statusCode=status;response.headers={};response.resume=()=>{};response.destroy=()=>{};respond(response);
  if(status===200){response.emit('data',Buffer.from(body));response.emit('end');}
 });return request;}};
 const fakeProcess={argv:['node','policy.js','offer'],stdin:{setEncoding(){},on(event,fn){callbacks[event]=fn;}},stdout:{write(s){output.stdout+=s;}},stderr:{write(s){output.stderr+=s;}},exit(code){output.exitCode=code;}};
 Object.defineProperty(fakeProcess,'exitCode',{get(){return output.exitCode;},set(v){output.exitCode=v;}});
 const fakeFs={readFileSync(file){if(file===directory+'/release-public.pem')return publicKey.export({type:'spki',format:'pem'});if(file===directory+'/ca-bundle.crt')return 'offline CA fixture';throw Error('unexpected fixture file');}};
 const main={exports:{}};const load=name=>name==='https'?fakeHttps:name==='fs'?fakeFs:require(name);load.main=main;
 vm.runInNewContext(fs.readFileSync(directory+'/policy.js','utf8'),{require:load,module:main,__dirname:directory,process:fakeProcess,Buffer,setTimeout:error==='timeout'?(fn=>{queueMicrotask(fn);return 1;}):setTimeout,clearTimeout});
 callbacks.data('{"edition":"root"}');await callbacks.end();return output;
}
(async()=>{
 for(const [status,body,error,expected] of [[404,'',null,'feed-unavailable'],[503,'',null,'connection-error'],[null,'','ECONNRESET','connection-error'],[null,'','timeout','connection-error'],[200,'broken',null,'verification-error'],[200,JSON.stringify(envelope),null,'verification-error']]){
  const result=await offerFixture(status,body,error);assert.equal(result.exitCode,1);assert.equal(result.stdout,JSON.stringify({error:expected}));assert.equal(result.stderr,'');
 }
 console.log('System update offline offer error fixtures passed');
})().catch(e=>{console.error(e);process.exitCode=1;});

// New Root offers fail closed on the actual immutable 1.3 supervisor policy.
const historical=manifest('root'),gated={...historical,minimumSupervisorVersion:'1.1.1'};
assert.equal(policy.validate(gated).minimumSupervisorVersion,'1.1.1');
assert.equal(policy.validate(historical).edition,'root');
for(const value of ['1.1.3','2.0.0','bad',null,111])assert.throws(()=>policy.validate({...gated,minimumSupervisorVersion:value}));
assert.throws(()=>policy.validate({...manifest(),minimumSupervisorVersion:'1.1.1'}));
const originalSource=require('child_process').execFileSync('python3',['-c',"import tarfile;print(tarfile.open('tests/system_updates/fixtures/public-1.3.0-supervisor.tar.gz').extractfile('supervisor/system_updater/policy.js').read().decode(),end='')"],{cwd:require('path').resolve(__dirname,'../..'),encoding:'utf8'});
const original={exports:{}};
require('vm').runInNewContext(originalSource,{require,module:original,Buffer,process,__dirname:require('path').resolve(__dirname,'../../system-updater')});
assert.equal(original.exports.validate(historical).edition,'root');
assert.throws(()=>original.exports.validate(gated),/incompatible/);
const rawGated=Buffer.from(JSON.stringify(gated)),signedGated={payload:rawGated.toString('base64'),signature:crypto.sign('RSA-SHA256',rawGated,privateKey).toString('base64')};
assert.throws(()=>original.exports.verify(signedGated,publicKey),/incompatible/);
assert.equal(policy.verify(signedGated,publicKey).minimumSupervisorVersion,'1.1.1');
console.log('PASS historical six-field proofs retained; new Root minimum rejects old supervisor before offer');
