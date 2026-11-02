'use strict';
const assert=require('node:assert/strict');
(async()=>{
 let writes=[],ordinary=[];
 const handlers=require('./handlers')(async c=>{ordinary.push(c);return {returnValue:true,result:{}};},null,async(command,sources)=>{writes.push([command,sources]);return {returnValue:true,result:{sources:sources||{tv:true,youtube:false,hdmi:false},active:true}};});
 const read=await handlers.status({startup:'status'});
 assert.equal(read.returnValue,true);assert.deepEqual(read.result.result.sources,{tv:true,youtube:false,hdmi:false});
 const sources={tv:false,youtube:true,hdmi:false};
 assert.equal((await handlers.enable({startup:'configure',sources})).returnValue,true);
 assert.deepEqual(writes,[['status',undefined],['configure',sources]]);
 for(const invalid of [{startup:'configure',sources:{tv:1,youtube:false,hdmi:false}},{startup:'configure',sources:{tv:true}},{startup:'configure',sources:{...sources,extra:true}},{startup:'status',sources}])assert.equal((await handlers.enable(invalid)).returnValue,false);
 assert.deepEqual(ordinary,[],'startup settings never invoke Home enable');
 console.log('startup service payload tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
