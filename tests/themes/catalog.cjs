'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const fixture = require('../showcase/fixture.cjs');
const {generateCatalog, buildCatalog} = require('../../scripts/build-tv-theme-catalog.cjs');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'tv-catalog-'));
try {
  const active = fixture(root, 'active', 'Active');
  for (const availability of ['removed', 'unavailable']) {
    const entry = fixture(root, availability, availability);
    entry.record.availability = availability;
    fs.writeFileSync(path.join(root, 'registry', require('../../scripts/check-theme-submissions.cjs').keyFor(entry.record.id) + '.json'), JSON.stringify(entry.record));
  }
  const generated = generateCatalog({showcaseRoot: root});
  const catalog = JSON.parse(generated.get('theme-catalog.json'));
  const builtins = JSON.parse(fs.readFileSync(path.resolve('launcher/builtin-themes.json'))).themes;
  assert.deepEqual(catalog.themes.map(t => t.id), ['builtin:classic', ...builtins.map(entry=>entry.id), active.record.id]);
  const external = catalog.themes.find(entry=>entry.id===active.record.id);
  assert.equal(external.url, active.record.descriptorUrl);
  assert.equal(external.digest, active.record.descriptorSha256);
  for(const entry of builtins){const local=catalog.themes.find(theme=>theme.id===entry.id),manifest=JSON.parse(fs.readFileSync(path.resolve('launcher',entry.url))),base=entry.url.slice(0,entry.url.lastIndexOf('/')+1);assert.equal(local.preview,base+manifest.assets.find(asset=>asset.id===manifest.previewAssetId).path);assert.equal(local.credits,base+manifest.license.creditsPath);assert.equal(local.licenseFile,base+manifest.license.textPath);}
  for (const t of catalog.themes) assert.match(t.preview, /^(?:theme-catalog|themes)\/[a-zA-Z0-9/._-]+$/);
  const builtinRoot=path.join(root,'builtins');fs.mkdirSync(builtinRoot);fs.copyFileSync(path.resolve('launcher/builtin-themes.json'),path.join(builtinRoot,'builtin-themes.json'));fs.cpSync(path.resolve('launcher/themes'),path.join(builtinRoot,'themes'),{recursive:true});
  const firstBuiltin=builtins[0],localDescriptor=path.join(builtinRoot,firstBuiltin.url),localManifest=JSON.parse(fs.readFileSync(localDescriptor)),localBase=path.dirname(localDescriptor),creditsFile=path.join(localBase,localManifest.license.creditsPath);
  const badCredits=fs.readFileSync(creditsFile);badCredits[0]^=1;fs.writeFileSync(creditsFile,badCredits);assert.throws(()=>generateCatalog({showcaseRoot:root,builtinRoot}),/byte\/hash mismatch/,'catalog does not expose unverified built-in credits');
  fs.copyFileSync(path.resolve('launcher',path.dirname(firstBuiltin.url),localManifest.license.creditsPath),creditsFile);fs.appendFileSync(localDescriptor,' ');assert.throws(()=>generateCatalog({showcaseRoot:root,builtinRoot}),/descriptor digest mismatch/);
  const output = path.join(root, 'output');
  buildCatalog({showcaseRoot:root, launcherRoot:output});
  assert.doesNotThrow(() => buildCatalog({showcaseRoot:root, launcherRoot:output, check:true}));
  const before = Array.from(generated, ([name, bytes]) => [name, require('node:crypto').createHash('sha256').update(bytes).digest('hex')]);
  assert.deepEqual(Array.from(generateCatalog({showcaseRoot:root}), ([name, bytes]) => [name, require('node:crypto').createHash('sha256').update(bytes).digest('hex')]), before);
  fs.writeFileSync(path.join(output, 'theme-catalog/orphan.txt'), 'old');
  assert.throws(() => buildCatalog({showcaseRoot:root, launcherRoot:output, check:true}), /stale/);
  buildCatalog({showcaseRoot:root, launcherRoot:output});
  assert.equal(fs.existsSync(path.join(output, 'theme-catalog/orphan.txt')), false);
  const inventory = JSON.parse(fs.readFileSync(path.join(output, 'builtin-theme-files.json')));
  for (const name of generated.keys()) assert.ok(inventory.includes(name));
  fs.appendFileSync(path.join(output, external.preview), 'changed');
  assert.throws(() => buildCatalog({showcaseRoot:root, launcherRoot:output, check:true}), /stale/);
  active.record.previewFiles[0] = '../escape.png';
  fs.writeFileSync(path.join(root, 'registry', require('../../scripts/check-theme-submissions.cjs').keyFor(active.record.id) + '.json'), JSON.stringify(active.record));
  assert.throws(() => generateCatalog({showcaseRoot:root}));
  console.log('TV theme catalogue tests passed');
} finally { fs.rmSync(root, {recursive:true, force:true}); }
