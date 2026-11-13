// Persistent CARD bootstrap; optional media must not gate accepted appearance.
'use strict';
const { assert, chromium, fs, path, stage } = require('./browser.cjs');
const http = require('node:http');
const { execFileSync } = require('node:child_process');
const { compile } = require('../../scripts/compile-tv-web.cjs');

(async () => {
  const site = stage('noroot-startup-readiness');
  const historical = process.env.CYTV_READINESS_SOURCE,
    shared = [
      'app.js',
      'theme-manager.js',
      'theme-data.js',
      'personal-wallpaper.js',
      'wallpaper-library.js'
    ];
  const source = (edition, name) =>
    historical && shared.includes(name)
      ? execFileSync('git', ['show', historical + ':launcher/' + name], {
          encoding: 'utf8'
        })
      : fs.readFileSync(path.join(site, edition, name), 'utf8');
  const server = http.createServer((req, res) => {
    const file = path.resolve(
      site,
      '.' + new URL(req.url, 'http://localhost').pathname
    );
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
      return res.writeHead(404).end();
    res.setHeader(
      'Content-Type',
      {
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.html': 'text/html',
        '.css': 'text/css',
        '.jpg': 'image/jpeg',
        '.mp4': 'video/mp4'
      }[path.extname(file)] || 'application/octet-stream'
    );
    const name = path.basename(file),
      edition = path.basename(path.dirname(file));
    res.end(
      historical && shared.includes(name)
        ? source(edition, name)
        : fs.readFileSync(file)
    );
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  async function check(savedBuiltin, edition, earlyRoot = false) {
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
      }),
      errors = [];
    let queries = 0,
      mediaRequests = 0,
      releaseMedia;
    const mediaGate = new Promise((resolve) => {
      releaseMedia = resolve;
    });
    page.on('pageerror', (error) => errors.push(error.message));
    await page.exposeFunction('producerContext', () => {
      queries++;
      return {};
    });
    await page.addInitScript(
      ({ savedBuiltin, rootEdition, handlesRelaunch, earlyRoot }) => {
        localStorage.setItem(
          'tvhome.theme.choice.v1',
          JSON.stringify({ id: 'builtin:ribbon', title: 'Ribbon' })
        );
        window.PalmSystem = {
          launchParams: { cytvHome: { reason: 'home', generation: 8 } },
          activate() {}
        };
        window.rootAudit = [];
        window.earlyRoot = earlyRoot;
        window.rootRestoreReads = 0;
        if (rootEdition) {
          const frame = requestAnimationFrame.bind(window),
            queued = [];
          let active = !handlesRelaunch;
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            get: () => !active
          });
          window.requestAnimationFrame = (callback) =>
            active
              ? frame((time) => {
                  rootAudit.push('frame');
                  callback(time);
                })
              : (queued.push(callback), queued.length);
          PalmSystem.activate = () => {
            rootAudit.push('activate');
            active = true;
            queued
              .splice(0)
              .forEach((callback) => requestAnimationFrame(callback));
            document.dispatchEvent(new Event('visibilitychange'));
          };
        }
        window.seedWallpaper = savedBuiltin
          ? new Promise((resolve, reject) => {
              const request = indexedDB.open('ctv-personal-wallpaper-v1', 1);
              request.onupgradeneeded = () =>
                request.result.createObjectStore('wallpaper');
              request.onerror = reject;
              request.onsuccess = () => {
                const db = request.result,
                  tx = db.transaction('wallpaper', 'readwrite');
                tx.objectStore('wallpaper').put(
                  { envelope: null, source: 'builtin:black-hole' },
                  'slot'
                );
                tx.oncomplete = () => {
                  db.close();
                  resolve();
                };
                tx.onerror = reject;
              };
            })
          : Promise.resolve();
      },
      {
        savedBuiltin,
        earlyRoot,
        rootEdition: edition === 'root-launcher',
        handlesRelaunch:
          JSON.parse(fs.readFileSync(path.join(site, edition, 'appinfo.json')))
            .handlesRelaunch === true
      }
    );
    await page.route('**/personal-wallpaper.js', (route) =>
      route.fulfill({
        body:
          source(edition, 'personal-wallpaper.js') +
          `
      const restoreWallpaper=PersonalWallpaper.start;
      PersonalWallpaper.start=function(){return seedWallpaper.then(()=>restoreWallpaper());};`
      })
    );
    await page.route(/^https:/, (route) => route.abort());
    await page.route('**/theme-data.js', (route) =>
      route.fulfill({
        body:
          source(edition, 'theme-data.js') +
          `
      const prepareAppearance=ThemeData.prepare;
      ThemeData.prepare=function(){return prepareAppearance.apply(this,arguments).then(input=>{window.preparedAppearance=input;return input;});};`
      })
    );
    await page.route('**/preview/bridge.js', (route) =>
      route.fulfill({
        body:
          fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') +
          `
      window.CYTV_BROWSER_PREVIEW=false;
      const original=window.PalmServiceBridge.prototype.call;
      window.PalmServiceBridge.prototype.call=function(uri,raw){
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.system.updater.service/restoreProfile'){
          rootAudit.push('restore');
          if(window.earlyRoot&&rootRestoreReads++===0){
            this.onservicecallback(JSON.stringify({returnValue:true,result:null}));return;
          }
          if(window.earlyRoot==='permission'&&rootRestoreReads===2){
            rootAudit.push('permission-refused');
            this.onservicecallback(JSON.stringify({returnValue:false,errorText:'Legacy updater permissions changed; computer recovery required'}));return;
          }
          const icon='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=';
          const profile={schema:1,inventory:{apps:[{id:'readiness.app',title:'Readiness fixture',icon}],inputs:[]},config:{columns:5,dockApps:['readiness.app'],hiddenApps:[]},settings:{}};
          this.onservicecallback(JSON.stringify({returnValue:true,result:{profile,transaction:'readiness-root',version:ROOT_VERSION,phase:'verifying'}}));return;
        }
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.system.updater.service/status'&&window.earlyRoot){
          rootAudit.push('pending');
          this.onservicecallback(JSON.stringify({returnValue:true,result:{id:'readiness-root',edition:'root',phase:'installing'}}));return;
        }
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.system.updater.service/healthy'){
          rootAudit.push('healthy');window.rootHealth={payload:JSON.parse(raw),rendered:RootLauncherRendered,marker:localStorage.getItem('tvhome.theme.trial.v1'),theme:ThemeManager.current().id};
          this.onservicecallback(JSON.stringify({returnValue:true,result:{}}));return;
        }
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.root.preview.service/status'&&JSON.parse(raw).presentation==='context'){
          window.producerContext().then(()=>this.onservicecallback(JSON.stringify({returnValue:true,result:{content:true}})));return;
        }
        if(uri==='luna://com.gathin.tvhome.renewal/presentationContext'){
          window.producerContext().then(reply=>this.onservicecallback(JSON.stringify(reply)));return;
        }
        original.call(this,uri,raw);
      };`
      })
    );
    await page.route(
      /(?:themes\/ribbon\/videos\/|wallpapers\/black-hole-stream)/,
      async (route) => {
        mediaRequests++;
        await mediaGate;
        await route.continue();
      }
    );
    try {
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      // Optional media remains pending beyond two seconds without blocking appearance.
      await page.waitForTimeout(2300);
      const before = await page.evaluate(() => ({
        ready: window.RootLauncherRendered === true,
        theme: ThemeManager.current().id,
        host: window.CYTV_HOME_HOST,
        transient: !!window.HomePresentationController
      }));
      console.log(
        JSON.stringify({
          edition,
          savedBuiltin,
          before,
          queries,
          mediaRequests,
          host: 'card'
        })
      );
      assert.equal(
        before.ready,
        true,
        'verified poster/layout must become ready without optional video bytes'
      );
      assert.equal(before.theme, 'builtin:ribbon');
      if (savedBuiltin)
        assert.equal(
          await page.evaluate(() => PersonalWallpaper.state().builtinId),
          'builtin:black-hole'
        );
      assert.equal(before.host, 'card');
      assert.equal(before.transient, false);
      assert.equal(
        queries,
        0,
        'CARD readiness does not query borrowed content'
      );
      if (edition === 'root-launcher') {
        const root = await page.evaluate(() => ({
          version: ROOT_VERSION,
          health: rootHealth,
          audit: rootAudit,
          profile: localStorage.getItem(RootProfileData.key)
        }));
        assert(
          root.version && root.profile,
          'actual Root version branch and profile restore adapter ran'
        );
        assert.equal(root.health.rendered, true);
        assert.equal(root.health.theme, 'builtin:ribbon');
        assert.equal(root.health.marker, null);
        assert.equal(root.health.payload.edition, 'root');
        assert.equal(
          root.audit.includes('activate'),
          false,
          'platform owns CARD activation'
        );
        assert(root.audit.indexOf('restore') < root.audit.indexOf('healthy'));
        if (earlyRoot) {
          assert.equal(
            root.audit.filter((event) => event === 'restore').length,
            earlyRoot === 'permission' ? 3 : 2
          );
          if (earlyRoot === 'permission')
            assert(
              root.audit.indexOf('permission-refused') <
                root.audit.indexOf('healthy'),
              'a transient permission refusal still requires genuine profile/frame health'
            );
          assert(
            root.audit.indexOf('pending') < root.audit.indexOf('healthy'),
            'early CARD startup waits for the transaction without a relaunch event'
          );
        }
        assert(
          root.audit
            .slice(0, root.audit.indexOf('healthy'))
            .filter((event) => event === 'frame').length >= 2,
          'profile health follows painted readiness frames'
        );
      }
      releaseMedia();
      await page.waitForTimeout(100);
      assert.equal(
        queries,
        0,
        'media completion cannot introduce an underlay query'
      );
      assert.equal(await page.evaluate(() => RootLauncherRendered), true);
      assert.deepEqual(errors, []);
      console.log(
        'PASS ' +
          edition +
          ' ' +
          (savedBuiltin ? 'saved builtin wallpaper' : 'saved theme') +
          ' CARD appearance ready before optional media; profile/frame ordering preserved'
      );
    } finally {
      releaseMedia();
      await page.close();
    }
  }
  async function checkOverlap(edition, scenario) {
    const page = await browser.newPage(),
      errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    const names = ['app.js', 'theme-data.js', 'personal-wallpaper.js'],
      sources = {};
    for (const name of names) sources[name] = source(edition, name);
    const compiled = await compile(sources);
    try {
      await page.addInitScript(() => {
        localStorage.setItem(
          'tvhome.theme.choice.v1',
          JSON.stringify({ id: 'builtin:ribbon', title: 'Ribbon' })
        );
        window.activationCalls = 0;
        window.PalmSystem = {
          activate() {
            window.activationCalls++;
          }
        };
        window.seedWallpaper = new Promise((resolve, reject) => {
          const request = indexedDB.open('ctv-personal-wallpaper-v1', 1);
          request.onupgradeneeded = () =>
            request.result.createObjectStore('wallpaper');
          request.onerror = reject;
          request.onsuccess = () => {
            const db = request.result,
              tx = db.transaction('wallpaper', 'readwrite');
            tx.objectStore('wallpaper').put(
              { envelope: null, source: 'builtin:black-hole' },
              'slot'
            );
            tx.oncomplete = () => {
              db.close();
              resolve();
            };
            tx.onerror = reject;
          };
        });
      });
      await page.route(/^https:/, (route) => route.abort());
      await page.route('**/app.js', (route) =>
        route.fulfill({ body: compiled['app.js'] })
      );
      await page.route('**/preview/bridge.js', (route) =>
        route.fulfill({
          body:
            fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') +
            ';window.CYTV_BROWSER_PREVIEW=false;window.PREVIEW_HOME_CONTEXT="content";'
        })
      );
      await page.route('**/theme-data.js', (route) =>
        route.fulfill({
          body:
            compiled['theme-data.js'] +
            ';var realThemePrepare=ThemeData.prepare;ThemeData.prepare=function(){var args=arguments;if(window.themeRequested)return realThemePrepare.apply(ThemeData,args);window.themeRequested=true;return new Promise(function(resolve,reject){window.releaseTheme=function(fail){if(fail)reject(Error("Theme fixture failure"));else resolve(realThemePrepare.apply(ThemeData,args));};});};'
        })
      );
      await page.route('**/personal-wallpaper.js', (route) =>
        route.fulfill({
          body:
            compiled['personal-wallpaper.js'] +
            ';var realPersonalStart=PersonalWallpaper.start;PersonalWallpaper.start=function(){window.personalRequested=true;return window.personalRestore||(window.personalRestore=new Promise(function(resolve,reject){window.releasePersonal=function(fail){if(fail)reject(Error("Personal fixture failure"));else resolve(seedWallpaper.then(function(){return realPersonalStart();}));};}).then(function(value){window.personalSettled=true;return value;}));};'
        })
      );
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.waitForFunction(() => window.themeRequested === true);
      assert.equal(
        await page.evaluate(() => window.personalRequested === true),
        true,
        'personal restoration starts before theme preparation completes'
      );
      const pending = () =>
        page.evaluate(() => ({
          ready: RootLauncherRendered,
          hidden: document
            .getElementById('homeSurface')
            .classList.contains('ctv-starting'),
          activations: activationCalls
        }));
      assert.deepEqual(await pending(), {
        ready: false,
        hidden: true,
        activations: 0
      });
      const personalFirst =
        scenario === 'personal-first' ||
        scenario === 'personal-failure' ||
        scenario === 'cancel';
      await page.evaluate(
        ({ personalFirst, scenario }) =>
          personalFirst
            ? releasePersonal(scenario === 'personal-failure')
            : releaseTheme(scenario === 'theme-failure'),
        { personalFirst, scenario }
      );
      await page.waitForTimeout(80);
      if (personalFirst && scenario !== 'personal-failure')
        await page.waitForFunction(() => window.personalSettled === true);
      assert.deepEqual(
        await pending(),
        { ready: false, hidden: true, activations: 0 },
        'either pending appearance prevents reveal and activation'
      );
      if (scenario === 'cancel')
        await page.evaluate(() => ThemeManager.reset());
      await page.evaluate(
        (personalFirst) => (personalFirst ? releaseTheme() : releasePersonal()),
        personalFirst
      );
      await page.waitForFunction(() => RootLauncherRendered === true);
      const expected =
        scenario === 'theme-failure' || scenario === 'cancel'
          ? 'builtin:classic'
          : 'builtin:ribbon';
      assert.equal(
        await page.evaluate(() => ThemeManager.current().id),
        expected
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().builtinId),
        scenario === 'personal-failure' ? null : 'builtin:black-hole',
        'late theme application/recovery preserves the independently restored wallpaper'
      );
      assert.equal(
        await page.evaluate(() => activationCalls),
        0,
        'platform owns CARD foreground'
      );
      assert.deepEqual(errors, []);
      console.log(
        'PASS compiled ' +
          edition +
          ' concurrent startup ' +
          scenario +
          '; both appearance barriers and platform foreground contract retained'
      );
    } finally {
      await page.close();
    }
  }
  async function checkStartup(edition, scenario) {
    const page = await browser.newPage(),
      errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    const { version } = JSON.parse(source(edition, 'appinfo.json'));
    const transaction = 'startup-readiness',
      icon =
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=',
      profile = {
        schema: 1,
        inventory: {
          apps: [
            { id: 'readiness.first', title: 'First', icon },
            { id: 'readiness.second', title: 'Second', icon }
          ],
          inputs: []
        },
        config: { columns: 5, dockApps: ['readiness.first'], hiddenApps: [] },
        settings: {}
      };
    if (scenario === 'profile-failure') profile.inventory.apps[0].icon = '';
    await page.addInitScript((scenario) => {
      window.startupScenario = scenario;
      window.startupFaults = 0;
      window.startupHealth = [];
      window.startupLaunches = [];
      if (scenario === 'weather-sync') {
        const toggle = DOMTokenList.prototype.toggle;
        DOMTokenList.prototype.toggle = function (name) {
          if (name === 'weather-reserves-right') {
            startupFaults++;
            throw new TypeError('Weather DOM fixture failure');
          }
          return toggle.apply(this, arguments);
        };
      }
      if (scenario === 'weather-forecast') {
        localStorage.setItem(
          'tvhome.weather.v1',
          JSON.stringify({
            enabled: true,
            provider: 'open-meteo',
            preferred: 'forecast',
            mode: 'manual',
            location: { name: 'Berlin', latitude: 52.52, longitude: 13.41 }
          })
        );
        const createRange = document.createRange;
        document.createRange = function () {
          if (document.querySelector('#homeWeather[data-format="forecast"]')) {
            startupFaults++;
            throw new TypeError('Weather forecast Range fixture failure');
          }
          return createRange.call(this);
        };
      }
      if (scenario === 'render-failure') {
        const remove = DOMTokenList.prototype.remove;
        DOMTokenList.prototype.remove = function (name) {
          if (name === 'ctv-starting')
            throw new Error('Required render fixture failure');
          return remove.apply(this, arguments);
        };
      }
    }, scenario);
    await page.route(/^https:/, (route) => route.abort());
    await page.route('**/preview/bridge.js', (route) =>
      route.fulfill({
        body:
          fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') +
          `
      window.CYTV_BROWSER_PREVIEW=false;
      const startupBridge=window.PalmServiceBridge.prototype.call;
      window.PalmServiceBridge.prototype.call=function(uri,raw){
        const service='luna://com.cleanyourtv.system.updater.service/';
        if(uri===service+'restoreProfile'){
          this.onservicecallback(JSON.stringify({returnValue:true,result:{
            profile:${JSON.stringify(profile)},transaction:${JSON.stringify(transaction)},
            version:${JSON.stringify(version)},phase:'verifying'
          }}));return;
        }
        if(uri===service+'healthy'){
          startupHealth.push(JSON.parse(raw));
          this.onservicecallback(JSON.stringify({returnValue:true,result:{}}));return;
        }
        if(uri==='luna://com.webos.applicationManager/launch'){
          startupLaunches.push(JSON.parse(raw).id);
          this.onservicecallback(JSON.stringify({returnValue:true}));return;
        }
        startupBridge.call(this,uri,raw);
      };`
      })
    );
    let releaseForecast;
    if (scenario === 'weather-forecast') {
      const forecastGate = new Promise((resolve) => {
        releaseForecast = resolve;
      });
      await page.route(
        'https://api.open-meteo.com/v1/forecast?*',
        async (route) => {
          await forecastGate;
          await route.fulfill({
            headers: { 'Access-Control-Allow-Origin': '*' },
            json: {
              current: { temperature_2m: 8, weather_code: 3 },
              daily: {
                time: ['2026-11-13'],
                temperature_2m_min: [4],
                temperature_2m_max: [8],
                weather_code: [3]
              }
            }
          });
        }
      );
    }
    if (scenario === 'weather-async')
      await page.route('**/weather-data.js', (route) =>
        route.fulfill({
          body:
            source(edition, 'weather-data.js') +
            `
        const createWeatherStore=WeatherData.create;
        WeatherData.create=function(options){
          const store=createWeatherStore(options);
          store.start=function(){
            startupFaults++;
            return new Promise((resolve,reject)=>{
              window.rejectWeatherStart=()=>reject(new Error('Weather promise fixture failure'));
            });
          };
          return store;
        };`
        })
      );
    await page.route('**/install-settings.js', (route) =>
      route.fulfill({
        body:
          source(edition, 'install-settings.js') +
          `
      const listenForSettings=CYTVInstallSettings.listen;
      CYTVInstallSettings.listen=function(onError){
        window.startupSettingsListening=true;
        if(startupScenario==='settings-sync'){
          startupFaults++;
          throw new Error('Settings listener fixture failure');
        }
        if(startupScenario==='settings-async'){
          startupFaults++;
          return Promise.reject(new Error('Settings listener promise fixture failure'));
        }
        return listenForSettings(onError);
      };`
      })
    );
    try {
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      const health = () => page.evaluate(() => startupHealth);
      if (scenario === 'profile-failure') {
        await page.locator('#systemUpdates').waitFor();
        assert.equal(await page.evaluate(() => !!window.HomeUIReady), false);
        assert.deepEqual(await health(), []);
      } else {
        await page.waitForFunction(() => !!window.HomeUIReady);
        const result = await page.evaluate(() =>
          HomeUIReady.then(
            () => 'ready',
            (error) => error.message
          )
        );
        if (scenario === 'render-failure') {
          assert.equal(result, 'Required render fixture failure');
          await page.locator('#systemUpdates').waitFor();
          assert.equal(await page.evaluate(() => RootLauncherRendered), false);
          assert.deepEqual(await health(), []);
        } else {
          assert.equal(result, 'ready', edition + ' ' + scenario);
          await page.waitForFunction(() => window.startupSettingsListening);
          assert.equal(await page.evaluate(() => RootLauncherRendered), true);
          if (releaseForecast) {
            assert.equal(
              await page.evaluate(() => HomeWeather.store.state().data),
              null
            );
            releaseForecast();
            await page.waitForFunction(() => startupFaults > 0);
            assert.equal(
              await page.evaluate(() => HomeWeather.store.state().data.temp),
              8
            );
          }
          const first = page.locator(
            '#tiles .focused[data-app-id="readiness.first"]'
          );
          await first.waitFor();
          await page.keyboard.press('ArrowRight');
          await page
            .locator('#tiles .focused[data-app-id="readiness.second"]')
            .waitFor();
          await page.keyboard.press('Enter');
          assert.deepEqual(await page.evaluate(() => startupLaunches), [
            'readiness.second'
          ]);
          if (scenario !== 'weather-sync')
            assert.equal(await page.locator('#homeWeather').count(), 1);
          if (scenario === 'weather-async')
            await page.evaluate(() => rejectWeatherStart());
          // Let a theme-triggered Weather frame and unhandled rejections surface.
          await page.evaluate(
            () =>
              new Promise((resolve) =>
                requestAnimationFrame(() => requestAnimationFrame(resolve))
              )
          );
          assert.deepEqual(errors, []);
          assert.equal(
            await page.evaluate(() => startupFaults),
            scenario === 'success' ? 0 : 1
          );
          assert.equal(
            await page.evaluate(() => SystemUpdates.isOpen()),
            false
          );
          assert.deepEqual(await health(), [
            {
              edition: edition === 'root-launcher' ? 'root' : 'no-root',
              transaction,
              version
            }
          ]);
        }
      }
      assert.deepEqual(errors, []);
      console.log('PASS ' + edition + ' startup ' + scenario);
    } finally {
      if (releaseForecast) releaseForecast();
      await page.close();
    }
  }
  try {
    const editions = process.env.CYTV_READINESS_EDITION
        ? [process.env.CYTV_READINESS_EDITION]
        : ['launcher', 'root-launcher'],
      overlapOnly = process.env.CYTV_READINESS_OVERLAP_ONLY === '1',
      startupOnly = process.env.CYTV_READINESS_STARTUP;
    if (!historical && !overlapOnly)
      for (const edition of editions)
        for (const scenario of startupOnly
          ? [startupOnly]
          : [
              'weather-sync',
              'weather-async',
              'weather-forecast',
              'settings-sync',
              'settings-async',
              'success',
              'render-failure',
              'profile-failure'
            ])
          await checkStartup(edition, scenario);
    if (startupOnly) return;
    if (!overlapOnly)
      for (const edition of editions)
        for (const savedBuiltin of [false, true])
          await check(savedBuiltin, edition);
    if (!historical && !overlapOnly && editions.includes('root-launcher')) {
      await check(false, 'root-launcher', true);
      await check(false, 'root-launcher', 'permission');
    }
    if (!historical || overlapOnly)
      for (const edition of editions)
        for (const scenario of [
          'personal-first',
          'theme-first',
          'theme-failure',
          'personal-failure',
          'cancel'
        ])
          await checkOverlap(edition, scenario);
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
