const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('tests/themes/wallpaper.cjs','utf8').split("let f=fixture(undefined)")[0];
const fixture=vm.runInNewContext(source+';fixture',{require});
const f=fixture(true),personal={manifest:{id:'personal:wallpaper',title:'My wallpaper',defaults:{wallpaperAssetId:'poster',dim:0},assets:[{id:'poster',width:1280,height:720}]},assetHandles:{poster:'blob:personal'},origin:'phone'};
assert.equal(typeof f.api.setPersonal,'function');f.api.configure(f.input);f.api.setPersonal(personal,true);assert.equal(f.api.state().source,'personal');f.api.configure(f.input);assert.equal(f.api.state().posterURL,'blob:personal');f.api.reset();assert.equal(f.api.state().posterURL,'blob:personal');f.api.setPersonal(personal,false);assert.equal(f.api.state().source,'theme');assert.equal(f.api.state().posterURL,'');console.log('PASS personal independent of theme/reset');
