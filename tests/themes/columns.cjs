// Wrong precedence, accepting malformed geometry, or committing memory before
// storage succeeds must fail independently of the browser and TV services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const filename = require('node:path').resolve(__dirname, '../../launcher/home-layout.js');
assert(fs.existsSync(filename), 'column preference model is missing');
const {create, key} = require(filename);
function storage() {
  const values = new Map();
  return {getItem: name => values.has(name) ? values.get(name) : null,
    setItem: (name, value) => values.set(name, String(value)), removeItem: name => values.delete(name)};
}
const saved = storage(), config = {columns: 5};
let model = create(saved, config);
assert.deepEqual(model.state(), {columns: 5, override: null, themeColumns: 5, preset: 'dock-grid', allowColumnOverride: true, ribbon: null});
model.setThemeColumns(6);
assert.equal(model.state().columns, 6);
model.setColumns(3);
model.setThemeColumns(8);
assert.deepEqual(model.state(), {columns: 3, override: 3, themeColumns: 8, preset: 'dock-grid', allowColumnOverride: true, ribbon: null});
assert.equal(config.columns, 3);
model = create(saved, config);
model.setThemeColumns(7);
assert.equal(model.state().columns, 3, 'explicit choice survives reload and theme switch');
model.setColumns(null);
assert.equal(model.state().columns, 7, 'By theme restores the current author default');
assert.equal(create(saved, {columns: 7}).state().override, null, 'auto stays auto after reload');
for (const bad of [0, 9, -1, 1.5, NaN, Infinity, '4', {}, undefined]) {
  assert.throws(() => model.setColumns(bad), /columns-invalid/);
  assert.throws(() => model.setThemeColumns(bad), /columns-invalid/);
}
saved.setItem(key, '{broken');
assert.equal(create(saved, {columns: 4}).state().columns, 4, 'legacy configured count is retained');
assert.equal(create(storage(), {columns: 0}).state().columns, 5, 'malformed configuration falls back safely');
const unavailable = storage();
model = create(unavailable, {columns: 5});
unavailable.setItem = () => {throw Error('quota');};
assert.throws(() => model.setColumns(8), /quota/);
assert.equal(model.state().columns, 5, 'failed save preserves rendered state');
const profileStore = storage();
profileStore.setItem('profile', JSON.stringify({schema: 1, config: {columns: 5}, settings: {}}));
const adapter = {key: 'profile', validate: value => value};
model = create(profileStore, {columns: 5}, adapter);
model.setColumns(2);
assert.equal(JSON.parse(profileStore.getItem('profile')).config.columns, 2, 'existing profile keeps the effective count');
const previous = profileStore.getItem('profile'), setItem = profileStore.setItem;
profileStore.setItem = (name, value) => {if (name === 'profile') throw Error('profile-quota'); setItem(name, value);};
assert.throws(() => model.setColumns(8), /profile-quota/);
assert.equal(model.state().columns, 2);
assert.equal(JSON.parse(profileStore.getItem(key)).columns, 2, 'preference rolls back after profile save failure');
assert.equal(profileStore.getItem('profile'), previous);
const automaticStore = storage(), automaticConfig = {columns: 5};
const automatic = create(automaticStore, automaticConfig);
automatic.setThemeLayout({preset:'scenic-grid', columns:8, allowColumnOverride:false, spacingScale:1, textScale:1, focusScale:1.1});
assert.equal(automatic.state().columns,8);
assert.equal(automaticConfig.columns,5,'effective theme columns must not become a captured legacy preference');
assert.equal(create(automaticStore,JSON.parse(JSON.stringify(automaticConfig))).state().override,null,'capture/reload preserves By theme without a dedicated key');
automatic.setThemeLayout({preset:'channel-list',columns:1,spacingScale:1,textScale:1,focusScale:1.1});
assert.equal(automatic.state().columns,1,'Channel inherits its author default after Alpine');
automatic.setColumns(4);automatic.setThemeColumns(8);
assert.equal(automaticConfig.columns,4,'explicit preference remains capturable');
automatic.setColumns(null);
assert.equal(automaticConfig.columns,5,'By theme captures the neutral legacy default, not current theme columns');
const legacyConfig={columns:8},legacy=create(storage(),legacyConfig);
assert.equal(legacy.state().override,8,'genuine nondefault legacy preference is still imported');
const migratedStore=storage(),migratedConfig={columns:8};
const migrated=create(migratedStore,migratedConfig);
migrated.setThemeLayout({preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1});
migratedStore.setItem('tvhome.theme.choice.v1',JSON.stringify({id:'builtin:alpine',title:'Alpine'}));
const migratedProfile=JSON.parse(JSON.stringify({config:migratedConfig}));
const migratedReload=create(migratedStore,migratedProfile.config);
assert.equal(migratedReload.state().override,8,'genuine legacy eight survives first Alpine choice, profile capture and reload');
migratedReload.setThemeLayout({preset:'channel-list',columns:1,spacingScale:1,textScale:1,focusScale:1.1});
assert.equal(migratedReload.state().columns,8,'Channel honors normalized genuine legacy preference');
assert.equal(JSON.parse(migratedStore.getItem(key)).columns,8,'legacy normalization uses the existing explicit preference key');
for(const [columns,theme] of [[4,'builtin:classic'],[4,'builtin:alpine'],[8,'builtin:alpine'],[3,'github:example/themes:demo']]){
 const legacyStore=storage(),legacyProfile={config:{columns}};
 legacyStore.setItem('tvhome.theme.choice.v1',JSON.stringify({id:theme,title:'Saved theme'}));
 const beforeTheme=create(legacyStore,legacyProfile.config);
 assert.equal(beforeTheme.state().override,columns,'saved '+theme+' does not prove legacy '+columns+' is polluted');
 beforeTheme.setThemeLayout({preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1});
 const reload=create(legacyStore,JSON.parse(JSON.stringify(legacyProfile)).config);
 assert.equal(reload.state().override,columns,'profile reload retains legacy preference with '+theme);
 reload.setThemeLayout({preset:'channel-list',columns:1,spacingScale:1,textScale:1,focusScale:1.1});
 assert.equal(reload.state().columns,columns,'Channel honors legacy preference after profile reload');
 assert.equal(JSON.parse(legacyStore.getItem(key)).columns,columns,'trusted legacy preference is normalized without theme inference');
}
const explicitStore=storage();explicitStore.setItem('tvhome.theme.choice.v1',JSON.stringify({id:'builtin:alpine',title:'Alpine'}));
explicitStore.setItem(key,JSON.stringify({version:1,columns:8}));
assert.equal(create(explicitStore,{columns:5}).state().override,8,'modern explicit eight is retained');
explicitStore.setItem(key,JSON.stringify({version:1,columns:null}));
assert.equal(create(explicitStore,{columns:8}).state().override,null,'explicit By theme takes precedence over any legacy value');
explicitStore.removeItem('tvhome.theme.choice.v1');
assert.equal(create(explicitStore,{columns:8}).state().override,null,'theme reset cannot override explicit By theme');
console.log('PASS columns precedence, bounds, reload, legacy profiles and failed persistence');
