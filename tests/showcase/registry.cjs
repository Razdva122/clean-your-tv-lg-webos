'use strict';
const assert = require('node:assert/strict'), fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {validateRecord,loadRegistry,validateFiles}=require('../../scripts/check-theme-submissions.cjs');
const fixture=require('./fixture.cjs'),root=fs.mkdtempSync(path.join(os.tmpdir(),'cytv-registry-'));
try {
 const {record:r,base}=fixture(root); fixture(root,'day');
 validateRecord({...r,license:'MIT AND CC-BY-SA-3.0'});
 validateRecord({...r,license:'LicenseRef-Personal-Fan-Theme'});
 assert.throws(()=>validateRecord({...r,license:'MIT OR unknown'}),/license/);
 assert.equal(loadRegistry(root).length,2,'distinct themes in a collection retain distinct IDs');
 const orderFile=path.join(root,'order.json'),pinned=[r.id,'github:owner/collection:day'];
 fs.writeFileSync(orderFile,JSON.stringify(pinned));
 assert.deepEqual(loadRegistry(root).map(e=>e.record.id),pinned,'curated order overrides filename order');
 const newcomer=fixture(root,'aaa');
 assert.deepEqual(loadRegistry(root).map(e=>e.record.id),[...pinned,newcomer.record.id],'new alphabetically earlier theme appends after existing themes');
 fs.writeFileSync(orderFile,JSON.stringify([...pinned,r.id]));
 assert.throws(()=>loadRegistry(root),/order/i,'duplicate ordered IDs are rejected');
 fs.writeFileSync(orderFile,JSON.stringify([...pinned,'github:owner/collection:missing']));
 assert.throws(()=>loadRegistry(root),/order/i,'unknown ordered IDs are rejected');
 fs.writeFileSync(orderFile,JSON.stringify(pinned));
 for(const change of [{title:'<img src=x onerror=alert(1)>'},{descriptorUrl:r.descriptorUrl.replace(r.sourceCommit,'main')},{descriptorUrl:r.descriptorUrl.replace('/owner/','/attacker/')},{descriptorUrl:r.descriptorUrl.replace('/night/','/../')},{descriptorUrl:r.descriptorUrl+'?raw=1'},{themeApiVersion:2},{license:'All rights reserved'},{author:{name:'Owner',sourceProfile:'https://github.com/attacker'}},{creditsFile:'../secrets'},{previewFiles:['https://evil.test/image.png']},{previewFiles:[base+'../evil.png']},{sourceCommit:'a'.repeat(39)},{themeVersion:'01.0.0'},{tags:['trending']},{reviewedAt:'2026-02-30'},{approved:true},{evidence:[{kind:'device',summary:'test',url:'javascript:alert(1)'}]}]) assert.throws(()=>validateRecord({...r,...change}),JSON.stringify(change));
 fs.writeFileSync(path.join(root,base,'CREDITS.txt'),'tampered');assert.throws(()=>validateFiles(r,root),/Byte\/hash mismatch/);
 fs.writeFileSync(path.join(root,base,'CREDITS.txt'),'Original test image\n');
 fs.writeFileSync(path.join(root,'registry','another.json'),JSON.stringify(r));assert.throws(()=>loadRegistry(root),/identity|Duplicate/);
 console.log('Showcase registry: valid local byte hashes, multi-theme identity and 17 hostile records passed');
} finally {fs.rmSync(root,{recursive:true,force:true});}
