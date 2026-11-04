const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const ctx={Promise,Uint8Array,ArrayBuffer,DataView,atob,btoa,setTimeout,clearTimeout,document:{dispatchEvent(){}},CustomEvent:function(){}};
assert(fs.existsSync('launcher/personal-wallpaper.js'),'personal manager exists');vm.runInNewContext(fs.readFileSync('launcher/personal-wallpaper.js','utf8'),ctx);
(async()=>{assert.equal(typeof ctx.PersonalWallpaper.receive,'function');for(const input of [null,{}, {schemaVersion:1,kind:'wallpaper',source:'phone',image:{},variants:[{}]}])await assert.rejects(ctx.PersonalWallpaper.receive(input));assert.equal(ctx.PersonalWallpaper.state().installed,false);console.log('PASS malformed personal input fails without persistence');})().catch(e=>{console.error(e);process.exit(1);});
