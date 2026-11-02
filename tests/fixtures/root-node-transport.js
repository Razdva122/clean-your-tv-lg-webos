'use strict';
// Only the network boundary is redirected: real generated policies, Node HTTPS,
// TLS certificate/hostname verification, response streams and deadlines execute.
var assert=require('assert'),fs=require('fs'),https=require('https'),path=require('path'),Module=require('module'),dns=require('dns'),lookup=dns.lookup;
var base=process.argv[2],realGet=https.get,load=Module._load,cert=fs.readFileSync(base+'/cert.pem'),port,mode='ok',seen=0,lastError;
var server=https.createServer({key:fs.readFileSync(base+'/key.pem'),cert:cert},function(req,res){
 if(req.url.indexOf('/timeout')>=0)return;
 if(req.url.indexOf('/abort')>=0){res.writeHead(200);res.write('partial');res.socket.destroy();return;}
 if(req.url.indexOf('/redirect')>=0){res.writeHead(302,{Location: mode==='foreign'?'https://example.com/forbidden':'../package'});res.end();return;}
 if(req.url.indexOf('/loop')>=0){res.writeHead(302,{Location:'loop'});res.end();return;}
 if(req.url.indexOf('/http-error')>=0){res.writeHead(503);res.end();return;}
 res.writeHead(200);res.end('package!');
});
var originalRead=fs.readFileSync;
// Node 0.12 ignores request-local lookup; redirect only this synthetic DNS name.
dns.lookup=function(host,options,callback){
 if(host!=='wrong.invalid')return lookup.apply(dns,arguments);
 if(typeof options==='function')callback=options;
 var address=server.address().address,family=address.indexOf(':')>=0?6:4;
 process.nextTick(function(){if(options&&options.all)callback(null,[{address:address,family:family}]);else callback(null,address,family);});
};
Module._load=function(name,parent,isMain){
 if(name==='https')return {get:function(options,respond){
  assert.equal(typeof options,'object','HTTPS must receive a single options object');
  assert.strictEqual(options.rejectUnauthorized,true);assert.equal(options.ca,cert.toString());seen++;
  var local={hostname:mode==='hostname'?'wrong.invalid':'localhost',port:port,path:options.path,method:'GET',rejectUnauthorized:options.rejectUnauthorized,ca:mode==='untrusted'?undefined:options.ca,headers:options.headers};
  lastError=null;var request=realGet(local,respond);request.on('error',function(error){lastError=error;});return request;
 }};
 if(name==='fs')return Object.assign({},fs,{readFileSync:function(file,encoding){return /\/ca-bundle\.crt$/.test(file)?encoding?cert.toString():cert:originalRead.apply(fs,arguments);}});
 return load.call(this,name,parent,isMain);
};
var fetch=require(base+'/root-updater/updater/fetch'),policy=require(base+'/system/system_updater/policy');
function rejects(promise,pattern,expectedCode){return promise.then(function(){throw Error('unexpected successful transport: '+mode);},function(error){assert(error);if(pattern){assert(lastError&&pattern.test(lastError.message),String(lastError&&lastError.message));if(expectedCode)assert.equal(error.updateError,expectedCode);}});}
var prefix='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.2.3/';
function run(p){
 mode='ok';
 return p.get(prefix+'package',8).then(function(raw){assert.equal(raw.toString(),'package!');return p.get(prefix+'redirect',8);}).then(function(raw){assert.equal(raw.toString(),'package!');return rejects(p.get(prefix+'package',7));}).then(function(){return rejects(p.get(prefix+'loop',8));}).then(function(){return rejects(p.get(prefix+'abort',8));}).then(function(){return rejects(p.get(prefix+'http-error',8));}).then(function(){mode='foreign';return rejects(p.get(prefix+'redirect',8));}).then(function(){mode='hostname';return rejects(p.get(prefix+'package',8),/altname|hostname|certificate.*name/i,p===policy?'connection-error':undefined);}).then(function(){mode='untrusted';return rejects(p.get(prefix+'package',8),/self.signed/i,p===policy?'connection-error':undefined);}).then(function(){mode='ok';var timer=global.setTimeout;global.setTimeout=function(fn,ms){return timer(fn,ms===60000?50:ms);};return rejects(p.get(prefix+'timeout',8)).then(function(){global.setTimeout=timer;},function(error){global.setTimeout=timer;throw error;});}).then(function(){var before=seen;return rejects(p.get('https://example.com/package',8)).then(function(){assert.equal(seen,before);});});
}
server.listen(0,'localhost',function(){port=server.address().port;run(fetch).then(function(){return run(policy);}).then(function(){console.log('PASS Root generated HTTPS '+process.version+': strict TLS/hostname, redirects, size, HTTP/abort/deadline failures and URL admission');done();},function(error){console.error(error.stack);process.exitCode=1;done();});});
function done(){Module._load=load;dns.lookup=lookup;server.close();}
