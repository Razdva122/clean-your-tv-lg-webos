 'use strict';
const assert=require('assert/strict'),fs=require('fs'),path=require('path');
const policy=require('../../launcher/theme-policy.js'),data=require('../../launcher/theme-data.js');
function box(type,...parts){const body=Buffer.concat(parts),h=Buffer.alloc(8);h.writeUInt32BE(body.length+8);h.write(type,4);return Buffer.concat([h,body]);}
function movie({width=1920,height=1080,duration=2000,audio=false,codec='avc1'}={}){
 const mvhd=Buffer.alloc(100);mvhd.writeUInt32BE(1000,12);mvhd.writeUInt32BE(duration,16);
 const tkhd=Buffer.alloc(84);tkhd.writeUInt32BE(width*65536,76);tkhd.writeUInt32BE(height*65536,80);
 const mdhd=Buffer.alloc(24);mdhd.writeUInt32BE(1000,12);mdhd.writeUInt32BE(duration,16);
 const hdlr=Buffer.alloc(24);hdlr.write(audio?'soun':'vide',8);
 const avc1=Buffer.alloc(78);avc1.writeUInt16BE(width,24);avc1.writeUInt16BE(height,26);
 const avcc=box('avcC',Buffer.from([1,100,0,40,255,225,0,2,103,100,1,0,2,104,0]));
 const sd=Buffer.alloc(8);sd.writeUInt32BE(1,4);
 const stbl=box('stbl',box('stsd',sd,box(codec,avc1,avcc)));
 const mdia=box('mdia',box('mdhd',mdhd),box('hdlr',hdlr),box('minf',stbl));
 return Buffer.concat([box('ftyp',Buffer.from('isom\0\0\0\0isomavc1','binary')),box('moov',box('mvhd',mvhd),box('trak',box('tkhd',tkhd),mdia)),box('mdat',Buffer.from([0,0,0,1,101]))]);
}
const fixture=require('./fixtures/valid-manifest.json');
function manifest(){const m=structuredClone(fixture);m.defaults.wallpaperAssetId=m.previewAssetId;m.requires.capabilities.push('video-wallpaper-v1');const bytes=movie();m.wallpaperVideo={variants:[{quality:'1080p',path:'wallpaper.mp4',mediaType:'video/mp4',size:bytes.length,sha256:data.hash(bytes),width:1920,height:1080}]};return m;}
assert.equal(policy.validateManifest(manifest()).wallpaperVideo.variants[0].quality,'1080p');
for(const edit of [m=>m.requires.capabilities.pop(),m=>m.defaults.wallpaperAssetId=null,m=>m.wallpaperVideo.variants.push(m.wallpaperVideo.variants[0]),m=>m.wallpaperVideo.variants[0].size=4194305,m=>m.wallpaperVideo.variants[0].width=3840,m=>m.wallpaperVideo.variants[0].path=m.assets[0].path,m=>m.wallpaperVideo.variants=[]]){const m=manifest();edit(m);assert.throws(()=>policy.validateManifest(m));}
const ungated=structuredClone(fixture);ungated.requires.capabilities.push('video-wallpaper-v1');assert.throws(()=>policy.validateManifest(ungated));
assert.deepEqual(data.videoInfo(movie()),{width:1920,height:1080,duration:2});
assert.deepEqual(data.videoInfo(movie({width:3840,height:2160})),{width:3840,height:2160,duration:2});
for(const options of [{audio:true},{duration:0},{duration:61000},{codec:'hvc1'},{width:1919}])assert.throws(()=>data.videoInfo(movie(options)));
for(const bytes of [Buffer.alloc(0),movie().subarray(0,100),Buffer.concat([movie(),Buffer.from([1])])])assert.throws(()=>data.videoInfo(bytes));
const bad=movie();bad.writeUInt32BE(0,0);assert.throws(()=>data.videoInfo(bad));
// Exercise the real external package through byte verification and receiver envelope assembly.
const entry=require('../../scripts/check-theme-submissions.cjs').loadRegistry().find(e=>e.record.title==='Channel');
const pack={descriptor:new Uint8Array(fs.readFileSync(path.resolve('showcase',entry.base,'cytv-theme.json'))),files:{}};
for(const f of entry.files.filter(f=>f!=='cytv-theme.json'))pack.files[f]=new Uint8Array(fs.readFileSync(path.resolve('showcase',entry.base,f)));
const m=JSON.parse(data.decode(pack.descriptor));m.defaults.wallpaperAssetId=m.previewAssetId;m.requires.capabilities.push('video-wallpaper-v1');m.wallpaperVideo=manifest().wallpaperVideo;
function descriptor(){pack.descriptor=data.encode(JSON.stringify(m));pack.digest=data.hash(pack.descriptor);}
pack.files['wallpaper.mp4']=movie();descriptor();assert.equal(data.verify(pack,'99.0.0').manifest.wallpaperVideo.variants.length,1);
const env={schemaVersion:1,descriptor:Buffer.from(pack.descriptor).toString('base64'),files:{}};for(const key of Object.keys(pack.files))env.files[key]=Buffer.from(pack.files[key]).toString('base64');assert.equal(data.unpackEnvelope(env,'99.0.0').digest,pack.digest);
pack.files['wallpaper.mp4']=movie({width:3840,height:2160});m.wallpaperVideo.variants[0].size=pack.files['wallpaper.mp4'].length;m.wallpaperVideo.variants[0].sha256=data.hash(pack.files['wallpaper.mp4']);descriptor();assert.throws(()=>data.verify(pack,'99.0.0'),/dimensions/);
console.log('PASS video policy, MP4 boundary validation and transport integrity');
module.exports={movie,manifest};
// Media installation creates URLs without touching a native video decoder.
const vm=require('vm');
async function preparation(){
 const entry=require('../../scripts/check-theme-submissions.cjs').loadRegistry().find(e=>e.record.title==='Channel');
 const m=JSON.parse(fs.readFileSync(path.resolve('showcase',entry.base,'cytv-theme.json'),'utf8')),files={};
 for(const f of entry.files.filter(f=>f!=='cytv-theme.json'))files[f]=new Uint8Array(fs.readFileSync(path.resolve('showcase',entry.base,f)));
 m.defaults.wallpaperAssetId=m.previewAssetId;m.requires.capabilities.push('video-wallpaper-v1');
 m.wallpaperVideo={variants:['4k','1080p'].map(quality=>{const width=quality==='4k'?3840:1920,height=quality==='4k'?2160:1080,bytes=movie({width,height}),name=quality+'.mp4';files[name]=bytes;return {quality,path:name,mediaType:'video/mp4',size:bytes.length,sha256:data.hash(bytes),width,height};})};
 const descriptor=data.encode(JSON.stringify(m)),pack={descriptor,digest:data.hash(descriptor),files};
 let sequence=0,cancel=false,mode='',created={},revoked=[],videoCount=0;
 class FakeBlob{constructor(parts,options){this.bytes=parts[0];this.type=options.type;}}
 class Image{set src(url){const b=created[url],info=data.imageInfo(b.bytes,b.type,true);this.naturalWidth=info.width;this.naturalHeight=info.height;Promise.resolve().then(()=>this.onload&&this.onload());}}
 const context={JSON,Uint8Array,ArrayBuffer,DataView,Int32Array,Promise,setTimeout,clearTimeout,ThemePolicy:policy,Blob:FakeBlob,Image,URL:{createObjectURL(blob){if(blob.type==='video/mp4'){videoCount++;if(mode==='error'&&videoCount===2)throw Error('URL failed');if(mode==='cancel')cancel=true;}const url='blob:verified-'+(++sequence);created[url]=blob;return url;},revokeObjectURL(url){revoked.push(url);}}};
 vm.runInNewContext(fs.readFileSync('launcher/theme-data.js','utf8'),context);
 const ready=await context.ThemeData.prepare(pack,'99.0.0');assert.deepEqual(Object.keys(ready.videoHandles),['4k','1080p']);assert.equal(videoCount,2);assert.equal(revoked.length,0);context.ThemeData.dispose(ready.assetHandles,ready.videoHandles);assert.equal(revoked.length,Object.keys(created).length);
 for(const failure of ['error','cancel']){created={};revoked=[];mode=failure;cancel=false;videoCount=0;await assert.rejects(context.ThemeData.prepare(pack,'99.0.0',()=>cancel),failure==='error'?/URL failed/:/Cancelled/);assert.equal(revoked.length,Object.keys(created).length,'release every image/video handle on '+failure);}
 mode='';cancel=false;let leaseDisposals=0,cacheCalls=0;
 context.WallpaperMediaCache={prepare:async(manifest,received,isCancelled)=>{cacheCalls++;assert.equal(received,pack);assert.equal(manifest.id,m.id);assert.equal(isCancelled(),false);return {handles:{'4k':'file:///private/uhd.mp4','1080p':'file:///private/fhd.mp4'},dispose(){leaseDisposals++;}};}};
 const native=await context.ThemeData.prepare(pack,'99.0.0',()=>false);assert.equal(cacheCalls,1);assert.equal(native.videoHandles['4k'],'file:///private/uhd.mp4');assert(native.videoLease);context.ThemeData.dispose(native.assetHandles,native.videoHandles,native.videoLease);assert.equal(leaseDisposals,1);
 context.WallpaperMediaCache.prepare=async()=>{cancel=true;return {handles:{'4k':'file:///private/uhd.mp4'},dispose(){leaseDisposals++;}};};await assert.rejects(context.ThemeData.prepare(pack,'99.0.0',()=>cancel),/Cancelled/);assert.equal(leaseDisposals,2,'cancelled native preparation releases lease');
 console.log('PASS video prepare ownership, no native decoder, failure/cancellation cleanup');
}
preparation().catch(e=>{console.error(e);process.exitCode=1;});
