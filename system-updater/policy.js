'use strict';
// Independently provisioned trust boundary. Signed fields are data only.
var crypto=require('crypto'),https=require('https'),fs=require('fs'),URL=require('url').URL;
// Keep aligned with build.VERSION and the packaged app/service metadata.
var SUPERVISOR_VERSION='1.1.2';
var REPO='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/';
var IDENTITIES={home:'com.gathin.tvhome',helper:'com.local.nativehome',updater:'com.cleanyourtv.updater',root:'com.cleanyourtv.root.preview','root-updater':'com.cleanyourtv.root.updater','root-infrastructure':null};
var SETS={'no-root':['home','helper','updater'],root:['root','root-updater','root-infrastructure']},MAX=64*1024*1024;
function version(v){if(typeof v!=='string'||!/^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$/.test(v))throw Error('invalid-version');return v.split('.').map(Number);}
function compare(a,b){a=version(a);b=version(b);for(var i=0;i<3;i++)if(a[i]!==b[i])return a[i]>b[i]?1:-1;return 0;}
function fields(value,required){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===required.length&&required.every(function(k){return Object.prototype.hasOwnProperty.call(value,k);});}
function validate(m){
 var required=['schema','edition','release','supervisor','notes','components'];
 if(m&&m.edition==='root'&&Object.prototype.hasOwnProperty.call(m,'minimumSupervisorVersion'))required.push('minimumSupervisorVersion');
 if(!fields(m,required)||m.schema!==1||m.supervisor!==1||!SETS[m.edition]||typeof m.release!=='string'||m.release[0]!=='v'||typeof m.notes!=='string'||m.notes.length>4000||!Array.isArray(m.components))throw Error('incompatible-system-release');
 if(Object.prototype.hasOwnProperty.call(m,'minimumSupervisorVersion')&&compare(m.minimumSupervisorVersion,SUPERVISOR_VERSION)>0)throw Error('minimum-supervisor-version');
 version(m.release.slice(1));var seen={},names=SETS[m.edition];
 if(m.components.length!==names.length)throw Error('incomplete-system-release');
 m.components.forEach(function(c){
  var infra=c&&c.name==='root-infrastructure',required=['name','version','url','sha256','size','kind'];if(!infra)required.push('application');
  if(!fields(c,required)||names.indexOf(c.name)<0||seen[c.name]||c.kind!==(infra?'infrastructure':'ipk')||(!infra&&c.application!==IDENTITIES[c.name]))throw Error('invalid-component-identity');seen[c.name]=true;version(c.version);
  var prefix=REPO+'download/'+m.release+'/';
  if(typeof c.url!=='string'||c.url.indexOf(prefix)!==0||!/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(c.url.slice(prefix.length))||c.url.slice(prefix.length).indexOf('..')>=0||!(infra?/\.tar\.gz$/:/\.ipk$/).test(c.url)||typeof c.sha256!=='string'||!/[a-f0-9]{64}/.test(c.sha256)||c.sha256.length!==64||!Number.isInteger(c.size)||c.size<1||c.size>MAX)throw Error('invalid-component-asset');
 });return m;
}
function verify(e,key){
 if(!fields(e,['payload','signature'])||typeof e.payload!=='string'||typeof e.signature!=='string'||e.payload.length>65536||e.signature.length>2048)throw Error('invalid-envelope');
 var bytes=Buffer.from(e.payload,'base64'),sig=Buffer.from(e.signature,'base64');if(bytes.toString('base64')!==e.payload||sig.toString('base64')!==e.signature)throw Error('invalid-envelope');
 var verifier=crypto.createVerify('RSA-SHA256');verifier.update(bytes);verifier.end();if(!verifier.verify(key,sig))throw Error('invalid-signature');return validate(JSON.parse(bytes.toString('utf8')));
}
function allowed(raw){try{var u=new URL(raw);return u.protocol==='https:'&&!u.username&&!u.password&&!u.port&&!u.hash&&((u.hostname==='github.com'&&!u.search&&u.pathname.indexOf('/Razdva122/clean-your-tv-lg-webos/releases/')===0)||u.hostname==='release-assets.githubusercontent.com'||u.hostname==='objects.githubusercontent.com');}catch(_){return false;}}
function get(url,limit,redirects){return new Promise(function(resolve,reject){
 if(!allowed(url)||(redirects||0)>3)return reject(Error('url-rejected'));
 var done=false,total=0,chunks=[],req,timer;
 function finish(error,value){if(done)return;done=true;clearTimeout(timer);if(error){if(req)req.destroy();reject(error);}else resolve(value);}
 function transport(error){var failure=Error('download-failed');failure.updateError='connection-error';finish(failure);}
 var options=Object.assign(require('url').parse(url),{rejectUnauthorized:true,ca:fs.readFileSync(__dirname+'/ca-bundle.crt','utf8'),headers:{'User-Agent':'CleanYourTV-System-Updater','Accept':'application/octet-stream'}});
 req=https.get(options,function(res){
  if([301,302,303,307,308].indexOf(res.statusCode)>=0){res.resume();try{var next=new URL(res.headers.location,url).href;get(next,limit,(redirects||0)+1).then(function(b){finish(null,b);},finish);}catch(e){finish(e);}return;}
  if(res.statusCode!==200){res.resume();var failure=Error('download-http');failure.updateError=res.statusCode===404?'feed-unavailable':'connection-error';finish(failure);return;}
  res.on('data',function(b){total+=b.length;if(total>limit){res.destroy();finish(Error('download-too-large'));}else chunks.push(b);});res.on('end',function(){finish(null,Buffer.concat(chunks));});res.on('error',transport);res.on('aborted',transport);
 });timer=setTimeout(transport,60000);req.on('error',transport);
});}
module.exports={supervisorVersion:SUPERVISOR_VERSION,validate:validate,verify:verify,get:get,allowed:allowed,compare:compare};
if(require.main===module){var input='',method=process.argv[2];process.stdin.setEncoding('utf8');process.stdin.on('data',function(s){input+=s;if(Buffer.byteLength(input)>131072)process.exit(2);});process.stdin.on('end',async function(){try{
 var p=JSON.parse(input||'{}'),key=fs.readFileSync(__dirname+'/release-public.pem'),result,m;
 if(method==='offer'){if(!SETS[p.edition])throw Error('invalid-edition');var envelope=JSON.parse((await get(REPO+'latest/download/system-update-'+p.edition+'.json',131072)).toString('utf8'));m=verify(envelope,key);if(m.edition!==p.edition)throw Error('edition-mismatch');result={candidate:Object.assign({},m,{proof:envelope})};}
 else if(method==='verify')result=verify(p.proof,key);
 else if(method==='package'){m=verify(p.proof,key);var component=m.components.filter(function(c){return c.name===p.name;})[0];if(!component)throw Error('unknown-component');var bytes=await get(component.url,component.size);if(bytes.length!==component.size||crypto.createHash('sha256').update(bytes).digest('hex')!==component.sha256)throw Error('package-hash-mismatch');process.stdout.write(bytes);return;}
 else throw Error('unknown-operation');process.stdout.write(JSON.stringify(result));
 }catch(e){var code=e.updateError==='connection-error'?'connection-error':method==='offer'&&e.updateError==='feed-unavailable'?'feed-unavailable':'verification-error';process.stdout.write(JSON.stringify({error:code}));process.exitCode=1;}});}
