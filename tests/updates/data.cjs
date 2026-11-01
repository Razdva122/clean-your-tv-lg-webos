const assert=require('assert'),data=require('../../launcher/user-data');
const s={schema:1,inventory:{apps:[{id:'app',title:'App',icon:'data:image/png;base64,YQ=='}],inputs:[]},config:{columns:5,dockApps:[],hiddenApps:[]},settings:{'tvhome.order':'["app"]'}};
const map=new Map(),storage={getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,v)};
assert.equal(data.load(storage),null);data.save(storage,s);assert.deepEqual(data.load(storage),s);data.apply(storage,s);assert.equal(map.get('tvhome.order'),'["app"]');
assert.throws(()=>data.validate({...s,settings:{token:'secret'}}));assert.throws(()=>data.validate({...s,inventory:{apps:[{...s.inventory.apps[0],icon:'icons/a.png'}],inputs:[]}}));
map.set(data.key,'broken');assert.throws(()=>data.load(storage));
console.log('PASS portable inventory and settings');
for(const locale of ['pt-BR','cs']){
 const localized={...s,settings:{'tvhome.language':locale}};
 data.apply(storage,localized);assert.equal(map.get('tvhome.language'),locale);
}
assert.throws(()=>data.validate({...s,settings:{'tvhome.language':'<script>'}}));
console.log('PASS portable locale validation and restoration');
