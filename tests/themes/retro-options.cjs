'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const policy=require('../../launcher/theme-policy.js'),fixture=require('./fixtures/valid-manifest.json');
const manifest=()=>({...structuredClone(fixture),layout:{...fixture.layout,datePlacement:'below-clock',heroCursor:true},requires:{...fixture.requires,capabilities:['retro-decoration-v1']}});
assert.equal(policy.validateManifest(manifest()).layout.datePlacement,'below-clock');
for(const change of [m=>m.requires.capabilities=[],m=>m.layout.datePlacement='absolute',m=>m.layout.heroCursor='yes',m=>m.layout.preset='side-grid']){const m=manifest();change(m);assert.throws(()=>policy.validateManifest(m));}
const nodes={}, document={getElementById:id=>nodes[id]||null,createElement:()=>({}),head:{appendChild(n){nodes[n.id]=n;n.parentNode=this;},removeChild(n){delete nodes[n.id];}}};
const context={document,ThemePolicy:{...policy,compileRules:(b,h)=>policy.compileRules(structuredClone(b),h)}};
vm.runInNewContext(fs.readFileSync('launcher/theme-runtime.js','utf8'),context);
const rules={schemaVersion:1,rules:[]};
context.ThemeRuntime.apply({manifest:manifest(),rules});
assert.match(nodes['ctv-theme-style'].textContent, /#timeRow/);
assert.match(nodes['ctv-theme-style'].textContent, /prefers-reduced-motion/);
assert.match(nodes['ctv-theme-style'].textContent, /ctv-retro-cursor/);
context.ThemeRuntime.suspend('settings');assert.equal(nodes['ctv-theme-style'].disabled,true);
context.ThemeRuntime.resume('settings');assert.equal(nodes['ctv-theme-style'].disabled,false);
context.ThemeRuntime.apply({manifest:fixture,rules});assert.doesNotMatch(nodes['ctv-theme-style'].textContent,/ctv-retro-cursor|#timeRow/);
context.ThemeRuntime.reset();assert.equal(nodes['ctv-theme-style'],undefined);
console.log('PASS optional Retro decorations validation and lifecycle');
(async()=>{
 const compiler=require('../../theme-api/compile.cjs');
 for(const easing of ['steps(0,end)','steps(9,end)','steps(4,start)'])await assert.rejects(()=>compiler.compileThemeCss('.ctv-card{transition:color 120ms '+easing+'}'));
 const compiled=await compiler.compileThemeCss('.ctv-card{transition:color 120ms steps(4,end)}');
 assert.match(compiled.css,/steps\(4,end\)/);
 assert.throws(()=>context.ThemeRuntime.apply({manifest:fixture,rules:compiled.bundle}),/steppedTransitions/);
 const m=manifest();m.layout.steppedTransitions=true;
 context.ThemeRuntime.apply({manifest:m,rules:compiled.bundle});
 const before=nodes['ctv-theme-style'].textContent;
 const bad=manifest();bad.layout.heroCursor='bad';assert.throws(()=>context.ThemeRuntime.apply({manifest:bad,rules}));assert.equal(nodes['ctv-theme-style'].textContent,before);
 const source={manifest:fixture,css:'.ctv-card{transition:color 120ms steps(4,end)}',assets:[{id:'preview',path:'preview.png',mediaType:'image/png',data:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=','base64')}],documents:[{path:'LICENSE.txt',data:'MIT'},{path:'CREDITS.txt',data:'Original'}]};
 const output=await compiler.compileSource(source);assert.equal(output.manifest.layout.steppedTransitions,true);assert.deepEqual(output.manifest.requires.capabilities,['retro-decoration-v1']);
 await assert.rejects(()=>compiler.compileThemeCss('.ctv-card{transition:transform 120ms steps(4,end)}'));
 console.log('PASS bounded stepped transition compile and atomic reject');
})().catch(e=>{console.error(e);process.exitCode=1;});
// Prefixed-only WebKit must resolve the trusted animation as well.
document.documentElement={style:{webkitTransform:''}};
context.ThemeRuntime.apply({manifest:manifest(),rules});
assert.match(nodes['ctv-theme-style'].textContent,/@-webkit-keyframes ctv-retro-cursor/);
assert.match(nodes['ctv-theme-style'].textContent,/-webkit-animation:ctv-retro-cursor/);
