const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
const policy=require('../../launcher/theme-policy.js');
const manifest=require('./fixtures/valid-manifest.json');
const rules={schemaVersion:1,rules:[{selector:[{part:'card',states:[]}],declarations:[{property:'color',value:{type:'color',rgba:[255,0,0,1]}}]}]};
const nodes={}, revoked=[],columns=[];
const surfaceClasses=new Set();
const surface={classList:{add:name=>surfaceClasses.add(name),remove:name=>surfaceClasses.delete(name)}};nodes.homeSurface=surface;
const document={getElementById:id=>nodes[id]||null,createElement:()=>({disabled:false,textContent:'',parentNode:null}),head:{appendChild(node){nodes[node.id]=node;node.parentNode=this;},removeChild(node){delete nodes[node.id];node.parentNode=null;}}};
// The browser policy shares a realm with runtime-created bundles; bridge that VM boundary here.
const runtimePolicy={...policy,compileRules:(bundle,handles)=>policy.compileRules(structuredClone(bundle),handles)};
const context={document,ThemePolicy:runtimePolicy,HomeLayoutState:{setThemeColumns:n=>columns.push(n)},URL:{revokeObjectURL:h=>revoked.push(h)}};
vm.runInNewContext(fs.readFileSync('launcher/theme-runtime.js','utf8'),context);
assert.equal(typeof context.ThemeRuntime.apply,'function','validated runtime apply exists');
assert.equal(surfaceClasses.has('ctv-theme-active'),false);
context.ThemeRuntime.suspend('settings');
context.ThemeRuntime.apply({manifest,rules,assetHandles:{}});
assert.equal(nodes['ctv-theme-style'].disabled,true,'applying while Settings is open stays suspended');
assert(surfaceClasses.has('ctv-theme-active'),'successful application marks the surface active even while suspended');
context.ThemeRuntime.resume('settings');assert.equal(nodes['ctv-theme-style'].disabled,false);
const accepted=nodes['ctv-theme-style'].textContent;
assert.throws(()=>context.ThemeRuntime.apply({manifest,rules:{schemaVersion:1,rules:[{selector:[{part:'body',states:[]}],declarations:[]}]},assetHandles:{}}));
assert.equal(nodes['ctv-theme-style'].textContent,accepted,'invalid theme preserves accepted CSS');
assert(surfaceClasses.has('ctv-theme-active'),'invalid application preserves the accepted active state');
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...manifest,layout:{...manifest.layout,textScale:1.2}},rules,assetHandles:{}}),/layout-invalid/);
context.ThemeRuntime.apply({manifest,rules,assetHandles:{},overrides:{accent:'#abcdef',dim:.4}});
assert.match(nodes['ctv-theme-style'].textContent,/#abcdef/);
const imageRule={selector:[{part:'home',states:[]}],declarations:[{property:'background-image',value:{type:'asset',id:'preview'}}]};
const repeatedImages={schemaVersion:1,rules:Array.from({length:512},()=>structuredClone(imageRule))};
const beforeBudgetCss=nodes['ctv-theme-style'].textContent,beforeBudgetColumns=columns.slice();
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...manifest,layout:{...manifest.layout,columns:8}},rules:repeatedImages,assetHandles:{preview:'data:image/png;base64,'+Buffer.alloc(32768).toString('base64')}}),/css-budget/);
assert.equal(nodes['ctv-theme-style'].textContent,beforeBudgetCss);
assert.deepEqual(columns,beforeBudgetColumns,'budget rejection preserves geometry');
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...manifest,defaults:{...manifest.defaults,wallpaperAssetId:'preview'},layout:{...manifest.layout,columns:8}},rules:{schemaVersion:1,rules:[imageRule,imageRule]},assetHandles:{preview:'data:image/png;base64,'+'A'.repeat(100000)}}),/css-budget/,'wallpaper and rule output share one final stylesheet budget');
assert.equal(nodes['ctv-theme-style'].textContent,beforeBudgetCss);
assert.deepEqual(columns,beforeBudgetColumns);
context.ThemeRuntime.reset();assert.equal(nodes['ctv-theme-style'],undefined);assert.equal(columns.at(-1),5);
assert.equal(surfaceClasses.has('ctv-theme-active'),false,'reset removes the active surface marker');
// Older renderers can keep accepting Classic, but must reject new geometry before mutation.
const previousCss=nodes['ctv-theme-style'],previousColumns=columns.slice();
for (const preset of ['icon-grid','side-grid','channel-list','scenic-grid']) {
 assert.throws(()=>context.ThemeRuntime.apply({manifest:{...manifest,layout:{...manifest.layout,preset}},rules,assetHandles:{}}),/layout-invalid/);
 assert.equal(nodes['ctv-theme-style'],previousCss);
 assert.equal(surfaceClasses.has('ctv-theme-active'),false,'rejected application cannot mark an inactive surface active');
 assert.deepEqual(columns,previousColumns);
}
const layouts=[];
context.HomeLayoutState.setThemeLayout=layout=>layouts.push(structuredClone(layout));
for (const preset of ['dock-grid','icon-grid','side-grid','channel-list','scenic-grid']) {
 const next={...manifest,layout:{...manifest.layout,preset}};
 context.ThemeRuntime.apply({manifest:next,rules,assetHandles:{}});
 assert.deepEqual(layouts.at(-1),next.layout,'runtime forwards the whole validated layout');
 assert.deepEqual(columns,previousColumns,'new renderer does not receive a second columns-only mutation');
}
const beforeInvalidLayout=layouts.length,beforeInvalidCss=nodes['ctv-theme-style'].textContent;
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...manifest,layout:{...manifest.layout,preset:'custom'}},rules,assetHandles:{}}),/layout-invalid/);
assert.equal(layouts.length,beforeInvalidLayout);
assert.equal(nodes['ctv-theme-style'].textContent,beforeInvalidCss);
const hiddenBorder={schemaVersion:1,rules:[{selector:[{part:'card',states:['focused','moving']}],declarations:[
 {property:'border-width',value:{type:'length',value:0,unit:'px'}},
 {property:'border-style',value:{type:'keyword',value:'none'}},
 {property:'border-color',value:{type:'color',rgba:[0,0,0,0]}}
]}]};
context.ThemeRuntime.apply({manifest,rules:hiddenBorder,assetHandles:{},overrides:{accent:'#abcdef'}});
assert.match(nodes['ctv-theme-style'].textContent, /\.ctv-card\.is-focused\{border-color:#abcdef!important;border-style:solid!important;border-width:2px!important;\}$/, 'trusted focus minimum overrides author hidden borders and higher-specificity states');
context.ThemeRuntime.reset();
assert.equal(surfaceClasses.has('ctv-theme-active'),false);
assert.deepEqual(layouts.at(-1),{preset:'dock-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1});
assert.equal(nodes['ctv-theme-style'],undefined);
console.log('Theme runtime checks passed');

const fixed={...manifest,layout:{...manifest.layout,allowColumnOverride:false}};
assert.throws(()=>context.ThemeRuntime.apply({manifest:fixed,rules,assetHandles:{}}),/unsupported column policy/,'older renderer rejects fixed policy before mutation');
assert.equal(nodes['ctv-theme-style'],undefined);
context.HomeLayoutState.supportsColumnPolicy=true;
context.ThemeRuntime.apply({manifest:fixed,rules,assetHandles:{}});
assert.equal(layouts.at(-1).allowColumnOverride,false);
context.ThemeRuntime.reset();
assert.notEqual(layouts.at(-1).allowColumnOverride,false,'Classic restores adjustable columns');

const iconCssRules={schemaVersion:1,rules:[{selector:[{part:'icon',states:['light']}],declarations:[{property:'filter',value:{type:'filter',functions:[{name:'grayscale',amount:1},{name:'invert',amount:1},{name:'brightness',amount:1.3}]}},{property:'mix-blend-mode',value:{type:'keyword',value:'screen'}}]},{selector:[{part:'card',states:['focused']}],declarations:[{property:'border-width',value:{type:'length',value:0,unit:'px'}},{property:'border-style',value:{type:'keyword',value:'none'}}]},{selector:[{part:'card',states:[]}],declarations:[{property:'background-color',value:{type:'color',rgba:[0,0,0,0]}}]}]};
const modernManifest={...structuredClone(manifest),layout:{...manifest.layout,preset:'scenic-grid'},requires:{...manifest.requires,capabilities:['modern-icon-css-v1']}};
context.ThemeRuntime.reset();
assert.throws(()=>context.ThemeRuntime.apply({manifest:modernManifest,rules:iconCssRules,assetHandles:{}}),/modern icon CSS/);
assert.equal(nodes['ctv-theme-style'],undefined,'unsupported browser preserves Classic');
context.CSS={supports:()=>true};
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...modernManifest,requires:{...manifest.requires,capabilities:[]}},rules:iconCssRules,assetHandles:{}}),/capability/);
context.ThemeRuntime.apply({manifest:modernManifest,rules:iconCssRules,assetHandles:{}});
assert.match(nodes['ctv-theme-style'].textContent,/scale\(1.1\)!important/);
assert.match(nodes['ctv-theme-style'].textContent,/background-color:rgba\(0,0,0,0\)!important/);
assert.doesNotMatch(nodes['ctv-theme-style'].textContent,/ctv-label\.is-focused\{color:#fff!important/,'visible hero avoids duplicate selected captions');
const hiddenHeroRules=structuredClone(iconCssRules);hiddenHeroRules.rules.push({selector:[{part:'hero',states:[]}],declarations:[{property:'color',value:{type:'color',rgba:[0,0,0,0]}}]});
context.ThemeRuntime.apply({manifest:modernManifest,rules:hiddenHeroRules,assetHandles:{}});
assert.match(nodes['ctv-theme-style'].textContent,/ctv-label\.is-focused\{color:#fff!important/,'hidden hero keeps a readable selected-caption fallback');
assert.doesNotMatch(nodes['ctv-theme-style'].textContent,/border-width:3px!important/);
context.ThemeRuntime.reset();
console.log('PASS CSS-only icon feature gate, trusted scale focus and background cascade');
const enlargedIcons={schemaVersion:1,rules:[{selector:[{part:'card',states:[]},{part:'icon',states:[]}],declarations:[{property:'transform',value:{type:'scale',amount:1.6}}]}]};
assert.throws(()=>context.ThemeRuntime.apply({manifest:modernManifest,rules:enlargedIcons,assetHandles:{}}),/fixed scenic-grid/,'image enlargement cannot bypass a saved column override');
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...modernManifest,layout:{...modernManifest.layout,columns:8,allowColumnOverride:false}},rules:enlargedIcons,assetHandles:{}}),/fixed scenic-grid/,'eight-column images cannot overlap');
context.ThemeRuntime.apply({manifest:{...modernManifest,layout:{...modernManifest.layout,allowColumnOverride:false}},rules:enlargedIcons,assetHandles:{}});
assert.match(nodes['ctv-theme-style'].textContent,/transform:scale\(1.6\)!important/);
context.ThemeRuntime.reset();
console.log('PASS bounded CSS enlargement, fixed-column guard and trusted icon cascade');
// Runtime-injected rules bypass the static PostCSS build. Model a prefixed-only CSSOM.
document.documentElement={style:{webkitTransform:''}};
context.ThemeRuntime.apply({manifest:{...modernManifest,layout:{...modernManifest.layout,allowColumnOverride:false}},rules:enlargedIcons,assetHandles:{}});
assert.match(nodes['ctv-theme-style'].textContent,/-webkit-transform:scale\(1.6\)!important/);
assert.match(nodes['ctv-theme-style'].textContent,/;transform:scale\(1.6\)!important/,'standard declaration remains for later engines');
const prefixedCss=nodes['ctv-theme-style'].textContent,layoutsBeforePrefixBudget=layouts.length;
context.ThemePolicy={...runtimePolicy,limits:{...policy.limits,emittedCssBytes:prefixedCss.length-1}};
assert.throws(()=>context.ThemeRuntime.apply({manifest:{...modernManifest,layout:{...modernManifest.layout,allowColumnOverride:false}},rules:enlargedIcons,assetHandles:{}}),/css-budget/);
assert.equal(nodes['ctv-theme-style'].textContent,prefixedCss,'prefix expansion cannot exceed the budget or replace accepted styles');
assert.equal(layouts.length,layoutsBeforePrefixBudget,'prefix budget is checked before geometry mutation');
context.ThemePolicy=runtimePolicy;
context.ThemeRuntime.reset();
context.HomeLayoutState.supportsRibbonOptions=true;
const ribbonManifest={...manifest,requires:{...manifest.requires,capabilities:['ribbon-layout-v1']},layout:{...manifest.layout,preset:'scenic-grid',allowColumnOverride:false,ribbon:{skewDeg:-12,shortcuts:'bottom-left',left:400}}};
context.ThemeRuntime.apply({manifest:ribbonManifest,rules,assetHandles:{}});
assert.match(nodes['ctv-theme-style'].textContent,/-webkit-transform:skewX\(-12deg\)!important/);
assert.match(nodes['ctv-theme-style'].textContent,/-webkit-animation:none/);
assert.match(nodes['ctv-theme-style'].textContent,/-webkit-justify-content:center/);
context.ThemeRuntime.reset();
console.log('PASS prefixed runtime theme transforms, animations and flex alignment');
