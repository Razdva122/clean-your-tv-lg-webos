'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const home=require('../../launcher/home-layout.js'),policy=require('../../launcher/theme-policy.js'),compiler=require('../../theme-api/compile.cjs'),fixture=require('./fixtures/valid-manifest.json');
const defaults={left:112,right:112,bottom:162,cardHeight:128,gap:24,skewDeg:0,focusLift:0,iconScale:1,shortcuts:'header',edgeNavigation:'wrap',labels:'below',showClock:true};
const layout=ribbon=>({preset:'scenic-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1,allowColumnOverride:false,ribbon});
const manifest=ribbon=>({...fixture,layout:layout(ribbon),requires:{...fixture.requires,capabilities:['ribbon-layout-v1']}});
const contract=require('../../theme-api/contract.json');
assert.deepEqual(contract.layout.ribbon.defaults,defaults);assert.equal(contract.optionalCapabilities['ribbon-layout-v1'].layout,'ribbon');
assert.deepEqual(home.normalizeRibbon({}),defaults); assert.deepEqual(policy.normalizeRibbon({}),defaults);
const bounds={left:[64,640],right:[32,320],bottom:[0,200],cardHeight:[96,240],gap:[0,64],skewDeg:[-18,18],focusLift:[0,64],iconScale:[.4,1]};
for(const normalize of [home.normalizeRibbon,policy.normalizeRibbon]) {
 for(const [key,[min,max]] of Object.entries(bounds)) {
  for(const value of [min,max])assert.equal(normalize({...(key==='bottom'?{labels:'focused-above'}:{}),[key]:value})[key],value);
  for(const value of [min-1,max+1,NaN,Infinity,'1',null,...(key==='skewDeg'||key==='iconScale'?[]:[min+.5])])assert.throws(()=>normalize({[key]:value}),/layout-invalid/,key+': '+value);
 }
 for(const bad of [{labels:'below',bottom:0},{labels:'below',bottom:63},null,[],true,{unknown:1},{shortcuts:'footer'},{edgeNavigation:'none'},{labels:'none'},{showClock:0},{shortcuts:'bottom-left',left:339}])assert.throws(()=>normalize(bad),/layout-invalid/);
 assert.equal(normalize({labels:'below',bottom:64}).bottom,64);
 assert.equal(normalize({labels:'focused-above',bottom:0}).bottom,0);
 assert.equal(normalize({shortcuts:'bottom-left',left:340,skewDeg:1.5,labels:'focused-above',edgeNavigation:'shortcuts',showClock:false}).showClock,false);
}
assert.deepEqual(home.geometry('scenic-grid',5),{preset:'scenic-grid',left:112,width:1696,maxWidth:128,maxHeight:128,dockTop:790,padding:0,rowGap:100,rowExtra:0,heroOffset:176,scrollTop:760,scrollBottom:1060,dock:false,columnWidth:339.2,cardWidth:128,cardHeight:128,top:790});
assert.equal(home.geometry('dock-grid',5).top,708);
const ribbon={...defaults,left:400,right:80,bottom:64,cardHeight:200,gap:20,skewDeg:-12,focusLift:40};
const g=home.geometry('scenic-grid',5,ribbon),margin=Math.abs(Math.tan(-12*Math.PI/180)*240);
assert.equal(g.left,400+margin);assert.equal(g.width,1440-2*margin);assert.equal(g.columnWidth,g.width/5);assert.equal(g.cardWidth,Math.min(360,g.columnWidth-20));assert.equal(g.top,816);assert.equal(g.cardHeight,200);assert.equal(g.padding,0);assert.equal(g.rowGap,0);assert.equal(g.rowExtra,0);assert.deepEqual(g.ribbon,ribbon);
assert.throws(()=>home.geometry('dock-grid',5,{}),/layout-invalid/);
const tooNarrow={left:640,right:320,skewDeg:18,cardHeight:240,focusLift:64,gap:64};
assert.throws(()=>home.geometry('scenic-grid',8,tooNarrow),/layout-invalid/);
const model=home.create({getItem:()=>null,setItem:()=>{},removeItem:()=>{}},{columns:5});assert.equal(model.supportsRibbonOptions,true);assert.equal(model.state().ribbon,null);
model.setThemeLayout(layout({}));assert.deepEqual(model.state().ribbon,defaults);
for(const bad of [{...layout({}),preset:'icon-grid'},{...layout({}),allowColumnOverride:true},{...layout({}),allowColumnOverride:undefined},layout({gap:65}),{...layout(tooNarrow),columns:8}]){const previous=model.state();assert.throws(()=>model.setThemeLayout(bad),/layout-invalid/);assert.deepEqual(model.state(),previous);}
const snapshot=model.state();snapshot.ribbon.left=999;assert.equal(model.state().ribbon.left,112);
model.setThemeLayout({...layout(undefined),preset:'dock-grid'});assert.equal(model.state().ribbon,null);
assert.deepEqual(policy.validateManifest(manifest({})).layout.ribbon,defaults);
assert.throws(()=>policy.validateManifest(manifest({gap:65})),error=>error.code==='layout-invalid');
for(const bad of [{...manifest({}),requires:{...fixture.requires,capabilities:[]}},{...fixture,requires:{...fixture.requires,capabilities:['ribbon-layout-v1']}},{...manifest({}),layout:{...layout({}),allowColumnOverride:true}},{...manifest({}),requires:{...fixture.requires,capabilities:['ribbon-layout-v1','ribbon-layout-v1']}},{...manifest(tooNarrow),layout:{...layout(tooNarrow),columns:8}}])assert.throws(()=>policy.validateManifest(bad));
for(const capabilities of [['unknown'],['modern-icon-css-v1','ribbon-layout-v1','unknown']])assert.throws(()=>policy.validateManifest({...manifest({}),requires:{...fixture.requires,capabilities}}),error=>error.code==='api-unsupported');
const context=vm.createContext({});vm.runInContext(fs.readFileSync(require.resolve('../../launcher/theme-policy.js'),'utf8'),context);assert.equal(vm.runInContext('ThemePolicy.normalizeRibbon({}).left',context),112);
(async()=>{
const source={manifest:manifest({skewDeg:12,iconScale:.65}),css:'.ctv-card{color:red}',assets:[{id:'preview',path:'preview.png',mediaType:'image/png',data:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=','base64')}],documents:[{path:'LICENSE.txt',data:'MIT'},{path:'CREDITS.txt',data:'Original'}]};
const output=await compiler.compileSource(source);assert.deepEqual(output.manifest.layout.ribbon,{...defaults,skewDeg:12,iconScale:.65});assert.deepEqual(output.manifest.requires.capabilities,['ribbon-layout-v1']);assert.equal(output.manifest.themeApiVersion,1);assert.equal(output.manifest.requires.minimumHomeVersion,'0.0.0');
const both=await compiler.compileSource({...source,css:'.ctv-icon{filter:invert(1)}'});assert.deepEqual(both.manifest.requires.capabilities,['modern-icon-css-v1','ribbon-layout-v1']);policy.validateManifest(both.manifest);
console.log('PASS bounded ribbon options, geometry, compiler and atomic application');
})().catch(error=>{console.error(error);process.exitCode=1;});
