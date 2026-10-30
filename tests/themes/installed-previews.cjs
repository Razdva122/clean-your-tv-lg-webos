'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const data=require('../../launcher/theme-data.js'),entry=require('../../scripts/check-theme-submissions.cjs').loadRegistry().find(e=>e.record.title==='Channel');
const original={descriptor:new Uint8Array(fs.readFileSync(path.join('showcase',entry.base,'cytv-theme.json'))),digest:entry.record.descriptorSha256,files:{}};
for(const name of entry.files.filter(n=>n!=='cytv-theme.json'))original.files[name]=new Uint8Array(fs.readFileSync(path.join('showcase',entry.base,name)));
let pack=structuredClone(original),made=0,revoked=0,blob;
const ctx={Promise,Uint8Array,ArrayBuffer,Blob,URL:{createObjectURL(value){made++;blob=value;return 'blob:preview';},revokeObjectURL(){revoked++;}},ThemeStore:{get:async()=>pack},ThemeData:Object.assign({},data,{request:async url=>data.encode(JSON.stringify(url==='appinfo.json'?{version:'1.5.1'}:{schemaVersion:1,themes:[{id:'builtin:alpine',title:'Alpine',version:'1.0.0',url:'themes/alpine/cytv-theme.json',digest:'b'.repeat(64)}]}))})};
vm.runInNewContext(fs.readFileSync('launcher/theme-manager.js','utf8'),ctx);
(async()=>{
 const lease=await ctx.ThemeManager.preview({id:entry.record.id,digest:original.digest});assert.equal(lease.url,'blob:preview');assert.equal(blob.type,'image/png');assert.equal(blob.size,entry.manifest.assets.find(a=>a.id===entry.manifest.previewAssetId).size);lease.dispose();lease.dispose();assert.equal(revoked,1);
 pack=structuredClone(original);pack.files[entry.manifest.assets[0].path][0]^=1;await assert.rejects(ctx.ThemeManager.preview({id:entry.record.id,digest:original.digest}),/hash mismatch/);assert.equal(made,1);
 pack=structuredClone(original);delete pack.files[entry.manifest.assets[0].path];await assert.rejects(ctx.ThemeManager.preview({id:entry.record.id,digest:original.digest}));assert.equal(made,1);
 pack=original;await assert.rejects(ctx.ThemeManager.preview({id:'github:other/repo:theme',digest:original.digest}),/identity/);assert.equal(made,1);
 pack=null;await assert.rejects(ctx.ThemeManager.preview({id:entry.record.id,digest:original.digest}),/missing/);assert.equal(made,1);console.log('Installed preview leases: actual verified bytes, hash/missing/identity rejection and idempotent disposal passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
