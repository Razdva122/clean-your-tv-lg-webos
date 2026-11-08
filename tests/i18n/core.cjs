const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const source = fs.readFileSync('launcher/i18n.js', 'utf8');
function load(lang, stored, blocked = false) {
  const saved = { 'tvhome.language': stored };
  let reloads = 0;
  const ctx = {
    navigator: { languages: lang, language: lang[0] },
    localStorage: {
      getItem: (k) => {
        if (blocked) throw Error('blocked');
        return saved[k] || null;
      },
      setItem: (k, v) => {
        if (blocked) throw Error('blocked');
        saved[k] = v;
      }
    },
    location: { reload: () => reloads++ }
  };
  ctx.window = ctx;
  vm.runInNewContext(source, ctx);
  return { i: ctx.HomeI18n, saved, reloads: () => reloads };
}
assert.equal(load(['pt-PT']).i.language(), 'pt-BR');
assert.equal(load(['ja-JP', 'de-AT']).i.language(), 'de');
assert.equal(load(['xx']).i.language(), 'en');
assert.equal(load(['en-US'], 'ru').i.language(), 'ru');
assert.equal(load(['ko-KR'], 'not-a-locale').i.language(), 'ko');
assert.equal(load(['hi-IN'], null, true).i.language(), 'hi');
const x = load(['fr-FR']);
x.i.add({ fr: { 'Hello {name}': 'Bonjour {name}' } });
assert.equal(x.i.t('Hello {name}', { name: '$& <b>' }), 'Bonjour $& <b>');
assert.equal(x.i.t('Fallback {n}', { n: 0 }), 'Fallback 0');
assert.equal(x.i.setLanguage('de'), true);
assert.equal(x.saved['tvhome.language'], 'de');
assert.equal(x.reloads(), 1);
assert.equal(x.i.setLanguage('bad'), false);
assert.equal(x.reloads(), 1);
assert.equal(
  load(['en'], null, true).i.setLanguage('de'),
  false,
  'blocked storage must not pretend to persist or reload'
);
assert.equal(x.i.languages.length, 13);
assert.equal(load(['cs-CZ']).i.language(), 'cs');
assert.equal(load(['cs_CZ.UTF-8']).i.language(), 'cs');
assert.equal(load(['en'], 'cs').i.language(), 'cs');
assert.equal(x.i.setLanguage('cs'), true);
assert.equal(x.saved['tvhome.language'], 'cs');
assert.equal(x.i.languages.find((l) => l.code === 'cs').name, 'Čeština');
for (const [tag, want] of [
  ['zh', 'zh-Hans'],
  ['zh_CN', 'zh-Hans'],
  ['zh-SG', 'zh-Hans'],
  ['zh-TW', 'zh-Hant'],
  ['zh-HK', 'zh-Hant'],
  ['zh_MO', 'zh-Hant'],
  ['zh-Hant-CN', 'zh-Hant'],
  ['zh-Hans-TW', 'zh-Hans']
]) {
  assert.equal(load([tag]).i.language(), want, tag);
}
for (const code of ['zh-Hans', 'zh-Hant']) {
  const selected = load(['en']);
  assert.equal(selected.i.setLanguage(code), true);
  assert.equal(selected.saved['tvhome.language'], code);
  assert.equal(selected.i.language(), code);
}
console.log(
  'PASS locale resolution, preference, interpolation, storage failures'
);
let bridge,
  timed,
  loaded = false;
const tv = {
  navigator: { language: 'en-US' },
  localStorage: { getItem: () => null },
  setTimeout: (fn) => {
    timed = fn;
    return 1;
  },
  clearTimeout() {},
  PalmServiceBridge: function () {
    bridge = this;
    this.cancel = () => {};
    this.call = (uri, raw) => {
      assert.equal(uri, 'luna://com.webos.settingsservice/getSystemSettings');
      assert.equal(JSON.parse(raw).key, 'localeInfo');
    };
  }
};
tv.window = tv;
vm.runInNewContext(source, tv);
tv.HomeI18n.ready(() => {
  loaded = true;
});
assert.equal(loaded, false);
bridge.onservicecallback(
  JSON.stringify({
    returnValue: true,
    settings: { localeInfo: { locales: { UI: 'de-DE' } } }
  })
);
assert.equal(loaded, true);
assert.equal(
  tv.HomeI18n.language(),
  'de',
  'TV UI language takes precedence over browser'
);
console.log('PASS async TV system locale before UI startup');
const htmlLocale = load(['de']);
htmlLocale.i.add({ de: { 'Inputs': '<Eingänge>', 'Choose': '"Wählen"' } });
assert.equal(
  htmlLocale.i.html(
    '<span>Inputs</span><button title="Choose">Inputs</button>'
  ),
  '<span>&lt;Eingänge&gt;</span><button title="&quot;Wählen&quot;">&lt;Eingänge&gt;</button>'
);
let done = 0;
const failedTV = {
  ...tv,
  navigator: { language: 'fr' },
  PalmServiceBridge: function () {
    this.call = () => {
      throw Error('unavailable');
    };
    this.cancel = () => {};
  }
};
failedTV.window = failedTV;
vm.runInNewContext(source, failedTV);
failedTV.HomeI18n.ready(() => done++);
assert.equal(done, 1);
assert.equal(failedTV.HomeI18n.language(), 'fr');
console.log(
  'PASS escaped markup and fallback when TV locale service is unavailable'
);

// Legacy WebKit may ignore locale options without throwing, leaking seconds/GMT.
for (const intl of [undefined, {}]) {
  const legacy = vm.createContext({ Intl: intl });
  vm.runInContext(
    'Date.prototype.toLocaleTimeString = function () { return "10:57:36 PM GMT+04:00"; };',
    legacy
  );
  vm.runInContext(source, legacy);
  for (const [hour, minute, expected] of [
    [0, 5, '00:05'],
    [12, 5, '12:05'],
    [22, 57, '22:57']
  ]) {
    const stamp = new Date(2026, 10, 7, hour, minute, 36).getTime();
    assert.equal(legacy.HomeI18n.formatTime(stamp), expected);
  }
}
for (const [lang, expected] of [
  ['en', ['12:05 AM', '12:05 PM', '10:05 PM']],
  ['ru', ['00:05', '12:05', '22:05']],
  ['de', ['00:05', '12:05', '22:05']],
  ['ko', ['오전 12:05', '오후 12:05', '오후 10:05']]
]) {
  const modern = vm.createContext({ navigator: { language: lang } });
  vm.runInContext(
    'Date.prototype.toLocaleTimeString = function () { return "10:57:36 PM GMT+04:00"; };',
    modern
  );
  vm.runInContext(source, modern);
  for (const [index, hour] of [0, 12, 22].entries()) {
    const stamp = new Date(2026, 10, 7, hour, 5, 36).getTime();
    assert.equal(modern.HomeI18n.formatTime(stamp), expected[index]);
  }
}
console.log(
  'PASS compact legacy clock and localized modern hour/minute formatting'
);
