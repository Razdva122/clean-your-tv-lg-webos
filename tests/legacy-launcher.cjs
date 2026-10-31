// Run with PLAYWRIGHT_MODULE=/path/to/playwright node tests/legacy-launcher.cjs.
// Models the missing inset shorthand and two JS APIs, not a complete old TV engine.
// Restoring inset-only positioning must fail the clipping checks; restoring
// findIndex/Object.assign must fail startup/Inputs in the oldest profile.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const postcss = require('postcss');
const {fileURLToPath, pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const appRoot = process.env.TV_WEB_DIR ? path.resolve(process.env.TV_WEB_DIR) : path.join(root, 'launcher');
const artifacts = path.join(root, 'build/tests/issue-20');
const profiles = ['modern', 'no-inset', 'no-inset-or-es2015', 'prefixed-webkit'];

(async () => {
  fs.mkdirSync(artifacts, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  let failed = false;
  try {
    for (const profile of profiles) {
      if (process.env.LEGACY_PROFILE && process.env.LEGACY_PROFILE !== profile) continue;
      const page = await browser.newPage({viewport: {width: 1920, height: 1080}, locale: 'en'});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      try {
        if (profile !== 'modern') {
          await page.route('**/*.css', route => {
            // Old parsers ignore the unsupported declaration; preserve everything else.
            let css = fs.readFileSync(fileURLToPath(route.request().url()), 'utf8')
              .replace(/\binset\s*:[^;}]+;?/g, '');
            if (profile === 'prefixed-webkit') {
              const tree = postcss.parse(css);
              tree.walkDecls(d => {
                if (/^(transform(?:-origin)?|transition(?:-.+)?|animation(?:-.+)?|align-.+|justify-content|flex(?:-.+)?)$/.test(d.prop) ||
                    (d.prop === 'display' && /^(inline-)?flex$/.test(d.value))) d.remove();
              });
              tree.walkAtRules('keyframes', rule => rule.remove());
              css = tree.toString();
            }
            return route.fulfill({contentType: 'text/css', body: css});
          });
        }
        await page.addInitScript(oldest => {
          if (oldest) {
            delete Array.prototype.findIndex;
            delete Object.assign;
          }
          window.launches = [];
          window.inventoryRequests = [];
          window.airplayMode = 'success';
          window.PalmServiceBridge = function () {
            this.cancel = function () {};
            this.call = function (uri, raw) {
              const params = JSON.parse(raw);
              // Model the actual LS2 missing-service envelope. A generic failed
              // operation must not activate a competing legacy installer.
              if (uri.indexOf('luna://com.cleanyourtv.system.updater.service/') === 0) {
                setTimeout(() => this.onservicecallback(JSON.stringify({returnValue:false,errorCode:-1,errorText:'Service does not exist: com.cleanyourtv.system.updater.service'})), 0);
                return;
              }
              if (uri.endsWith('/listApps')) {
                window.inventoryRequests.push(this);
                return;
              }
              if (uri === 'luna://airplay.service/showAirplayPage') {
                window.airplayRequest = this;
                if (window.airplayMode === 'silent') return;
                setTimeout(() => this.onservicecallback(JSON.stringify({returnValue: window.airplayMode === 'success'})), 0);
                return;
              }
              if (uri.endsWith('/launch')) window.launches.push(params.id);
              setTimeout(() => this.onservicecallback(JSON.stringify({returnValue: uri.endsWith('/launch')})), 0);
            };
          };
        }, profile === 'no-inset-or-es2015');
        if (profile === 'prefixed-webkit') await page.addInitScript(() => {
          // Model WebKit's unsupported unprefixed CSSOM writes as well as CSS parsing.
          const nativeStyle = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'style'), styles = new WeakMap();
          const unsupported = new Set(['transform', 'transition']);
          Object.defineProperty(HTMLElement.prototype, 'style', {...nativeStyle, get() {
            const style = nativeStyle.get.call(this);
            if (!styles.has(style)) styles.set(style, new Proxy(style, {
              has(target, name) {return !unsupported.has(name) && Reflect.has(target, name);},
              get(target, name) {
                if (unsupported.has(name)) return undefined;
                const value = Reflect.get(target, name, target);
                return typeof value === 'function' ? value.bind(target) : value;
              },
              set(target, name, value) {return unsupported.has(name) || Reflect.set(target, name, value, target);}
            }));
            return styles.get(style);
          }});
          const text = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
          Object.defineProperty(Node.prototype, 'textContent', {...text, set(value) {
            if (this.nodeName === 'STYLE') value = value.replace(/(^|[;{])\s*(?:transform(?:-origin)?|transition|animation|justify-content):[^;}]+/g, '$1');
            text.set.call(this, value);
          }});
        });
        await page.route('**/config.js', route => route.fulfill({body:
          'window.CONFIG={columns:5,dockApps:["test.0","test.1","test.2","test.3","test.4","test.5","test.6"],hiddenApps:[],liveTvApp:"test.live"};'}));
        await page.route('**/apps.js', route => route.fulfill({body: 'window.TV_APPS=' + JSON.stringify({
          apps: Array.from({length: 7}, (_, i) => ({id: 'test.' + i,
            title: i === 0 ? 'ATRESplayer - Series, películas y TV online' : 'App ' + i,
            icon: i === 6 ? 'missing-test-icon.png' : 'brand-v2-icon.png'})),
          inputs: [{label: 'HDMI 1', appId: 'test.hdmi'}]
        }) + ';'}));
        await page.goto(pathToFileURL(path.join(appRoot, 'index.html')).href);
        await page.waitForFunction(() => document.querySelectorAll('#tiles .item').length === 8);
        // Issue #68: verify the real downloaded face, not just computed CSS weight.
        // SFNT tests separately ensure these are static outlines for old engines.
        const fontSession = await page.context().newCDPSession(page);
        await fontSession.send('DOM.enable');
        await fontSession.send('CSS.enable');
        for (const [weight, name] of [[300, 'Light'], [400, 'Regular'], [500, 'Medium'], [700, 'Bold']]) {
          await page.evaluate(async weight => {
            const probe = document.createElement('span');
            probe.id = 'font-regression-probe';
            probe.textContent = 'Home 0123456789';
            probe.style.cssText = 'position:absolute;top:0;left:0;font-family:Outfit;font-size:48px;font-weight:' + weight;
            document.body.appendChild(probe);
            await document.fonts.load(weight + ' 48px Outfit', probe.textContent);
            // Font loading resolves before the next layout/paint; CDP reads shaped glyphs.
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          }, weight);
          const {root: doc} = await fontSession.send('DOM.getDocument');
          const {nodeId} = await fontSession.send('DOM.querySelector', {nodeId: doc.nodeId, selector: '#font-regression-probe'});
          const {fonts} = await fontSession.send('CSS.getPlatformFontsForNode', {nodeId});
          assert.equal(fonts.length, 1, 'Outfit sample must not silently fall back');
          assert.equal(fonts[0].postScriptName, 'Outfit-' + name, 'select the actual static face for weight ' + weight);
          assert(fonts[0].isCustomFont && fonts[0].glyphCount > 0, 'render the packaged font');
          await page.locator('#font-regression-probe').evaluate(probe => probe.remove());
        }
        await fontSession.detach();
        await page.waitForTimeout(900); // Wait for the entry/focus CSS transitions.
        const geometry = await page.evaluate(() => ['viewport', 'stage'].map(id => {
          const r = document.getElementById(id).getBoundingClientRect();
          return {id, width: r.width, height: r.height};
        }));
        console.log(profile, JSON.stringify({geometry, errors}));
        await page.screenshot({path: path.join(artifacts, profile + '.png')});
        assert.deepEqual(geometry, [
          {id: 'viewport', width: 1920, height: 1080},
          {id: 'stage', width: 1920, height: 1080}
        ], 'the app grid must occupy the TV screen, even without inset support');
        assert.deepEqual(errors, [], 'launcher must initialize without unsupported API errors');
        if (profile === 'prefixed-webkit') {
          const rows = await page.locator('#topButtons .pill').evaluateAll(buttons => buttons.map(b => Math.round(b.getBoundingClientRect().top)));
          assert(rows.length >= 3 && rows.every(y => y === rows[0]), 'WebKit shortcuts remain in one horizontal row');
          const centres = await page.evaluate(() => {
            const c = document.querySelector('#tiles .focused .card').getBoundingClientRect();
            const g = document.getElementById('glass').getBoundingClientRect();
            return [Math.abs(c.x + c.width / 2 - g.x - g.width / 2), Math.abs(c.y + c.height / 2 - g.y - g.height / 2)];
          });
          assert(centres.every(d => d < 1), 'WebKit focus frame follows the selected card');
        }
        assert.equal(await page.locator('#tiles .focused').getAttribute('data-app-id'), 'test.0');
        assert.equal(await page.locator('#tiles img').evaluateAll(images =>
          images.filter(image => image.complete && image.naturalWidth > 0).length), 6);
        assert.equal(await page.locator('.missing-icon').count(), 1);
        assert(await page.locator('#tiles [data-app-id="test.0"] .card').evaluate(card => {
          const r = card.getBoundingClientRect();
          return card.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }), 'a populated DOM is insufficient: the viewport must not clip the cards');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Enter');
        assert.deepEqual(await page.evaluate(() => window.launches), ['test.1']);
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(500);
        assert(await page.locator('.missing-icon').evaluate(card => {
          const r = card.getBoundingClientRect();
          return card.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }), 'second-row missing-icon fallback must remain visible after scrolling');
        await page.keyboard.press('ArrowUp');
        await page.keyboard.press('ArrowUp');
        await page.locator('#btnInputs').click();
        assert.equal(await page.locator('#inputsPanel .inputRow').count(), 2,
          'Inputs must include HDMI and Live TV without Object.assign');
        await page.keyboard.press('Escape');
        await page.locator('#btnSettings').click();
        assert.deepEqual(await page.locator('#renewalPanel').evaluate(el => {
          const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height];
        }), [0, 0, 1920, 1080]);
        await page.locator('[data-category=language]').click();
        await page.locator('#settingsLanguageChoices').waitFor({state: 'visible'});
        assert.equal(await page.locator('#settingsLanguageChoices button').count(), 13,
          'automatic and twelve languages must remain reachable without ES2015 APIs');
        await page.keyboard.press('ArrowRight');
        assert.equal(await page.evaluate(() => document.activeElement.dataset.language), 'auto');
        await page.keyboard.press('Escape');
        assert.equal(await page.evaluate(() => document.activeElement.dataset.category), 'language');
        await page.keyboard.press('Escape');
        await page.locator('#renewalPanel').waitFor({state: 'hidden'});
        await page.locator('#tiles .add-app').dispatchEvent('click');
        assert.deepEqual(await page.locator('#appPicker').evaluate(el => {
          const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height];
        }), [0, 0, 1920, 1080]);
        await page.keyboard.press('Escape');
        await page.evaluate(() => HomeI18n.confirm({title: 'Test', message: 'Test', action: 'OK'}, function () {}));
        assert.deepEqual(await page.locator('#homeConfirmation').evaluate(el => {
          const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height];
        }), [0, 0, 1920, 1080]);
        await page.keyboard.press('Escape');
        assert.deepEqual(errors, [], 'navigation and dialogs must not raise compatibility errors');
        // A late startup inventory reply must not take navigation away from Inputs.
        await page.locator('#btnInputs').click();
        await page.evaluate(() => inventoryRequests[0].onservicecallback(JSON.stringify({
          returnValue: true, apps: [{id: 'test.0', title: 'Updated title'}, {id: 'airplay', title: 'AirPlay'}]
        })));
        assert.equal(await page.locator('#tiles .focused').count(), 0, 'late inventory must preserve Inputs focus');
        await page.keyboard.press('Escape');
        assert(await page.locator('#inputsPanel').evaluate(el => el.classList.contains('hidden')), 'Back still closes Inputs after inventory refresh');
        await page.locator('#tiles .add-app').dispatchEvent('click');
        await page.evaluate(() => inventoryRequests[inventoryRequests.length - 1].onservicecallback(JSON.stringify({returnValue:false})));
        await page.locator('#appPicker [data-app-id="airplay"]').click();
        // Closing the picker exposes grid tiles under the pointer. Park it
        // outside the grid before selecting the app for remote-control tests.
        await page.mouse.move(0, 0);
        await page.locator('#tiles [data-app-id="airplay"]').dispatchEvent('mouseover');
        assert.equal(await page.locator('#tiles .focused').getAttribute('data-app-id'), 'airplay');
        await page.clock.install();
        await page.evaluate(() => { window.launches = []; window.airplayMode = 'success'; });
        await page.keyboard.press('Enter');
        await page.clock.runFor(1);
        await page.clock.fastForward(10000);
        assert.deepEqual(await page.evaluate(() => launches), [], 'successful AirPlay page must not launch the app again');
        await page.evaluate(() => { window.airplayMode = 'error'; });
        await page.keyboard.press('Enter');
        await page.clock.runFor(1);
        await page.clock.fastForward(10000);
        assert.deepEqual(await page.evaluate(() => launches), ['airplay'], 'explicit AirPlay failure uses normal launch');
        await page.evaluate(() => { window.launches = []; window.airplayMode = 'silent'; });
        await page.keyboard.press('Enter');
        await page.clock.fastForward(10000);
        assert.deepEqual(await page.evaluate(() => launches), ['airplay'], 'silent AirPlay service must fall back within ten seconds');
        await page.evaluate(() => airplayRequest.onservicecallback(JSON.stringify({returnValue:false})));
        assert.deepEqual(await page.evaluate(() => launches), ['airplay'], 'late AirPlay error must not launch twice');
        const restored = await page.evaluate(() => {
          let removed = 0;
          const remove = DOMTokenList.prototype.remove;
          DOMTokenList.prototype.remove = function () {
            if (Array.prototype.indexOf.call(arguments, 'shown') >= 0) removed++;
            return remove.apply(this, arguments);
          };
          const focused = document.querySelector('#tiles .focused').dataset.appId;
          document.dispatchEvent(new Event('webOSRelaunch'));
          document.dispatchEvent(new Event('visibilitychange'));
          DOMTokenList.prototype.remove = remove;
          return {removed, focused, after: document.querySelector('#tiles .focused').dataset.appId};
        });
        assert.equal(restored.removed, 0, 'returning Home must not restart tile entrance animation');
        assert.equal(restored.after, restored.focused, 'returning Home preserves the selected app');
        for (const interaction of ['hold', 'editing']) {
          await page.reload();
          await page.clock.runFor(100);
          await page.waitForFunction(() => window.RootLauncherRendered);
          await page.locator('#tiles [data-app-id="test.0"]').hover();
          await page.evaluate(() => { window.heldTile = document.querySelector('#tiles .focused'); });
          await page.keyboard.down('Enter');
          await page.clock.runFor(interaction === 'editing' ? 650 : 100);
          await page.evaluate(() => inventoryRequests[0].onservicecallback(JSON.stringify({
            returnValue: true, apps: [{id: 'test.0', title: 'Updated title'}]
          })));
          assert(await page.evaluate(() => heldTile === document.querySelector('#tiles .focused')), 'inventory must not replace the tile during ' + interaction);
          await page.keyboard.up('Enter');
          if (interaction === 'editing') {
            assert.equal(await page.locator('#tiles .moving').count(), 1, 'inventory must preserve tile editing');
            await page.keyboard.press('Escape');
            assert.equal(await page.locator('#tiles .moving').count(), 0, 'tile editing remains cancellable');
          } else {
            assert.deepEqual(await page.evaluate(() => launches), ['test.0'], 'releasing OK still launches the selected app');
          }
        }
        if (profile === 'prefixed-webkit') {
          await page.evaluate(fixture => {
            fixture.layout = {preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1,
              ribbon:{left:340,right:84,bottom:0,cardHeight:180,gap:0,skewDeg:-13,focusLift:36,shortcuts:'bottom-left',labels:'focused-above',showClock:false}};
            fixture.requires.capabilities.push('ribbon-layout-v1');
            ThemeRuntime.apply({manifest:fixture,rules:{schemaVersion:1,rules:[]},assetHandles:{}});
          }, require('./themes/fixtures/valid-manifest.json'));
          await page.clock.runFor(1000);
          const ribbon = await page.locator('#tiles .focused').evaluate(item => {
            const card = item.querySelector('.card').getBoundingClientRect();
            return {transform:getComputedStyle(item).getPropertyValue('-webkit-transform'),bottom:card.bottom};
          });
          assert.notEqual(ribbon.transform, 'none', 'runtime Ribbon skew survives the prefixed WebKit parser');
          assert(Math.abs(ribbon.bottom - 1080) < 2, 'runtime Ribbon resets the base card transform and remains bottom aligned');
          await page.screenshot({path:path.join(artifacts, profile + '-ribbon.png')});
        }
        assert.deepEqual(errors, [], 'late replies and return events must not raise errors');
        console.log('PASS', profile, 'visible cards, icons, scroll, launch, Inputs and full-screen dialogs');
      } catch (error) {
        failed = true;
        console.error('FAIL', profile, error.message);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  if (failed) process.exitCode = 1;
})().catch(error => {console.error(error); process.exitCode = 1;});
