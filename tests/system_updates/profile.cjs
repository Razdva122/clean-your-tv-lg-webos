const assert = require('assert'), fs = require('fs'), vm = require('vm');
const profile = {schema:1,inventory:{apps:[{id:'app.one',title:'One',icon:'data:image/png;base64,YQ=='}],inputs:[]},config:{columns:5,dockApps:[],hiddenApps:[]},settings:{'tvhome.order':'{"dock":"","ids":["app.one"]}'}};
const tick = () => new Promise(resolve => setImmediate(resolve));
function harness(edition, {unavailable=false, corrupt=false, versionMismatch=false, noBackup=false, corruptProfile=false, snapshotProfile=profile, phase='verifying', storage, tiles=['app.one']}={}) {
  const calls=[], scripts=[], memory=storage||new Map(), errors=[];
  const data=require(edition==='root'?'../../root-edition/ui/root-profile-data':'../../launcher/user-data');
  const restored={profile:corruptProfile?{}:snapshotProfile,transaction:'a'.repeat(32),version:versionMismatch?'9.9.9':'1.2.3',phase:phase};
  const window={ROOT_VERSION:'1.2.3',CONFIG:profile.config,TV_APPS:{apps:[{id:'packaged'}],inputs:[]},HomeData:data,RootProfileData:data,AppLibrary:require('../../launcher/app-library'),
    SystemUpdates:{open:o=>errors.push(o),rpc:async(method,payload)=>{calls.push([method,payload]);if(unavailable)throw Object.assign(Error('absent'),{unavailable:true});if(corrupt)throw Error('corrupt journal');return method==='restoreProfile'?(noBackup?null:restored):{};}},
    RootUpdates:{rpc:async()=>null,open:o=>errors.push(o)}};
  const document={createElement:()=>({}),body:{appendChild:s=>scripts.push(s)},querySelector:()=>tiles.length?{}:null,querySelectorAll:()=>tiles.map(id=>({getAttribute:()=>id}))};
  const ctx={window,document,localStorage:{getItem:k=>memory.has(k)?memory.get(k):null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)},setTimeout,clearTimeout,Promise,XMLHttpRequest:class{open(){}send(){this.status=200;this.responseText=JSON.stringify({id:'com.gathin.tvhome',version:'1.2.3'});this.onload();}}};
  Object.assign(ctx,window);
  window.location={reload(){errors.push('reload');}};
  vm.runInNewContext(fs.readFileSync(edition==='root'?'root-edition/ui/root-profile.js':'launcher/profile-bootstrap.js','utf8'),ctx);
  return {window,ctx,calls,scripts,memory,errors};
}
async function startAppearance(h) {
  const context={Promise,setTimeout,clearTimeout,Date,CustomEvent:function(){},requestAnimationFrame:fn=>fn(),document:{dispatchEvent(){}},localStorage:h.ctx.localStorage,
    ThemeRuntime:{reset(){},apply(){}},ThemeStore:{get:async()=>null},ThemeData:{
      request:async url=>url==='appinfo.json'?{version:'1.6.1'}:{schemaVersion:1,themes:[{id:'builtin:alpine',title:'Alpine',version:'1.0.0',url:'themes/alpine/cytv-theme.json',digest:'b'.repeat(64)}]},decode:JSON.stringify,
      load:async()=>({id:'builtin:alpine'}),prepare:async pack=>({manifest:{id:pack.id},assetHandles:{}}),dispose(){}}};
  vm.runInNewContext(fs.readFileSync('launcher/theme-manager.js','utf8'),context);
  await context.ThemeManager.start();return context.ThemeManager.current();
}
(async()=>{
  for(const edition of ['no-root','root']) {
    let h=harness(edition);await tick();
    assert.equal(h.calls[0]&&h.calls[0][0],'restoreProfile',edition+' must query independent backup before rendering');
    assert.equal(h.scripts.length,1);
    assert.equal(h.window.TV_APPS.apps[0].id,'app.one');
    assert.equal(h.memory.get('tvhome.order'),profile.settings['tvhome.order']);
    h.window.RootLauncherRendered=true;h.scripts[0].onload();await tick();
    const receipt=h.calls.find(c=>c[0]==='healthy');
    assert(receipt,edition+' must report health to transaction owner');
    assert.deepEqual(JSON.parse(JSON.stringify(receipt[1])),{edition,transaction:'a'.repeat(32),version:'1.2.3'});
    const data=require(edition==='root'?'../../root-edition/ui/root-profile-data':'../../launcher/user-data');
    h=harness(edition,{storage:new Map([[data.key,'{broken']])});await tick();
    assert.equal(h.scripts.length,1,edition+' valid independent snapshot must repair corrupt local storage');
    assert.equal(JSON.parse(h.memory.get(data.key)).inventory.apps[0].id,'app.one');
    h=harness(edition,{corruptProfile:true,storage:new Map([[data.key,'{broken']])});await tick();
    assert.equal(h.scripts.length,0,'corrupt local data cannot make an invalid independent snapshot usable');
    h=harness(edition,{storage:new Map([['tvhome.language','ru']])});await tick();
    assert.equal(h.memory.has('tvhome.language'),false,edition+' restoration must clear settings absent from the snapshot');
    h.memory.set('tvhome.language','de');
    h=harness(edition,{storage:h.memory});await tick();
    assert.equal(h.memory.get('tvhome.language'),'de',edition+' must restore a transaction only once and preserve later user settings');
    h=harness(edition,{storage:new Map([['tvhome.columns.v1','{"version":1,"columns":8}']])});await tick();
    assert.equal(h.memory.get('tvhome.columns.v1'),'{"version":1,"columns":8}',edition+' System snapshot does not encode or replace the live Columns preference');
    h.memory.set('tvhome.columns.v1','{"version":1,"columns":2}');
    h=harness(edition,{storage:h.memory});await tick();
    assert.equal(h.memory.get('tvhome.columns.v1'),'{"version":1,"columns":2}',edition+' repeated startup preserves a post-restore column choice');
    h=harness(edition,{noBackup:true});await tick();
    assert.equal(h.scripts.length,1,edition+' null independent snapshot must retain legacy startup');
    assert.equal(h.window.TV_APPS.apps[0].id,'packaged','null snapshot must not apply unrelated inventory');
    assert(!h.calls.some(c=>c[0]==='healthy'));
    h=harness(edition,{phase:'complete'});await tick();
    h.memory.set('tvhome.order','{"dock":"","ids":[]}');
    h=harness(edition,{phase:'verifying-rollback',storage:h.memory});await tick();
    assert.equal(h.memory.get('tvhome.order'),profile.settings['tvhome.order'],edition+' rollback must restore settings even when the launcher version is unchanged');
    h=harness(edition,{tiles:['wrong']});await tick();h.window.RootLauncherRendered=true;h.scripts[0].onload();await tick();
    assert(!h.calls.some(c=>c[0]==='healthy'),'wrong rendered inventory must not confirm startup');
    h=harness(edition,{versionMismatch:true});await tick();
    assert.equal(h.scripts.length,0,'a stale snapshot cannot start the wrong Home version');
    h=harness(edition,{corrupt:true});await tick();
    assert.equal(h.scripts.length,0,'a corrupt independent transaction must not fall through to legacy backup');
    h=harness(edition,{unavailable:true});await tick();
    assert.equal(h.scripts.length,1,'installations without supervisor retain legacy boot');
    const accepted=JSON.stringify({id:'builtin:alpine',title:'Alpine',digest:null});
    const effectiveEight={...profile,config:{...profile.config,columns:8}};
    for(const phase of ['verifying','verifying-rollback'])for(const columns of [null,4,8]) {
      const preference=JSON.stringify({version:1,columns});
      h=harness(edition,{phase,snapshotProfile:effectiveEight,storage:new Map([['tvhome.theme.choice.v1',accepted],['tvhome.columns.v1',preference]])});await tick();
      assert.equal(h.memory.get('tvhome.theme.choice.v1'),accepted,edition+' System restore preserves accepted Alpine');
      assert.equal(h.memory.get('tvhome.columns.v1'),preference,edition+' System restore preserves exact Columns mode');
      const layout=require('../../launcher/home-layout').create(h.ctx.localStorage,h.window.CONFIG);
      layout.setThemeLayout({preset:'channel-list',columns:1,spacingScale:1,textScale:1,focusScale:1.1});
      assert.equal(layout.state().columns,columns===null?1:columns,edition+' By theme and explicit columns remain distinct after profile restore');
      assert.equal((await startAppearance(h)).id,'builtin:alpine',edition+' next actual theme-manager startup restores accepted appearance');
    }
    for(const columns of [4,8]) {
      h=harness(edition,{snapshotProfile:{...profile,config:{...profile.config,columns}},storage:new Map([['tvhome.theme.choice.v1',JSON.stringify({id:'builtin:classic',title:'Classic'})]])});await tick();
      const layout=require('../../launcher/home-layout').create(h.ctx.localStorage,h.window.CONFIG);
      assert.equal(layout.state().override,columns,edition+' missing modern key cannot erase genuine legacy Classic columns');
    }
    for(const [choice,trial] of [[accepted,'{"kind":"trial","id":"builtin:alpine"}'],['{broken',null],[JSON.stringify({id:'github:owner/repo:missing',title:'Missing',digest:'b'.repeat(64)}),null]]) {
      const memory=new Map([['tvhome.theme.choice.v1',choice]]);if(trial)memory.set('tvhome.theme.trial.v1',trial);
      h=harness(edition,{storage:memory});await tick();
      if(trial)assert.equal(h.memory.get('tvhome.theme.trial.v1'),trial,'bootstrap must not hide an interrupted-trial marker');
      assert.equal((await startAppearance(h)).id,'builtin:classic',edition+' interrupted/invalid/missing-cache appearance still fails safe');
      assert.equal(h.memory.has('tvhome.theme.trial.v1'),false,'theme manager consumes recovery marker');
    }
  }
  const layout=JSON.stringify({version:1,ids:['app.one'],hidden:[],catalog:profile.inventory.apps});
  let root=harness('root',{storage:new Map([['tvhome.layout',layout]])});await tick();
  assert.equal(root.memory.has('tvhome.layout'),false,'authoritative system snapshot clears absent Root layout');
  root.memory.set('tvhome.layout',layout);
  assert.equal((await root.window.RootProfile.capture({system:true})).settings['tvhome.layout'],layout,'system capture includes the live Root layout');
  assert.equal((await root.window.RootProfile.capture()).settings['tvhome.layout'],undefined,'legacy capture remains compatible with pinned older Root updater');
  const layoutProfile={...profile,settings:{...profile.settings,'tvhome.layout':layout}};
  root=harness('root',{snapshotProfile:layoutProfile,storage:new Map([['tvhome.layout','{broken']])});await tick();
  assert.equal(root.memory.get('tvhome.layout'),layout,'system restore replaces layout before rendering');
  const rootData=require('../../root-edition/ui/root-profile-data');
  assert.throws(()=>rootData.validate({...profile,settings:{'tvhome.layout':'{broken'}}));
  assert.throws(()=>rootData.validate({...profile,settings:{'tvhome.layout':JSON.stringify({version:1,ids:['same','same'],hidden:[],catalog:[]})}}));
  console.log('PASS independent profile restoration, exact startup health and legacy fallback');
})().catch(e=>{console.error(e);process.exitCode=1;});
