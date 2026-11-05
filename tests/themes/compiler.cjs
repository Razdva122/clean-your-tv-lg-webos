const assert=require('node:assert/strict');
const fs=require('node:fs');
assert.ok(fs.existsSync('theme-api/compile.cjs'),'author CSS compiler exists');
const c=require('../../theme-api/compile.cjs');
const p=require('../../launcher/theme-policy.js');
(async()=>{
 for (const part of ['input-icon','network-icon','settings-icon']) {
  const out=await c.compileThemeCss('.ctv-'+part+'{color:transparent;background-image:url(icon.png)}',{assets:[{id:'glyph',path:'icon.png',mediaType:'image/png',data:Buffer.from([1])}]});
  assert.match(out.css,new RegExp('ctv-'+part));
 }
 let expansion=':root{--v0:red;';
 for(let i=1;i<=10;i++)expansion+='--v'+i+':'+('var(--v'+(i-1)+')').repeat(10)+';';
 expansion+='}.ctv-card{color:var(--v10)}';
 const child=require('node:child_process').spawnSync(process.execPath,['-e',
  'require('+JSON.stringify(require.resolve('../../theme-api/compile.cjs'))+').compileThemeCss('+JSON.stringify(expansion)+').then(()=>process.exit(2),e=>{if(e.code!=="css-budget")process.exit(3)})'],{timeout:1500,encoding:'utf8'});
 assert.equal(child.status,0,'exponential variables reject css-budget before child deadline: '+(child.error||child.stderr));
 const out=await c.compileThemeCss(':root { --accent: #123456; } .ctv-card.is-focused { background-color:var(--accent); border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.5); }');
 assert.match(p.compileRules(out.bundle,{}),/rgba\(18,52,86,1\)/);
 assert.match(out.css,/border-radius:12px/);
 const families=await c.compileThemeCss('.ctv-clock{color:#12345680;font-family:sans-serif;font-weight:500;font-style:italic;text-transform:uppercase;text-decoration:underline;letter-spacing:1px;text-shadow:0 2px 8px black;transition:color 200ms ease;} .ctv-card{border-color:rgba(1,2,3,.5);border-width:2px;border-style:solid;background-image:linear-gradient(180deg,#000 0%,#123456 100%);}');
 assert.match(families.css,/text-shadow:0px 2px 8px rgba/);
 assert.match(families.css,/linear-gradient/);
 await assert.rejects(()=>c.compileThemeCss('.ctv-card{'),/css-value/);
 await assert.rejects(()=>require('../../scripts/compile-tv-web.cjs').stylesheet('.x{text-decoration:underline wavy red}','theme.css'),/unsupported CSS/);
 for(const css of ['body{color:red}', '.ctv-card{position:fixed}', '@import "https://x/a.css";', '.ctv-card{color:red!important}', '.ctv-card{background-image:url(https://evil/x.png)}', '.ctv-card{background-image:u\\72l(https://evil/x.png)}', ':root{--x:url(https://evil/x)}.ctv-card{background-image:var(--x)}', '.ctv-card + body{color:red}', '.ctv-card:hover{color:red}', '.ctv-card{box-shadow:0 0 9999px red}']) {
   await assert.rejects(()=>c.compileThemeCss(css),undefined,css);
 }
 const imageStyles=await c.compileThemeCss('.ctv-home{background-image:url(preview.png)}'.repeat(512),{assets:[{id:'preview',path:'preview.png',mediaType:'image/png',data:Buffer.alloc(32768)}]});
 assert(imageStyles.css.length<=p.limits.emittedCssBytes,'host compatibility input is bounded');
 assert.match(imageStyles.css,/data:image\/png;base64,AA==/,'host syntax checks use a small trusted handle');
 assert.deepEqual((await c.compileThemeCss('.ctv-card{color:red}')).bundle,(await c.compileThemeCss('.ctv-card{color:red}')).bundle);

 const manifest=require('./fixtures/valid-manifest.json');
 const source={manifest,css:'.ctv-card{color:red}',source:manifest.source,assets:[{id:'preview',path:'preview.png',mediaType:'image/png',width:1,height:1,data:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=','base64')}],documents:[{path:'LICENSE.txt',data:'MIT'},{path:'CREDITS.txt',data:'Original'}]};
 const first=await c.compileSource(source);const second=await c.compileSource(source);
 assert.equal(first.report.manifestSha256,second.report.manifestSha256);
 assert.equal(first.manifest.rules.sha256,require('node:crypto').createHash('sha256').update(JSON.stringify(first.rules)+'\n').digest('hex'));
 await assert.rejects(()=>c.compileSource({...source,assets:[{...source.assets[0],width:1920}]}),/asset-invalid/);
 await assert.rejects(()=>c.compileSource({...source,assets:[{...source.assets[0],data:Buffer.from('<script>bad</script>')}]}),/asset-invalid/);
 const video=fs.readFileSync('tests/themes/fixtures/wallpaper-blue.mp4');
 const videoSource={...source,manifest:{...manifest,defaults:{...manifest.defaults,wallpaperAssetId:'preview'},wallpaperVideo:{variants:[{quality:'1080p',path:'assets/movie.mp4'}]}},videos:[{quality:'1080p',path:'assets/movie.mp4',data:video}]};
 const animated=await c.compileSource(videoSource);
 assert(animated.manifest.requires.capabilities.includes('video-wallpaper-v1'));
 assert.equal(animated.videos[0].data.length,video.length);
 assert.equal(animated.manifest.wallpaperVideo.variants[0].width,1920);
 const pack={descriptor:Buffer.from(JSON.stringify(animated.manifest)+'\n'),files:{}};
 pack.digest=require('../../launcher/theme-data.js').hash(pack.descriptor);
 pack.files[animated.manifest.rules.path]=Buffer.from(JSON.stringify(animated.rules)+'\n');
 for(const f of [...animated.assets,...animated.documents,...animated.videos])pack.files[f.path]=f.data;
 require('../../launcher/theme-data.js').verify(pack,'99.0.0');
 await assert.rejects(()=>c.compileSource({...videoSource,videos:[]}),/video/);
 await assert.rejects(()=>c.compileSource({...videoSource,videos:[{...videoSource.videos[0],data:Buffer.from('bad')}]}));
 await assert.rejects(()=>c.compileSource({...videoSource,videos:[{...videoSource.videos[0],quality:'4k'}]}));
 console.log('Theme compiler checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});
