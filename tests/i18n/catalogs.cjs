const fs = require('fs'),
  vm = require('vm'),
  assert = require('assert/strict');
const catalogs = {},
  ctx = {
    HomeI18n: {
      add(values) {
        for (const [locale, items] of Object.entries(values))
          Object.assign(catalogs[locale] || (catalogs[locale] = {}), items);
      }
    }
  };
ctx.window = ctx;
for (const file of [
  'launcher/catalogs.js',
  'root-edition/ui/root-locales.js',
  'launcher/theme-locales.js'
])
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), ctx);
const sources = Object.keys(catalogs.en),
  tags = [
    'en',
    'cs',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'zh-Hans',
    'zh-Hant'
  ];
for (const tag of tags)
  for (const key of sources) {
    assert.equal(
      typeof catalogs[tag]?.[key],
      'string',
      tag + ' missing ' + key
    );
    assert(catalogs[tag][key].trim(), tag + ' empty ' + key);
    assert.deepEqual(
      (catalogs[tag][key].match(/\{\w+\}/g) || []).sort(),
      (key.match(/\{\w+\}/g) || []).sort(),
      tag + ' placeholders ' + key
    );
  }
console.log(
  'PASS complete catalogs and interpolation placeholders for ' +
    sources.length +
    ' UI strings × thirteen TV languages'
);
