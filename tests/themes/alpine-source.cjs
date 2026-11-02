'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const {compileSource}=require('../../theme-api/compile.cjs');
const source='themes/alpine/',hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
(async()=>{
 const manifest=JSON.parse(fs.readFileSync(source+'theme.json'));
 assert.equal(manifest.id,'github:razdva122/clean-your-tv-lg-webos:alpine');assert.equal(manifest.themeVersion,'1.4.4');
 const expected={preview:'b122290c433d2f3921259c4efbc12dff57e805a1fe0cbbb45f31aa338b9eb2dc',landscape:'0d38c92bbb35dc31d0cf05a7f2ac9e724e9a046922e52673f32d498dd09d81ff','button-inputs':'405276aebdf8cb29509cac5d4c63f535dc5f0af511f0cc2c547d5141bd051bc8','button-network':'76446ac510cf667386ffcf47b17d9f86ea72fec31d76d09dd9f5c5df5717ceae','button-settings':'d513637e5a3b7a93be26ec4bc4d4266a10ac00aac417cb844e325b3d2c232763','inputs-preview':'cb040b79dafc1eafbdc7a4daacd768509888b25012f2ff67eba964bcbd9ea563','settings-preview':'1b6f34b9a6c7e91b8d5702e79b284e12d8b3c51c8c09b2125cf088a2a12559da','library-preview':'257f2e227508ea58cf125dd62fd87bd47230037617ad296a81f6bc077afea77e'};
 const assets=manifest.assets.map(a=>({...a,data:fs.readFileSync(source+a.path)}));
 assert.deepEqual(assets.map(a=>a.id).sort(),Object.keys(expected).sort());
 for(const a of assets)assert.equal(hash(a.data),expected[a.id],a.id+' preserves bundled Alpine 1.4.4 bytes');
 assert.equal(hash(fs.readFileSync(source+'LICENSE.txt')),'c50810017f170c3682cfc6e2640a5e3be416755ab52143e6966627f69e24995b');
 assert.equal(hash(fs.readFileSync(source+'CREDITS.txt')),'818ab3a39df2f0306896671bb68aa8f4fa53967c3c00e0344350e83e29f33603');
 const result=await compileSource({manifest,css:fs.readFileSync(source+'theme.css','utf8'),assets,documents:['LICENSE.txt','CREDITS.txt'].map(path=>({path,data:fs.readFileSync(source+path)})),source:{repository:'https://github.com/razdva122/clean-your-tv-lg-webos',commit:'a'.repeat(40)},minimumHomeVersion:'1.6.0'});
 assert.equal(hash(JSON.stringify(result.rules)+'\n'),'2f5b9b8339ad3ecf6b3ba193e595907b522b73138db7f5bd90f3b88c7474d2c0','compiled appearance is exactly bundled Alpine 1.4.4');
 console.log('PASS Alpine 1.4.4 Showcase source preserves exact rules, eight assets and both license documents');
})().catch(error=>{console.error(error);process.exitCode=1;});
