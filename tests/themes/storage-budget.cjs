'use strict';
const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
function api(navigator){const context={navigator,Promise,setTimeout,clearTimeout,Math,isFinite,document:{dispatchEvent(){}},CustomEvent:function(){}};vm.runInNewContext(fs.readFileSync('launcher/theme-store.js','utf8'),context);return context.StorageBudget;}
(async()=>{
 let storage=api({storage:{estimate:()=>Promise.resolve({usage:8*1048576,quota:10*1048576})}});
 await assert.rejects(storage.check(3*1048576),error=>error.code==='storage-full'&&error.budget.required===3*1048576&&error.budget.available===2*1048576&&error.budget.shortfall===1048576);
 const result=await storage.check(1048576);assert.equal(result.shortfall,0);assert.match(storage.format(result),/required 1.0 MiB; available 2.0 MiB; shortfall 0.0 MiB/);
 storage=api({webkitTemporaryStorage:{queryUsageAndQuota:ok=>ok(2,10)}});assert.equal((await storage.check(8)).available,8);
 storage=api({});assert.equal((await storage.check(100)).available,null);assert.match(storage.format(await storage.check(100)),/could not be determined/);
 storage=api({storage:{estimate:()=>Promise.resolve({quota:NaN,usage:1})}});assert.equal((await storage.check(100)).available,null);
 await assert.rejects(storage.quotaFailure({name:'QuotaExceededError'},100),error=>error.code==='storage-full'&&error.budget.required===100);
 console.log('PASS storage budgets, shortfall, legacy quota and honest unknown capacity');
})().catch(error=>{console.error(error);process.exitCode=1;});
