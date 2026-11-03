#!/usr/bin/env node
'use strict';
// Browser preview only: reuse reviewed data and the ordinary theme envelope validator.
const fs=require('node:fs'),path=require('node:path');
const {loadRegistry,readLocal}=require('./check-theme-submissions.cjs');
const root=path.resolve(__dirname,'../showcase');
const entries=loadRegistry(root).filter(e=>!e.record.availability);
const themes=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../launcher/theme-catalog.json'))).themes;
const packages={};
const mode=process.argv[2],argument=process.argv[3];
if(mode&&!['--output','--package'].includes(mode)||mode&&!argument)throw Error('Use --output DIRECTORY or --package DIGEST');
let requested;

for(const {record,base,files} of entries){
 const url='packages/'+record.descriptorSha256+'.json';
 packages[record.id]=url;
 if(!mode||mode==='--package'&&argument!==record.descriptorSha256)continue;
 const envelope={schemaVersion:1,descriptor:readLocal(root,base+'cytv-theme.json',65536).toString('base64'),files:{}};
 for(const file of files.filter(f=>f!=='cytv-theme.json'))envelope.files[file]=readLocal(root,base+file,6291456).toString('base64');
 if(mode==='--package')requested=envelope;
 else {const target=path.resolve(argument,url);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,JSON.stringify(envelope));}
}
if(themes.some(t=>!t.builtin&&!packages[t.id]))throw Error('Preview catalog has no reviewed package');
if(mode==='--package'&&!requested)throw Error('Unknown reviewed theme package');
process.stdout.write(JSON.stringify(mode==='--package'?requested:{themes,packages}));
