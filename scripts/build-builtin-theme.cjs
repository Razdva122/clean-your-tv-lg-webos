#!/usr/bin/env node
'use strict';
// Maintainer-only compiler: bundled themes are data; this script never ships to TV.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const {readLocal}=require('./check-theme-submissions.cjs'),{compileSource}=require('../theme-api/compile.cjs');
const root=path.resolve(__dirname,'..'),args=process.argv.slice(2),check=args.includes('--check');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),encode=x=>Buffer.from(JSON.stringify(x,null,2)+'\n');
(async()=>{
 if(args.filter(a=>!a.startsWith('--')).length!==1||args.some(a=>a.startsWith('--')&&a!=='--check'))throw Error('Use build-builtin-theme.cjs themes/SLUG [--check]');
 const source=path.resolve(root,args[0]);if(!source.startsWith(root+path.sep))throw Error('Source must be inside the repository');
 const manifest=JSON.parse(readLocal(source,'theme.json',65536));
 if(!/^builtin:[a-z0-9][a-z0-9-]{0,63}$/.test(manifest.id)||manifest.id==='builtin:classic')throw Error('Expected a packaged built-in identity');
 const relative='themes/'+manifest.id.slice(8),out=path.join(root,'launcher',relative),descriptorPath=path.join(out,'cytv-theme.json');
 const previous=fs.existsSync(descriptorPath)?JSON.parse(fs.readFileSync(descriptorPath)):null;
 const commit=previous?previous.source.commit:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
 const assets=manifest.assets.map(a=>({...a,data:readLocal(source,a.path,2097152)}));
 const documents=[...new Set([manifest.license.textPath,manifest.license.creditsPath])].map(name=>({path:name,data:readLocal(source,name,32768)}));
 const inputs=['theme.json','theme.css',...assets.map(a=>a.path),...documents.map(d=>d.path)];
 // Keep exact source provenance stable across later unrelated commits.
 // A shallow CI checkout can verify reproducible bytes without fetching source history.
 if(!check)for(const name of inputs){const actual=readLocal(source,name,6291456),pinned=cp.execFileSync('git',['show',commit+':'+path.relative(root,path.join(source,name)).split(path.sep).join('/')],{cwd:root,maxBuffer:8*1024*1024});if(!actual.equals(pinned))throw Error('Commit changed theme source and remove its old generated bundle before rebuilding');}
 const home=JSON.parse(fs.readFileSync(path.join(root,'launcher/appinfo.json')));
 const result=await compileSource({manifest,css:readLocal(source,'theme.css',262144).toString('utf8'),assets,documents,source:{repository:'https://github.com/razdva122/clean-your-tv-lg-webos',commit},minimumHomeVersion:previous?previous.requires.minimumHomeVersion:home.themeEngineVersion||home.version});
 const files=new Map(),m=result.manifest;m.rules.path='rules/'+m.rules.sha256+'.json';files.set(m.rules.path,Buffer.from(JSON.stringify(result.rules)+'\n'));
 for(const group of ['assets','documents'])for(const f of result[group]){const old=f.path,identity=group==='assets'?f.id:result[group].indexOf(f),name=group+'/'+identity+'-'+f.sha256+path.extname(old).toLowerCase();m[group].find(a=>a.path===old).path=name;if(m.license.textPath===old)m.license.textPath=name;if(m.license.creditsPath===old)m.license.creditsPath=name;files.set(name,f.data);}
 const descriptor=encode(m);files.set('cytv-theme.json',descriptor);
 const registryPath=path.join(root,'launcher/builtin-themes.json'),registry=JSON.parse(fs.readFileSync(registryPath));
 const entry={id:m.id,title:m.title,version:m.themeVersion,url:relative+'/cytv-theme.json',digest:hash(descriptor)},index=registry.themes.findIndex(e=>e.id===m.id);if(index<0)registry.themes.push(entry);else registry.themes[index]=entry;
 const inventoryPath=path.join(root,'launcher/builtin-theme-files.json'),inventory=JSON.parse(fs.readFileSync(inventoryPath)).filter(p=>!p.startsWith(relative+'/')).concat([...files.keys()].map(p=>relative+'/'+p)).sort();
 if(check){for(const [name,data]of files)if(!fs.existsSync(path.join(out,name))||!fs.readFileSync(path.join(out,name)).equals(data))throw Error('Stale bundled theme: '+name);if(!fs.readFileSync(registryPath).equals(encode(registry))||!fs.readFileSync(inventoryPath).equals(encode(inventory)))throw Error('Stale built-in registry/inventory');}
 else{fs.rmSync(out,{recursive:true,force:true});for(const [name,data]of files){fs.mkdirSync(path.dirname(path.join(out,name)),{recursive:true});fs.writeFileSync(path.join(out,name),data);}fs.writeFileSync(registryPath,encode(registry));fs.writeFileSync(inventoryPath,encode(inventory));}
 console.log((check?'Verified':'Built')+' '+m.id+' from '+commit);
})().catch(e=>{console.error(e.message);process.exitCode=1});
