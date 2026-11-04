const assert = require('assert');
const create = require('./root-exit.js');
const stock = {sam_home:'com.webos.app.home', profiles:{defaultApps:{categories:{home:'com.webos.app.home'}},idleApp:{appId:'com.webos.app.home'}}};
const wrap = result => ({returnValue:true,result:{returnValue:true,result}});
(async () => {
  const calls=[];
  let fail=false;
  const exit=create(async (method) => {
    calls.push(method);
    if(method==='restore') return wrap(fail?'conflict':'restored');
    return wrap({effective:stock});
  },async()=>calls.push('launch'));
  await exit(); assert.deepStrictEqual(calls,['restore','status','launch']);
  fail=true; calls.length=0;
  await assert.rejects(exit()); assert.deepStrictEqual(calls,['restore']);
  for(const reply of [null,{}, {returnValue:false},wrap({effective:{sam_home:'com.webos.app.home'}})]) {
    let launched=false;
    await assert.rejects(create(async m=>m==='restore'?wrap('restored'):reply,async()=>{launched=true;})());
    assert.strictEqual(launched,false);
  }
  let release;let count=0;
  const blocked=create(()=>{count++;return new Promise(r=>{release=r;});},async()=>{});
  const first=blocked(); await assert.rejects(blocked(),/already/);assert.strictEqual(count,1);
  release(wrap('conflict'));await assert.rejects(first);
  const gateStock={backend:'c1-native-gate',state:'stopped',profiles:null,
    mounted:false,healthy:false,stock_verified:true};
  let gateLaunches=0;
  await create(async m=>m==='restore'?wrap('restored'):wrap({effective:gateStock}),async()=>{gateLaunches++;})();
  assert.strictEqual(gateLaunches,1);
  for(const changes of [{mounted:true},{stock_verified:false},{profiles:{}},{healthy:true},{state:'armed'},
    {...stock,mounted:true,stock_verified:false}]) {
    await assert.rejects(create(async m=>m==='restore'?wrap('restored'):wrap({effective:{...gateStock,...changes}}),async()=>{gateLaunches++;})());
  }
  assert.strictEqual(gateLaunches,1);
  console.log('PASS Root exit readback, conflicts, malformed replies and duplicate requests');
})().catch(e=>{console.error(e);process.exit(1);});
