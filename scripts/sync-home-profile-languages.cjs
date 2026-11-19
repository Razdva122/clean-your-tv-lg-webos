const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function preferences() {
  const window = {};
  vm.runInNewContext(
    fs.readFileSync(path.join(root, 'launcher/i18n.js'), 'utf8'),
    { window }
  );
  return ['auto', ...window.HomeI18n.languages.map(({ code }) => code)];
}

function syncProfileLanguages({ write = false } = {}) {
  const codes = preferences().map((code) => "'" + code + "'");
  // Keep these lists in existing files so both services and historical
  // Root/System Updater bundle inventories retain their current dependencies.
  const js = '  var LANGUAGES = [\n    ' + codes.join(',\n    ') + '\n  ];';
  const python = 'LANGUAGES = (\n    ' + codes.join(',\n    ') + ',\n)';
  const targets = [
    'launcher/user-data.js',
    'updater-service/user-data.js',
    'root-edition/ui/root-profile-data.js',
    'root-edition/updater/profile.py'
  ];
  for (const name of targets) {
    const isPython = name.endsWith('.py');
    const declaration = isPython
      ? /^LANGUAGES = \([\s\S]*?^\)/m
      : /^  var LANGUAGES = \[[\s\S]*?^  \];/m;
    const filename = path.join(root, name);
    const current = fs.readFileSync(filename, 'utf8');
    assert.match(current, declaration, 'Missing language list in ' + name);
    const updated = current.replace(declaration, isPython ? python : js);
    if (write) {
      if (updated !== current) fs.writeFileSync(filename, updated);
    } else {
      assert.equal(
        current,
        updated,
        name +
          ' is out of sync. Run node scripts/sync-home-profile-languages.cjs --write'
      );
    }
  }
}

if (require.main === module) {
  const [mode = '--check', ...rest] = process.argv.slice(2);
  if (rest.length || !['--check', '--write'].includes(mode))
    throw Error(
      'Usage: node scripts/sync-home-profile-languages.cjs [--check | --write]'
    );
  syncProfileLanguages({ write: mode === '--write' });
}

module.exports = { preferences, syncProfileLanguages };
