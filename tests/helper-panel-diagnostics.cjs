// Real panel code with simulated DOM and caller-side LS2 transport; no TV is contacted.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('launcher/helper-control.js', 'utf8');
function panel(transportError = false) {
  const elements = [],
    calls = [],
    timers = new Map(),
    listeners = {};
  let timer = 0,
    confirms = 0;
  const document = {
    body: { appendChild() {} },
    addEventListener(name, fn) {
      listeners[name] = fn;
    },
    createElement(tag) {
      const element = {
        tag,
        hidden: false,
        disabled: false,
        attrs: {},
        scrollTop: 0,
        appendChild() {},
        setAttribute(key, value) {
          this.attrs[key] = value;
        },
        focus() {
          document.activeElement = this;
          if (this.onfocus) this.onfocus();
        },
        click() {
          if (this.onclick) this.onclick();
        }
      };
      elements.push(element);
      return element;
    }
  };
  const window = {
    HomeI18n: {
      ready: (callback) => callback(),
      t: (text) => text,
      confirm(options, callback) {
        confirms++;
        window.confirmStart = callback;
      }
    },
    RenewalPanel: {
      open() {
        throw Error('unexpected settings');
      }
    }
  };
  vm.runInNewContext(source, {
    window,
    document,
    setTimeout(fn) {
      timers.set(++timer, fn);
      return timer;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    PalmServiceBridge: class {
      constructor() {
        if (transportError) throw Error('SECRET transport');
      }
      cancel() {}
      call(uri, raw) {
        calls.push({
          uri,
          params: JSON.parse(raw),
          reply: (raw) => this.onservicecallback(raw)
        });
      }
    }
  });
  window.HomeHelper.open();
  const buttons = elements.filter((e) => e.tag === 'button'),
    details = elements.find((e) => e.tag === 'pre');
  const ui = {
    window,
    document,
    calls,
    timers,
    buttons,
    details,
    get confirms() {
      return confirms;
    },
    key(keyCode) {
      listeners.keydown({
        keyCode,
        preventDefault() {},
        stopImmediatePropagation() {}
      });
    },
    respond(i, value) {
      calls[i].reply(JSON.stringify(value));
    },
    snapshot() {
      return JSON.parse(details.textContent);
    }
  };
  assert.ok(
    buttons.find((b) => b.textContent === 'Show diagnostics'),
    'visible diagnostics action is available'
  );
  return ui;
}
function view(ui) {
  const before = ui.calls.length;
  ui.buttons[4].click();
  assert.equal(
    ui.calls.length,
    before,
    'viewing diagnostics performs no RPC or launch'
  );
  assert.equal(ui.buttons[4].attrs['aria-expanded'], 'true');
  assert.equal(ui.buttons[4].attrs['aria-controls'], ui.details.id);
  assert.equal(ui.document.activeElement, ui.details);
  assert.equal(ui.details.hidden, false);
  return ui.snapshot();
}
let ui = panel();
assert.equal(view(ui).helper_status.outcome, 'pending');
assert.equal(
  ui.snapshot().home_status.outcome,
  null,
  'unrequested Home status stays unknown'
);
ui.key(40);
assert.equal(ui.details.scrollTop, 80, 'remote can scroll diagnostics');
ui.key(461);
assert.equal(ui.details.hidden, true);
assert.equal(
  ui.document.activeElement,
  ui.buttons[4],
  'Back returns focus to disclosure'
);
assert.equal(ui.calls.length, 1);
ui.respond(0, {
  returnValue: false,
  errorCode: -1,
  errorText: 'SECRET SSID key /private/path',
  appId: 'secret'
});
let snapshot = view(ui);
assert.deepEqual(snapshot, {
  schema: 1,
  source: 'home-helper-panel',
  helper_status: {
    outcome: 'rejected',
    errorCode: -1,
    returnValue: false,
    running: null,
    blocked: null
  },
  home_status: {
    outcome: 'pending',
    errorCode: null,
    returnValue: null,
    enabled: null
  }
});
assert.equal(
  ui.calls.length,
  2,
  'refused service status probes only the independent Home broker'
);
ui.respond(1, { returnValue: false });
assert.ok(!ui.details.textContent.includes('SECRET'));
ui.buttons[2].click();
assert.equal(ui.calls.length, 2);
assert.equal(ui.confirms, 1, 'manual start still requires confirmation');
ui.window.confirmStart();
assert.equal(ui.calls.length, 3);
assert.equal(ui.calls[2].params.params.nativeHomeStart, true);
ui.buttons[4].click();
assert.equal(ui.details.hidden, true);
view(ui);
assert.equal(
  ui.calls.length,
  3,
  'diagnostics stay read-only during manual start'
);
for (const [raw, expected] of [
  ['{SECRET', 'invalid-json'],
  ['null', 'invalid-response'],
  ['[]', 'invalid-response'],
  ['"SECRET"', 'invalid-response'],
  ['{}', 'invalid-response'],
  ['{"returnValue":"true"}', 'invalid-response'],
  ['{"returnValue":null}', 'invalid-response']
]) {
  ui = panel();
  ui.calls[0].reply(raw);
  snapshot = view(ui);
  assert.equal(snapshot.helper_status.outcome, expected);
  assert.equal(snapshot.helper_status.running, null);
  assert.equal(ui.calls.length, 1);
}
ui = panel();
[...ui.timers.values()][0]();
assert.equal(view(ui).helper_status.outcome, 'timeout');
assert.equal(ui.calls.length, 1);
for (const code of ['SECRET', 1e50, 1.1, null]) {
  ui = panel();
  ui.respond(0, { returnValue: false, errorCode: code });
  assert.equal(view(ui).helper_status.errorCode, null);
}
ui = panel();
ui.respond(0, { returnValue: true, running: 'SECRET', blocked: 'SECRET' });
snapshot = view(ui);
assert.equal(snapshot.helper_status.running, null);
assert.equal(snapshot.helper_status.blocked, null);
ui = panel();
ui.respond(0, { returnValue: true, running: false, blocked: false });
assert.equal(ui.calls.length, 2);
ui.respond(1, { returnValue: false });
assert.equal(view(ui).helper_status.running, false);
assert.equal(ui.buttons[2].hidden, false);
ui = panel();
ui.respond(0, { returnValue: true, blocked: false });
assert.equal(ui.calls.length, 2);
ui.respond(1, {
  returnValue: false,
  errorCode: 403,
  enabled: 'SECRET',
  errorText: 'SECRET'
});
snapshot = view(ui);
assert.equal(snapshot.home_status.outcome, 'rejected');
assert.equal(snapshot.home_status.errorCode, 403);
assert.equal(snapshot.home_status.enabled, null);
assert.ok(!ui.details.textContent.includes('SECRET'));
ui = panel();
ui.respond(0, { returnValue: true, running: true });
ui.respond(1, { returnValue: true, enabled: false });
assert.equal(view(ui).home_status.enabled, false);
assert.equal(ui.calls.length, 2);
ui = panel();
ui.buttons[3].click();
ui.respond(1, { returnValue: false, errorCode: 2 });
ui.respond(0, { returnValue: true, running: true });
assert.equal(view(ui).helper_status.errorCode, 2);
assert.equal(ui.calls.length, 3, 'stale callback cannot trigger Home status');
ui = panel();
ui.buttons[0].click();
ui.window.HomeHelper.open();
ui.respond(1, { returnValue: false, errorCode: 3 });
ui.respond(0, { returnValue: false, errorCode: 4 });
assert.equal(
  view(ui).helper_status.errorCode,
  3,
  'closed generation cannot replace relaunch diagnostics'
);
ui = panel(true);
assert.equal(view(ui).helper_status.outcome, 'transport-error');
assert.equal(ui.calls.length, 0);
for (const failure of ['timeout', 'invalid-json', 'invalid-response']) {
  ui = panel();
  ui.respond(0, { returnValue: true });
  if (failure === 'timeout') [...ui.timers.values()][0]();
  else ui.calls[1].reply(failure === 'invalid-json' ? '{SECRET' : '{}');
  assert.equal(view(ui).home_status.outcome, failure);
  assert.equal(ui.calls.length, 2);
}
ui = panel();
ui.respond(0, { returnValue: true });
ui.buttons[3].click();
ui.respond(2, { returnValue: true });
ui.respond(3, { returnValue: true, enabled: false });
ui.respond(1, { returnValue: true, enabled: true });
assert.equal(
  view(ui).home_status.enabled,
  false,
  'stale Home callback cannot replace current diagnostics'
);
assert.ok(
  ui.details.textContent.length < 1024,
  'allowlisted snapshot has bounded output'
);
const catalogSource = fs.readFileSync('launcher/catalogs.js', 'utf8');
const catalogs = [];
vm.runInNewContext(catalogSource, {
  HomeI18n: {
    add(value) {
      catalogs.push(...Object.values(value));
    }
  }
});
for (const label of ['Show diagnostics', 'Hide diagnostics'])
  assert.equal(
    catalogs.filter((locale) => Object.hasOwn(locale, label)).length,
    13,
    'reuse all thirteen locale strings'
  );

// A delayed status reply must not steal focus from read-only diagnostics.
for (const outcome of [
  'home-success',
  'home-failure',
  'blocked',
  'status-failure'
]) {
  const pending = panel();
  view(pending);
  pending.respond(
    0,
    outcome === 'status-failure'
      ? { returnValue: true, running: 'invalid' }
      : { returnValue: true, running: false, blocked: outcome === 'blocked' }
  );
  if (outcome.indexOf('home-') === 0)
    pending.respond(1, {
      returnValue: outcome === 'home-success',
      enabled: true
    });
  assert.equal(
    pending.document.activeElement,
    pending.details,
    outcome + ': retain diagnostics focus'
  );
  pending.key(40);
  assert.equal(
    pending.details.scrollTop,
    80,
    outcome + ': remote still scrolls diagnostics'
  );
  pending.key(461);
  assert.equal(pending.details.hidden, true);
  assert.equal(pending.document.activeElement, pending.buttons[4]);
}
console.log(
  'PASS Helper panel diagnostics: safe caller outcomes, refusal/timeout/malformed data, no extra RPCs, stale generations, navigation and start consent'
);

// Optional real-browser geometry: node tests/helper-panel-diagnostics.cjs --browser
if (process.argv.includes('--browser'))
  (async () => {
    const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
    const browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
    const translations = {};
    vm.runInNewContext(catalogSource, {
      HomeI18n: {
        add(values) {
          Object.assign(translations, values);
        }
      }
    });
    try {
      for (const [width, height] of [
        [1280, 720],
        [1920, 1080]
      ]) {
        for (const locale of Object.keys(translations)) {
          const page = await browser.newPage({ viewport: { width, height } });
          const errors = [];
          page.on('pageerror', (e) => errors.push(e.message));
          await page.setContent(
            '<html><body><button id="previous">Home</button></body></html>'
          );
          await page.addStyleTag({ path: 'launcher/renewal-panel.css' });
          await page.evaluate((map) => {
            window.calls = [];
            window.HomeI18n = {
              ready: (f) => f(),
              t: (text) => map[text] || text,
              confirm() {
                throw Error('unexpected start');
              }
            };
            window.PalmServiceBridge = function () {
              this.cancel = function () {};
              this.call = function (uri) {
                window.calls.push(uri);
                this.onservicecallback(
                  JSON.stringify({
                    returnValue: false,
                    errorCode: -1,
                    errorText: 'SECRET'
                  })
                );
              };
            };
            document.getElementById('previous').focus();
          }, translations[locale]);
          await page.addScriptTag({ content: source });
          await page.evaluate(() => HomeHelper.open());
          await page.locator('.helper-panel button').nth(4).click();
          const geometry = await page.evaluate(() => {
            const pre = document.getElementById('helperPanelDiagnostics'),
              card = pre.parentNode;
            const rect = (e) => {
              const r = e.getBoundingClientRect();
              return {
                left: r.left,
                top: r.top,
                right: r.right,
                bottom: r.bottom
              };
            };
            return {
              card: rect(card),
              pre: rect(pre),
              actions: [...card.querySelectorAll('button')]
                .filter((b) => !b.hidden)
                .map(rect),
              calls: window.calls.length,
              scrollHeight: pre.scrollHeight,
              clientHeight: pre.clientHeight
            };
          });
          for (const r of [geometry.card, geometry.pre, ...geometry.actions]) {
            assert(
              r.left >= 0 &&
                r.top >= 0 &&
                r.right <= width &&
                r.bottom <= height,
              locale +
                ' ' +
                width +
                ': controls and diagnostics fit physical viewport'
            );
          }
          assert.equal(geometry.calls, 2);
          if (geometry.scrollHeight > geometry.clientHeight) {
            await page.keyboard.press('ArrowDown');
            assert(
              await page
                .locator('#helperPanelDiagnostics')
                .evaluate((e) => e.scrollTop > 0),
              'remote scrolls actual long pre'
            );
          }
          await page.keyboard.press('Escape');
          assert.equal(
            await page
              .locator('.helper-panel button')
              .nth(4)
              .evaluate((e) => document.activeElement === e),
            true
          );
          assert.equal(
            await page.locator('#helperPanelDiagnostics').isVisible(),
            false
          );
          assert.deepEqual(errors, []);
          await page.close();
        }
        console.log(
          'PASS Helper diagnostic browser geometry/navigation: ' +
            width +
            'x' +
            height +
            ', all 13 locales'
        );
      }
    } finally {
      await browser.close();
    }
  })().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
