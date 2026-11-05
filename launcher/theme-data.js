/* Data-only theme transport. No updater trust, author scripts or external CSS. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./theme-policy.js'),root);else root.ThemeData=factory(root.ThemePolicy,root);}(this,function(policy,root){
 'use strict';
 function fail(message){throw Error(message);}
 function encode(s){s=unescape(encodeURIComponent(s));var a=new Uint8Array(s.length);for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i);return a;}
 function decode(a){a=new Uint8Array(a);var s='';for(var i=0;i<a.length;i+=8192)s+=String.fromCharCode.apply(null,a.subarray(i,i+8192));return decodeURIComponent(escape(s));}
 function hash(input){
  var a=new Uint8Array(input),len=a.length,bytes=new Uint8Array(((len+9+63)>>6)<<6);bytes.set(a);bytes[len]=128;
  var v=new DataView(bytes.buffer);v.setUint32(bytes.length-8,Math.floor(len/536870912));v.setUint32(bytes.length-4,(len*8)>>>0);
  var h=[1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225];
  var k=[1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298];
  function r(x,n){return (x>>>n)|(x<<(32-n));}
  var w=new Int32Array(64);
  for(var offset=0;offset<bytes.length;offset+=64){var i;for(i=0;i<16;i++)w[i]=v.getInt32(offset+i*4);for(i=16;i<64;i++){var x=w[i-15],y=w[i-2];w[i]=((r(x,7)^r(x,18)^(x>>>3))+w[i-16]+(r(y,17)^r(y,19)^(y>>>10))+w[i-7])|0;}
   var aa=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
   for(i=0;i<64;i++){var t1=(hh+(r(e,6)^r(e,11)^r(e,25))+((e&f)^(~e&g))+k[i]+w[i])|0,t2=((r(aa,2)^r(aa,13)^r(aa,22))+((aa&b)^(aa&c)^(b&c)))|0;hh=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=aa;aa=(t1+t2)|0;}
   [aa,b,c,d,e,f,g,hh].forEach(function(n,index){h[index]=(h[index]+n)|0;});
  }
  return h.map(function(n){return ('00000000'+(n>>>0).toString(16)).slice(-8);}).join('');
 }
 function path(s){if(typeof s!=='string'||s.length>240||! /^[A-Za-z0-9_-]+(?:[./-][A-Za-z0-9_-]+)*$/.test(s)||s.split('/').some(function(p){return p==='.'||p==='..';}))fail('Unsafe theme path');return s;}
 function source(url,distributionPath){
  if(typeof url!=='string'||url.length>1000)fail('Use a public GitHub repository or a commit-pinned theme descriptor');url=url.trim();
  var repo=/^https:\/\/github\.com\/([A-Za-z0-9-]+)\/([A-Za-z0-9_.-]+)\/?$/.exec(url);
  if(repo&&(repo[2]==='.'||repo[2]==='..'))fail('Invalid repository');
  if(repo)return {repository:('https://github.com/'+repo[1]+'/'+repo[2]).toLowerCase(),owner:repo[1].toLowerCase(),repo:repo[2].toLowerCase()};
  var raw=/^https:\/\/raw\.githubusercontent\.com\/([A-Za-z0-9-]+)\/([A-Za-z0-9_.-]+)\/([a-f0-9]{40})\/(.+)$/.exec(url);
  if(!raw)fail('Use a public GitHub repository or a commit-pinned theme descriptor');path(raw[4]);
  if(!distributionPath&&!/(^|\/)cytv-theme(?:s)?\.json$/.test(raw[4]))fail('Expected cytv-theme.json or cytv-themes.json');
  return {repository:('https://github.com/'+raw[1]+'/'+raw[2]).toLowerCase(),owner:raw[1].toLowerCase(),repo:raw[2].toLowerCase(),commit:raw[3],path:raw[4]};
 }
 function versionAtLeast(actual,required){
  var pattern=/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
  var a=pattern.exec(actual),b=pattern.exec(required);if(!a||!b)return false;
  function numeric(x,y){x=x.replace(/^0+(?=\d)/,'');y=y.replace(/^0+(?=\d)/,'');return x.length!==y.length?(x.length>y.length?1:-1):x===y?0:x>y?1:-1;}
  for(var i=1;i<=3;i++){var n=numeric(a[i],b[i]);if(n)return n>0;}
  if(!a[4]||!b[4])return !a[4];var aa=a[4].split('.'),bb=b[4].split('.');
  for(i=0;i<Math.min(aa.length,bb.length);i++){if(aa[i]===bb[i])continue;var an=/^\d+$/.test(aa[i]),bn=/^\d+$/.test(bb[i]);if(an&&bn){n=numeric(aa[i],bb[i]);if(n)return n>0;}else if(an!==bn)return !an;else return aa[i]>bb[i];}return aa.length>=bb.length;
 }

 function request(url,limit,local,signal,deadline){return new Promise(function(resolve,reject){
  if(local!==true&&!/^https:\/\/(raw\.githubusercontent\.com|api\.github\.com)\//.test(url)&&!/^https:\/\/da\.gd\/coshorten\/[A-Za-z0-9_]{5,30}$/.test(url))return reject(Error('Unsupported theme host'));
  var x=new XMLHttpRequest(),done=false;function finish(error){if(done)return;done=true;if(signal)signal.cancel=null;if(error)reject(error);else resolve(new Uint8Array(x.response));}
  x.open('GET',url,true);x.responseType='arraybuffer';x.timeout=deadline?Math.max(1,Math.min(15000,deadline-Date.now())):15000;
  if(signal){if(signal.cancelled)return reject(Error('Cancelled'));signal.cancel=function(){x.abort();};}
  x.onprogress=function(e){if(e.loaded>limit||e.lengthComputable&&e.total>limit){finish(Error('Theme file exceeds its size limit'));x.abort();}};
  x.onload=function(){if(!((local===true&&x.status===0)||x.status===200)){var error=Error(x.status===404?'Theme file not found':'Could not download theme');error.status=x.status;return finish(error);}if(!x.response||x.response.byteLength>limit)return finish(Error('Theme file exceeds its size limit'));if(local!==true&&x.responseURL&&x.responseURL!==url)return finish(Error('Theme redirects are not accepted'));finish();};
  x.onerror=function(){finish(Error('Theme network error'));};x.ontimeout=function(){finish(Error('Theme download timed out'));};x.onabort=function(){finish(Error('Cancelled'));};x.send();
 });}
 function base64(value,limit){
  if(typeof value!=='string'||value.length>4*Math.ceil(limit/3)||value.length%4!==0||/[^A-Za-z0-9+/=]/.test(value)||/=[^=]|={3}/.test(value))fail('Invalid local theme data');
  var raw=atob(value);if(raw.length>limit)fail('Theme file exceeds its size limit');var bytes=new Uint8Array(raw.length);for(var i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);return bytes;
 }
 function unpackEnvelope(envelope,homeVersion){
  if(!envelope||envelope.schemaVersion!==1||!envelope.files||Array.isArray(envelope.files)||typeof envelope.files!=='object')fail('Invalid local theme package');
  var descriptor=base64(envelope.descriptor,65536),m=policy.validateManifest(JSON.parse(decode(descriptor)));
  if(m.id.indexOf('github:')!==0)fail('Local development requires an external theme identity');
  var files=filesFor(m),pack={descriptor:descriptor,digest:hash(descriptor),files:Object.create(null)};
  if(Object.keys(envelope.files).length!==files.length)fail('Unexpected local theme files');
  files.forEach(function(f){pack.files[path(f.path)]=base64(envelope.files[f.path],f.size);});
  verify(pack,homeVersion);return pack;
 }

 function filesFor(m){return [m.rules].concat(m.assets,m.documents,m.wallpaperVideo?m.wallpaperVideo.variants:[]);}
 function raw(s,p){return 'https://raw.githubusercontent.com/'+s.owner+'/'+s.repo+'/'+s.commit+'/'+path(p);}
 function shortLink(value){if(typeof value!=='string'||value.length>1000)return null;var match=/^(?:(?:https:\/\/)?da\.gd\/)?([A-Za-z0-9_]{5,30})$/i.exec(value.trim());return match?'https://da.gd/'+match[1]:null;}
 function expandLink(url,signal){return Promise.resolve().then(function(){
  if(typeof url!=='string')fail('Use a public GitHub repository or a commit-pinned theme descriptor');
  var short=shortLink(url);
  if(!short)return url;
  return request('https://da.gd/coshorten/'+short.slice(short.lastIndexOf('/')+1),4096,false,signal).then(function(bytes){
   var target=decode(bytes).trim();source(target);return target;
  });
 });}
 function resolve(url,signal){return expandLink(url,signal).then(function(url){var s=source(url);var revision=s.commit?Promise.resolve():request('https://api.github.com/repos/'+s.owner+'/'+s.repo+'/commits/HEAD',65536,false,signal).then(function(a){var r=JSON.parse(decode(a));if(!/^[a-f0-9]{40}$/.test(r.sha))fail('Invalid GitHub revision');s.commit=r.sha;});
  return revision.then(function(){var p=s.path||'cytv-themes.json';return request(raw(s,p),65536,false,signal).catch(function(e){if(s.path||e.status!==404)throw e;p='cytv-theme.json';return request(raw(s,p),65536,false,signal);}).then(function(a){var m=JSON.parse(decode(a));if(/cytv-themes\.json$/.test(p)){m=policy.validateCollection(m);if(m.repository.toLowerCase()!==s.repository)fail('Collection repository mismatch');var dir=p.slice(0,p.lastIndexOf('/')+1);return m.themes.map(function(t){return {title:t.title,id:t.id,version:t.themeVersion,url:raw(s,dir+t.path),digest:t.sha256,repository:s.repository};});}
   m=policy.validateManifest(m);if(m.id.indexOf('github:')!==0||m.source.repository.toLowerCase()!==s.repository)fail('Theme repository mismatch');return [{title:m.title,id:m.id,version:m.themeVersion,url:raw(s,p),digest:hash(a),repository:s.repository}];});});
 });}
 function imageInfo(a,type,wallpaper){
  var maxWidth=wallpaper?3840:1920,maxHeight=wallpaper?2160:1080;
  a=new Uint8Array(a);var v=new DataView(a.buffer,a.byteOffset,a.byteLength),w,h,i,n,kind;function str(at,count){return String.fromCharCode.apply(null,a.subarray(at,at+count));}
  if(type==='image/png'){
   if(a.length<45||str(1,3)!=='PNG'||a[0]!==137||a[4]!==13||a[5]!==10||a[6]!==26||a[7]!==10)fail('Invalid PNG');i=8;var ended=false,hasData=false;
   while(i+12<=a.length){n=v.getUint32(i);kind=str(i+4,4);if(n>a.length-i-12)fail('Invalid PNG chunk');if(i===8){if(kind!=='IHDR'||n!==13)fail('Invalid PNG header');w=v.getUint32(i+8);h=v.getUint32(i+12);}if(kind==='acTL')fail('Animated images are not supported');if(kind==='IDAT')hasData=true;i+=n+12;if(kind==='IEND'){ended=n===0;break;}}
   if(!ended||!hasData||i!==a.length)fail('Invalid PNG structure');
  }else if(type==='image/jpeg'){
   if(a.length<4||a[0]!==255||a[1]!==216||a[a.length-2]!==255||a[a.length-1]!==217)fail('Invalid JPEG');i=2;
   while(i+4<=a.length){if(a[i++]!==255)fail('Invalid JPEG marker');while(a[i]===255)i++;kind=a[i++];if(kind===218)break;n=v.getUint16(i);if(n<2||i+n>a.length)fail('Invalid JPEG segment');if([192,193,194].indexOf(kind)>=0){if(n<8)fail('Invalid JPEG frame');h=v.getUint16(i+3);w=v.getUint16(i+5);if(w>maxWidth||h>maxHeight)fail('Image dimensions exceed limits');}i+=n;}
  }else if(type==='image/webp'){
   if(a.length<30||str(0,4)!=='RIFF'||str(8,4)!=='WEBP'||v.getUint32(4,true)+8!==a.length)fail('Invalid WebP');kind=str(12,4);
   if(kind==='VP8X'){if(a[20]&2)fail('Animated images are not supported');w=1+a[24]+(a[25]<<8)+(a[26]<<16);h=1+a[27]+(a[28]<<8)+(a[29]<<16);var at=30,frame=false;while(at+8<=a.length){var chunk=str(at,4),size=v.getUint32(at+4,true),fw=null,fh=null;if(size>a.length-at-8)fail('Invalid WebP chunk');if(chunk==='ANIM'||chunk==='ANMF')fail('Animated images are not supported');if(chunk==='VP8 '){if(size<10||str(at+11,3)!=='\x9d\x01\x2a')fail('Invalid WebP frame');fw=v.getUint16(at+14,true)&16383;fh=v.getUint16(at+16,true)&16383;}else if(chunk==='VP8L'){if(size<5||a[at+8]!==47)fail('Invalid WebP frame');var lossless=v.getUint32(at+9,true);fw=(lossless&16383)+1;fh=((lossless>>>14)&16383)+1;}if(fw!==null){if(frame||fw!==w||fh!==h)fail('WebP canvas/frame dimensions mismatch');frame=true;}at+=8+size+(size%2);}if(!frame||at!==a.length)fail('Invalid WebP structure');}
   else if(kind==='VP8 '){if(str(23,3)!=='\x9d\x01\x2a')fail('Invalid WebP frame');w=v.getUint16(26,true)&16383;h=v.getUint16(28,true)&16383;}
   else if(kind==='VP8L'){if(a[20]!==47)fail('Invalid WebP frame');var bits=v.getUint32(21,true);w=(bits&16383)+1;h=((bits>>>14)&16383)+1;}else fail('Invalid WebP frame');
  }else fail('Unsupported image type');
  if(!w||!h||w>maxWidth||h>maxHeight)fail('Image dimensions exceed limits');return {width:w,height:h};
 }
 // Parse only bounded ISO BMFF metadata. Never instantiate a native media decoder at install.
 function videoInfo(input){
  var a=new Uint8Array(input),v=new DataView(a.buffer,a.byteOffset,a.byteLength),boxes=0,metadata=0;
  function invalid(){fail('Invalid MP4 video metadata');}
  function u32(at,end){if(at<0||at+4>end)invalid();return v.getUint32(at);}
  function str(at){return String.fromCharCode(a[at],a[at+1],a[at+2],a[at+3]);}
  function children(start,end){var out=[];while(start<end){if(++boxes>2048||start+8>end)invalid();var size=u32(start,end),header=8,type=str(start+4);if(size===1){if(start+16>end||u32(start+8,end)!==0)invalid();size=u32(start+12,end);header=16;}if(size<header||size>end-start)invalid();out.push({type:type,start:start+header,end:start+size});start+=size;}return out;}
  function one(items,type){var found=items.filter(function(b){return b.type===type;});if(found.length!==1)invalid();return found[0];}
  function duration(b){var at=b.start,version=a[at],scale,ticks;if(version===0){if(b.end-at<20)invalid();scale=u32(at+12,b.end);ticks=u32(at+16,b.end);}else if(version===1){if(b.end-at<32)invalid();scale=u32(at+20,b.end);var hi=u32(at+24,b.end),lo=u32(at+28,b.end);if(hi>2097151)invalid();ticks=hi*4294967296+lo;}else invalid();var seconds=ticks/scale;if(!scale||!isFinite(seconds)||seconds<1||seconds>60)invalid();return seconds;}
  if(a.length>policy.limits.videoUhdBytes)invalid();
  var top=children(0,a.length),ftyp=one(top,'ftyp'),moov=one(top,'moov');
  if(ftyp.end-ftyp.start<8||(ftyp.end-ftyp.start)%4||top[0]!==ftyp||!top.some(function(b){return b.type==='mdat'&&b.end>b.start;}))invalid();
  top.forEach(function(b){if(['ftyp','moov','mdat','free','skip','wide'].indexOf(b.type)<0)invalid();if(b.type!=='mdat')metadata+=b.end-b.start;});if(metadata>262144)invalid();
  var movie=children(moov.start,moov.end),seconds=duration(one(movie,'mvhd')),tracks=movie.filter(function(b){return b.type==='trak';});if(tracks.length!==1)invalid();
  var track=children(tracks[0].start,tracks[0].end),tkhd=one(track,'tkhd'),mdia=one(track,'mdia');
  var tk=tkhd.start,offset=a[tk]===0?76:a[tk]===1?88:-1;if(offset<0||tkhd.end-tk<offset+8)invalid();
  var width=u32(tk+offset,tkhd.end)/65536,height=u32(tk+offset+4,tkhd.end)/65536;
  if(!((width===1920&&height===1080)||(width===3840&&height===2160)))invalid();
  var media=children(mdia.start,mdia.end),handler=one(media,'hdlr');if(handler.end-handler.start<12||str(handler.start+8)!=='vide')invalid();
  var mediaSeconds=duration(one(media,'mdhd'));if(Math.abs(mediaSeconds-seconds)>.1)invalid();
  var minf=one(media,'minf'),stbl=one(children(minf.start,minf.end),'stbl'),stsd=one(children(stbl.start,stbl.end),'stsd');
  if(stsd.end-stsd.start<8||u32(stsd.start,stsd.end)!==0||u32(stsd.start+4,stsd.end)!==1)invalid();
  var samples=children(stsd.start+8,stsd.end),sample=one(samples,'avc1');if(samples.length!==1||sample.end-sample.start<78)invalid();
  if(v.getUint16(sample.start+24)!==width||v.getUint16(sample.start+26)!==height)invalid();
  var avcc=one(children(sample.start+78,sample.end),'avcC'),at=avcc.start,end=avcc.end;
  if(end-at<7||a[at]!==1||(a[at+4]&252)!==252||(a[at+4]&3)===2||(a[at+5]&224)!==224)invalid();
  function spsDimensions(start,size){
   function bad(){fail('Invalid H.264 SPS dimensions');}
   if(size<5||size>4096||(a[start]&128)||!(a[start]&96))bad();
   var rbsp=[],zeros=0,i,b;
   for(i=start+1;i<start+size;i++){b=a[i];if(zeros>=2){if(b===3){if(i+1>=start+size||a[i+1]>3)bad();zeros=0;continue;}if(b<3)bad();}rbsp.push(b);zeros=b===0?zeros+1:0;}
   var position=0;
   function bits(count){if(position+count>rbsp.length*8)bad();var value=0;while(count--){value=value*2+((rbsp[position>>3]>>(7-(position&7)))&1);position++;}return value;}
   function ue(max){var leading=0;while(!bits(1)){if(++leading>31)bad();}var value=Math.pow(2,leading)-1+bits(leading);if(value>max)bad();return value;}
   function se(){var value=ue(4294967294);return value%2?(value+1)/2:-value/2;}
   var profile=bits(8),constraints=bits(8),level=bits(8),chroma=1,separate=0;
   if((constraints&3)||profile!==a[avcc.start+1]||constraints!==a[avcc.start+2]||level!==a[avcc.start+3])bad();
   ue(31); // seq_parameter_set_id
   if([100,110,122,244,44,83,86,118,128,138,139,134,135].indexOf(profile)>=0){
    chroma=ue(3);if(chroma===3)separate=bits(1);ue(6);ue(6);bits(1);
    if(bits(1))for(i=0;i<(chroma===3?12:8);i++){if(bits(1)){var last=8,next=8;for(var j=0;j<(i<6?16:64);j++){if(next){var delta=se();if(delta< -128||delta>127)bad();next=(last+delta+256)%256;}if(next)last=next;}}}
   }else if([66,77,88].indexOf(profile)<0)bad();
   ue(12);var order=ue(2);if(order===0)ue(12);else if(order===1){bits(1);se();se();var cycle=ue(255);while(cycle--)se();}
   ue(16);bits(1);var columns=ue(239)+1,rows=ue(135)+1,frameOnly=bits(1);if(!frameOnly)bits(1);bits(1);
   var left=0,right=0,top=0,bottom=0;if(bits(1)){left=ue(3840);right=ue(3840);top=ue(2160);bottom=ue(2160);}bits(1); // VUI follows the dimensions; native playback validates its decode support.
   var arrayType=separate?0:chroma,cropX=arrayType===1||arrayType===2?2:1,cropY=(arrayType===1?2:1)*(2-frameOnly),codedWidth=columns*16,codedHeight=rows*16*(2-frameOnly);
   if(codedWidth>Math.ceil(width/16)*16||codedHeight>Math.ceil(height/(16*(2-frameOnly)))*16*(2-frameOnly)||codedWidth-cropX*(left+right)!==width||codedHeight-cropY*(top+bottom)!==height)bad();
  }
  var count=a[at+5]&31;at+=6;if(!count)invalid();
  function nal(kind){if(at+2>end)invalid();var n=v.getUint16(at);at+=2;if(!n||at+n>end||(a[at]&31)!==kind)invalid();if(kind===7)spsDimensions(at,n);at+=n;}
  while(count--)nal(7);if(at>=end)invalid();count=a[at++];if(!count)invalid();while(count--)nal(8);
  // High-profile avcC may include the standard chroma/bit-depth extension.
  if(at<end){if([100,110,122,144].indexOf(a[avcc.start+1])<0||end-at<4||(a[at]&252)!==252||(a[at+1]&248)!==248||(a[at+2]&248)!==248)invalid();count=a[at+3];at+=4;while(count--)nal(13);}
  if(at!==end)invalid();
  return {width:width,height:height,duration:seconds};
 }
 function verify(pack,homeVersion,appearanceOnly){
  if(!pack||!(pack.descriptor instanceof Uint8Array||pack.descriptor instanceof ArrayBuffer))fail('Invalid cached theme');
  var descriptor=new Uint8Array(pack.descriptor);if(descriptor.length>65536||hash(descriptor)!==pack.digest)fail('Descriptor hash mismatch');
  var m=policy.validateManifest(JSON.parse(decode(descriptor)));if(!versionAtLeast(homeVersion,m.requires.minimumHomeVersion))fail('Update Home before installing this theme');
  if(m.layout.spacingScale!==1||m.layout.textScale!==1||m.layout.focusScale!==1.1)fail('Unsupported layout scales');
  var files=filesFor(m),total=descriptor.length,videoPaths=(m.wallpaperVideo?m.wallpaperVideo.variants:[]).map(function(f){return f.path;});
  if(!pack.files||Object.keys(pack.files).some(function(key){return !files.some(function(f){return f.path===key;});})||appearanceOnly!==true&&Object.keys(pack.files).length!==files.length)fail('Unexpected cached theme files');
  files.forEach(function(f){path(f.path);total+=f.size;if(appearanceOnly===true&&videoPaths.indexOf(f.path)>=0)return;var a=pack.files[f.path];if(!a)fail('Theme file missing');a=new Uint8Array(a);if(a.length!==f.size||hash(a)!==f.sha256)fail('Theme file hash mismatch');});
  if(total>policy.limits.packageBytes)fail('Theme package exceeds limits');
  m.assets.forEach(function(f){var info=imageInfo(pack.files[f.path],f.mediaType,f.id===m.defaults.wallpaperAssetId);if(info.width!==f.width||info.height!==f.height)fail('Image dimensions do not match descriptor');});
  if(m.wallpaperVideo&&appearanceOnly!==true)m.wallpaperVideo.variants.forEach(function(f){var info=videoInfo(pack.files[f.path]);if(info.width!==f.width||info.height!==f.height)fail('Video dimensions do not match descriptor');});
  var rules=policy.validateRules(JSON.parse(decode(pack.files[m.rules.path])));return {manifest:m,rules:rules,size:total};
 }
 function load(entry,homeVersion,signal,progress,local,appearanceOnly){
  var started=Date.now(),origin=local===true?null:source(entry.url,true);return request(entry.url,65536,local,signal,started+60000).then(function(a){if(entry.digest&&hash(a)!==entry.digest)fail('Descriptor hash mismatch');var m=policy.validateManifest(JSON.parse(decode(a)));if(entry.id&&m.id!==entry.id||entry.version&&m.themeVersion!==entry.version||entry.title&&entry.title!==m.title)fail('Theme identity/version mismatch');if(local!==true&&(m.id.indexOf('github:')!==0||m.source.repository.toLowerCase()!==origin.repository))fail('Theme repository mismatch');if(!versionAtLeast(homeVersion,m.requires.minimumHomeVersion))fail('Update Home before installing this theme');
   var pack={digest:hash(a),descriptor:a,files:Object.create(null),url:entry.url},files=appearanceOnly===true?[m.rules].concat(m.assets,m.documents):filesFor(m),chain=Promise.resolve();
   // Only startup uses a partial package. Its optional media remains unverified
   // until the lease fetches and verifies the complete package before use.
   if(appearanceOnly===true&&m.wallpaperVideo)pack.loadVideos=function(mediaSignal){var chain=Promise.resolve(),deadline=Date.now()+60000;m.wallpaperVideo.variants.forEach(function(f){chain=chain.then(function(){if(mediaSignal.cancelled)fail('Cancelled');if(Date.now()>deadline)fail('Theme download timed out');return request(entry.url.slice(0,entry.url.lastIndexOf('/')+1)+path(f.path),f.size,local,mediaSignal,deadline).then(function(bytes){if(bytes.length!==f.size||hash(bytes)!==f.sha256)fail('Theme file hash mismatch');pack.files[f.path]=bytes;});});});return chain;};
   files.forEach(function(f,index){chain=chain.then(function(){if(Date.now()-started>60000)fail('Theme download timed out');if(progress)progress(index+1,files.length);var base=entry.url.slice(0,entry.url.lastIndexOf('/')+1);return request(base+path(f.path),f.size,local,signal,started+60000).then(function(bytes){if(bytes.length!==f.size||hash(bytes)!==f.sha256)fail('Theme file hash mismatch');pack.files[f.path]=bytes;});});});
   return chain.then(function(){verify(pack,homeVersion,appearanceOnly);return pack;});
  });
 }
 function deferredVideoLease(pack,parsed,homeVersion,cancelled){
  var disposed=false,generation=0,owned=null,pending=null,signal=null;
  function release(){generation++;if(signal){signal.cancelled=true;if(signal.cancel)signal.cancel();signal=null;}pending=null;var previous=owned;owned=null;if(previous)return Promise.resolve(previous.dispose());return Promise.resolve();}
  function acquire(){
   if(disposed||cancelled&&cancelled())return Promise.reject(Error('Cancelled'));
   if(owned)return owned.acquire();if(pending)return pending;
   var token=++generation,mediaSignal={cancelled:false},candidate=null;signal=mediaSignal;
   function check(){if(disposed||generation!==token||mediaSignal.cancelled||cancelled&&cancelled())fail('Cancelled');}
   var operation=Promise.resolve().then(function(){check();return pack.loadVideos?pack.loadVideos(mediaSignal):null;}).then(function(){
    check();verify(pack,homeVersion);check();
    if(root.WallpaperMediaCache)return root.WallpaperMediaCache.prepare(parsed.manifest,pack,function(){return mediaSignal.cancelled;});
    var handles={};candidate={acquire:function(){return Promise.resolve(handles);},dispose:function(){Object.keys(handles).forEach(function(q){URL.revokeObjectURL(handles[q]);});handles={};}};
    parsed.manifest.wallpaperVideo.variants.forEach(function(f){check();handles[f.quality]=URL.createObjectURL(new Blob([pack.files[f.path]],{type:f.mediaType}));});return candidate;
   }).then(function(value){candidate=value;check();return candidate.acquire();}).then(function(handles){check();owned=candidate;candidate=null;return handles;}).catch(function(error){if(candidate)candidate.dispose();throw error;});
   pending=operation;operation.then(function(){if(pending===operation){pending=null;signal=null;}},function(){if(pending===operation){pending=null;signal=null;}});return operation;
  }
  return {handles:{},acquire:acquire,release:release,dispose:function(){disposed=true;return release();}};
 }
 function prepare(pack,homeVersion,cancelled,appearanceOnly){var parsed=verify(pack,homeVersion,appearanceOnly),handles=Object.create(null),videos=Object.create(null),lease=null,chain=Promise.resolve();
  parsed.manifest.assets.forEach(function(f){chain=chain.then(function(){if(cancelled&&cancelled())throw Error('Cancelled');return new Promise(function(resolve,reject){var url=URL.createObjectURL(new Blob([pack.files[f.path]],{type:f.mediaType})),im=new Image(),timer=setTimeout(function(){finish(Error('Theme image decode timed out'));},8000),done=false;handles[f.id]=url;
   function finish(e){if(done)return;done=true;clearTimeout(timer);im.onload=im.onerror=null;if(e)reject(e);else resolve();}
   im.onload=function(){if(cancelled&&cancelled())return finish(Error('Cancelled'));finish(im.naturalWidth===f.width&&im.naturalHeight===f.height?null:Error('Theme image dimensions mismatch'));};im.onerror=function(){finish(Error('Could not decode theme image'));};im.src=url;
  });});});
  return chain.then(function(){
   if(cancelled&&cancelled())throw Error('Cancelled');
   if(!parsed.manifest.wallpaperVideo)return;
   if(appearanceOnly===true){lease=deferredVideoLease(pack,parsed,homeVersion,cancelled);return;}
   if(root.WallpaperMediaCache)return root.WallpaperMediaCache.prepare(parsed.manifest,pack,cancelled).then(function(result){lease=result;videos=result.handles;});
   parsed.manifest.wallpaperVideo.variants.forEach(function(f){if(cancelled&&cancelled())throw Error('Cancelled');videos[f.quality]=URL.createObjectURL(new Blob([pack.files[f.path]],{type:f.mediaType}));});
  }).then(function(){if(cancelled&&cancelled())throw Error('Cancelled');return {manifest:parsed.manifest,rules:parsed.rules,assetHandles:handles,videoHandles:videos,videoLease:lease};}).catch(function(e){dispose(handles,videos,lease);throw e;});
 }
 function dispose(handles,videos,lease){[handles,videos].forEach(function(map){Object.keys(map||{}).forEach(function(k){if(!lease||map===handles)URL.revokeObjectURL(map[k]);});});if(lease&&typeof lease.dispose==='function')lease.dispose();}

 return {shortLink:shortLink,unpackEnvelope:unpackEnvelope,encode:encode,decode:decode,hash:hash,path:path,source:source,resolve:resolve,request:request,load:load,verify:verify,prepare:prepare,dispose:dispose,imageInfo:imageInfo,videoInfo:videoInfo,versionAtLeast:versionAtLeast};
}));
