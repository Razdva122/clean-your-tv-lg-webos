'use strict';
require('./tile.cjs');
require('./diagnostics.cjs');
const assert = require('assert'),
  fs = require('fs'),
  path = require('path');
const { chromium } = require('playwright');
const vm = require('vm');
const SOURCE_APP = path.resolve(__dirname, '../app'),
  APP = process.env.CYTV_INSTALLER_APP || SOURCE_APP,
  ID = 'a'.repeat(32),
  LEASE = 'c'.repeat(32),
  SHA = 'b'.repeat(64);
(async () => {
  assert(
    fs.existsSync(path.join(APP, 'index.html')),
    'TV installer interface is required'
  );
  if (path.resolve(APP) !== SOURCE_APP) {
    const metadata = { window: {} };
    vm.runInNewContext(
      fs.readFileSync(path.join(APP, 'candidate.js'), 'utf8'),
      metadata
    );
    const versions = metadata.window.InstallerCandidate;
    for (const key of ['root', 'root-updater', 'supervisor']) {
      assert.match(
        versions[key],
        /^\d+\.\d+\.\d+$/,
        'packaged version for ' + key
      );
    }
  }
  const catalog = fs.readFileSync(path.join(APP, 'i18n.js'), 'utf8'),
    sandbox = {
      window: {
        localStorage: {
          getItem() {
            return 'en';
          },
          setItem() {}
        },
        navigator: { language: 'en' },
        document: { documentElement: {} }
      }
    };
  vm.runInNewContext(catalog, sandbox);
  for (const [tag, selected] of [
    ['cs', 'cs'],
    ['cs-CZ', 'cs'],
    ['CS_cz', 'cs'],
    ['zh', 'zh-Hans'],
    ['zh-CN', 'zh-Hans'],
    ['zh-SG', 'zh-Hans'],
    ['zh-TW', 'zh-Hant'],
    ['zh-HK', 'zh-Hant'],
    ['zh-MO', 'zh-Hant'],
    ['zh-Hant-CN', 'zh-Hant'],
    ['zh-Hans-TW', 'zh-Hans'],
    ['ZH_hAnT_sG', 'zh-Hant'],
    ['zh-Hans-HK', 'zh-Hans']
  ]) {
    const test = {
      window: {
        localStorage: {
          getItem() {
            return null;
          }
        },
        navigator: { language: tag },
        document: { documentElement: {} }
      }
    };
    vm.runInNewContext(catalog, test);
    assert.equal(test.window.document.documentElement.lang, selected, tag);
  }
  assert.equal(Object.keys(sandbox.window.InstallerI18n.names).length, 13);
  const keys = vm.runInNewContext(
    catalog.match(/var keys\s*=\s*(\[[\s\S]*?\]);/)[1]
  );
  keys.push(
    'continueOriginal',
    'resumeConfirm',
    'homebrewDeniedTitle',
    'homebrewDeniedBody',
    'existingSetup',
    'readyHome',
    'removeProductConfirm',
    'cleanKeepInstaller',
    'cleanRestoring',
    'cleanPackages',
    'cleanFiles',
    'cleanVerified',
    'cleanContinue',
    'removeInstaller',
    'removeInstallerConfirm',
    'cleanRequestNotSaved',
    'cleanTileUnverified',
    'cleanContinueAfterRestart'
  );
  for (const locale of Object.keys(sandbox.window.InstallerI18n.names)) {
    sandbox.window.InstallerI18n.set(locale);
    for (const key of keys) {
      const text = sandbox.window.InstallerI18n.t(key);
      assert.equal(typeof text, 'string', locale + ': ' + key);
      assert(text.trim(), locale + ': ' + key);
      assert.notEqual(text, key, locale + ': translated ' + key);
    }
  }
  const czech = sandbox.window.InstallerI18n;
  sandbox.window.InstallerI18n.set('en');
  const english = keys.map((key) => czech.t(key));
  czech.set('cs');
  assert.equal(czech.names.cs, 'Čeština');
  for (const [index, key] of keys.entries())
    if (key !== 'components')
      assert.notEqual(
        czech.t(key),
        english[index],
        'Czech must not fall back to English: ' + key
      );
  let stored = 'cs';
  const persisted = {
    window: {
      localStorage: {
        getItem() {
          return stored;
        },
        setItem(key, value) {
          stored = value;
        }
      },
      navigator: { language: 'en' },
      document: { documentElement: {} }
    }
  };
  vm.runInNewContext(catalog, persisted);
  assert.equal(
    persisted.window.document.documentElement.lang,
    'cs',
    'saved Czech wins over device English'
  );
  persisted.window.InstallerI18n.set('en');
  assert.equal(stored, 'en');
  persisted.window.InstallerI18n.set('cs');
  assert.equal(stored, 'cs');
  vm.runInNewContext(catalog, persisted);
  assert.equal(
    persisted.window.document.documentElement.lang,
    'cs',
    'manual choice survives reload'
  );
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  async function fixture(
    state,
    locale = 'en',
    size = { width: 1280, height: 720 }
  ) {
    const context = await browser.newContext({ viewport: size, locale });
    // file: localStorage persistence is browser-dependent; use a stable test origin.
    await context.route('https://cytv.test/**', async (route) => {
      const name = decodeURIComponent(
        new URL(route.request().url()).pathname
      ).replace(/^\//, '');
      const base = path.resolve(APP) + path.sep;
      const vendorQr = APP === SOURCE_APP && name === 'wallpaper-qr.js';
      const file = vendorQr
        ? path.join(__dirname, '../../launcher/wallpaper-qr.js')
        : path.resolve(APP, name);
      if ((!vendorQr && !file.startsWith(base)) || !fs.existsSync(file)) {
        await route.fulfill({ status: 404, body: '' });
        return;
      }
      await route.fulfill({ path: file });
    });
    await context.addInitScript(
      ({ state, ID, LEASE, SHA, locale }) => {
        if (!localStorage.getItem('cytv.installer.language'))
          localStorage.setItem('cytv.installer.language', locale);
        window.calls = [];
        window.cleanRequests = [];
        window.model = state;
        if (state.candidate) window.InstallerCandidate = state.candidate;
        window.saved = ID;
        if (state.savedOperation) {
          localStorage.setItem('cytv.installer.operation', ID);
          if (state.edition === 'no-root')
            localStorage.setItem(
              'cytv.installer.operation.edition',
              state.edition
            );
        }
        if (state.noHbc) return;
        window.PalmServiceBridge = function () {
          this.cancel = function () {};
          this.call = function (uri, raw) {
            const command = JSON.parse(raw).command;
            window.calls.push(command);
            let reply;
            if (
              window.model.execDenied ||
              (window.model.denyStatus && command.includes(' status '))
            ) {
              this.onservicecallback(
                JSON.stringify({
                  returnValue: false,
                  errorCode: -1,
                  errorText: 'Denied method call \"exec\" for category \"/\"'
                })
              );
              return;
            }
            const clean = command.match(
              / (homebrew-remove(?:-status|-tile)?) --operation ([a-f0-9]{32})(?: |$)/
            );
            if (clean) {
              window.cleanRequests.push({
                action: clean[1],
                operation: clean[2],
                saved: localStorage.getItem('cytv.installer.clean-removal')
              });
              if (
                clean[1] === 'homebrew-remove' &&
                window.model.loseCleanReply
              ) {
                this.onservicecallback(JSON.stringify({ returnValue: false }));
                return;
              }
              reply = (clean[1] === 'homebrew-remove-tile'
                ? window.model.tileRemoval
                : window.model.cleanStatus) || {
                action: 'remove',
                state: 'pending',
                stage: 'requested',
                current: false,
                restart_required: false,
                can_resume: false
              };
            } else if (command.includes(' no-root-start ')) {
              const operation = command.match(/--operation ([a-f0-9]+)/)[1];
              reply = {
                state: 'pending',
                edition: 'no-root',
                operation,
                stage: 'pairing'
              };
            } else if (command.includes(' no-root-status '))
              reply = window.model.noRootStatus;
            else if (command.includes(' status '))
              reply = window.model.status || {
                state: 'pending',
                stage: 'root-deploy',
                operation: ID,
                action: 'install',
                lease: LEASE
              };
            else if (command.endsWith('prepare-runtime')) {
              if (window.model.runtimeFailure) {
                setTimeout(
                  () =>
                    this.onservicecallback(
                      JSON.stringify({
                        returnValue: true,
                        stdoutString: JSON.stringify({ state: 'unsupported' })
                      })
                    ),
                  75
                );
                return;
              }
              window.model = window.model.afterPrepare || {
                state: 'fresh',
                pin: window.model.pin
              };
              reply = { state: 'runtime_ready' };
            } else if (
              command.includes(' install ') ||
              command.includes(' remove ')
            ) {
              if (window.model.loseReply) {
                this.onservicecallback(JSON.stringify({ returnValue: false }));
                return;
              }
              reply = {
                state: 'pending',
                stage: 'submitted',
                operation: command.match(/--operation ([a-f0-9]+)/)[1],
                action: command.includes(' remove ') ? 'remove' : 'install'
              };
            } else if (command.endsWith('activate'))
              reply = { state: 'complete', code: 'activated' };
            else if (command.endsWith('restore'))
              reply = { state: 'complete', code: 'restored' };
            else
              reply = {
                state: window.model.state,
                edition: window.model.edition,
                operation:
                  window.model.noRootStatus &&
                  window.model.noRootStatus.operation,
                code: window.model.code,
                reason: window.model.reason,
                checks: window.model.checks,
                failure: window.model.failure,
                installation: {
                  state: window.model.state,
                  tile_protocol: window.model.legacy ? undefined : 1,
                  can_install: window.model.state === 'fresh',
                  can_maintain: window.model.state === 'installed',
                  migrate_available:
                    window.model.state === 'fresh'
                      ? Object.hasOwn(window.model, 'migrateAvailable')
                        ? window.model.migrateAvailable
                        : false
                      : undefined,
                  versions: window.model.versions
                },
                candidate_sha256: SHA,
                payload_sha256: window.model.pin,
                active_operation: window.model.active || null,
                runtime: window.model.runtime
              };
            this.onservicecallback(
              JSON.stringify({
                returnValue: true,
                stdoutString: JSON.stringify(reply)
              })
            );
          };
        };
      },
      { state, ID, LEASE, SHA, locale }
    );
    const page = await context.newPage();
    await page.goto('https://cytv.test/setup.html');
    await page.waitForSelector('[data-screen]');
    return { context, page };
  }
  try {
    const fallback = await fixture({
      state: 'no_root_ready',
      edition: 'no-root'
    });
    await fallback.page.locator('[data-screen=no-root-review]').waitFor();
    await fallback.page.locator('#install').click();
    await fallback.page
      .locator('[data-confirm-action=no-root-install]')
      .waitFor();
    await fallback.page.locator('#cancel').click();
    assert.equal(
      await fallback.page.evaluate(
        () =>
          window.calls.filter((command) => command.includes(' no-root-start '))
            .length
      ),
      0
    );
    await fallback.page.locator('#install').click();
    await fallback.page.locator('#confirm').click();
    await fallback.page.locator('[data-screen=no-root-progress]').waitFor();
    for (const [key, label] of [
      ['no-root-pairing', 'Pair with webOS'],
      ['no-root-install', 'Install No-root components'],
      ['activate-home', 'Start Home Helper']
    ]) {
      assert.equal(
        await fallback.page
          .locator('[data-check=' + key + '] .check-name')
          .textContent(),
        label
      );
    }
    const request = await fallback.page.evaluate(() => {
      const saved = localStorage.getItem('cytv.installer.operation');
      window.model.state = 'pending';
      window.model.noRootStatus = {
        state: 'complete',
        current: true,
        edition: 'no-root',
        operation: saved
      };
      return saved;
    });
    assert.match(request, /^[a-f0-9]{32}$/);
    await fallback.page.locator('#refresh').click();
    await fallback.page.locator('[data-screen=no-root-installed]').waitFor();
    assert.equal(
      await fallback.page.evaluate(() =>
        localStorage.getItem('cytv.tile.home')
      ),
      'no-root'
    );
    assert.equal(
      await fallback.page.evaluate(
        () =>
          window.calls.filter((command) => command.includes(' no-root-start '))
            .length
      ),
      1
    );
    await Promise.all([
      fallback.page.waitForRequest(
        (request) => new URL(request.url()).pathname === '/index.html'
      ),
      fallback.page.evaluate(() =>
        document.dispatchEvent(new Event('webOSRelaunch'))
      )
    ]);
    await fallback.context.close();

    const russianFallback = await fixture(
      {
        state: 'pending',
        edition: 'no-root',
        savedOperation: true,
        noRootStatus: {
          state: 'pending',
          edition: 'no-root',
          operation: ID,
          stage: 'pairing'
        }
      },
      'ru',
      { width: 1920, height: 1080 }
    );
    await russianFallback.page
      .locator('[data-screen=no-root-progress]')
      .waitFor();
    assert(
      (await russianFallback.page.evaluate(() => window.calls[0])).includes(
        ' no-root-status ' + '--operation ' + ID
      )
    );
    assert.equal(
      await russianFallback.page
        .locator('[data-check=homebrew-access]')
        .count(),
      0
    );

    for (const [key, label] of [
      ['no-root-pairing', 'Сопряжение с webOS'],
      ['no-root-install', 'Установка компонентов No-root'],
      ['activate-home', 'Запуск Home Helper']
    ]) {
      const row = russianFallback.page.locator(
        '[data-check=' + key + '] .check-name'
      );
      assert.equal(await row.textContent(), label);
      assert(await row.isVisible());
    }
    await russianFallback.context.close();

    let f = await fixture({
        state: 'fresh',
        checks: {
          'homebrew-access': 'pass',
          'python-runtime': 'pass',
          'home-compatibility': 'pass'
        }
      }),
      p = f.page;
    await p.waitForSelector('[data-screen="review"]');
    assert.equal(
      await p
        .locator('[data-check="python-runtime"]')
        .getAttribute('data-status'),
      'pass'
    );
    assert.equal(
      await p.locator('[data-check="root-user"]').getAttribute('data-status'),
      'pending'
    );
    await p.locator('#install').focus();
    assert(
      (await p.evaluate(() => calls)).every((c) =>
        c.endsWith(' inspect --prepare-supervisor')
      ),
      'opening reviews the full installation'
    );
    assert.equal(
      await p.locator('#supervisor,#migrate,input[type=checkbox]').count(),
      0
    );
    assert.equal(await p.evaluate(() => document.activeElement.id), 'install');
    assert(!(await p.locator('#content').innerText()).includes('Updater'));
    await p.locator('#language').click();
    for (const [code, font] of [
      ['zh-Hans', 'CYTVChineseSC'],
      ['zh-Hant', 'CYTVChineseTC']
    ]) {
      const choice = p.locator('#lang-' + code);
      assert.equal(await choice.getAttribute('lang'), code);
      assert(
        (
          await choice.evaluate((el) => getComputedStyle(el).fontFamily)
        ).includes(font),
        'Chinese picker labels need their packaged script font before selection'
      );
    }
    await p.locator('#back').click();
    await p.waitForSelector('[data-screen="review"]');
    await p.locator('#language').click();
    await p.locator('#lang-cs').click();
    await p.waitForSelector('[data-screen="review"]');
    assert.equal(await p.locator('html').getAttribute('lang'), 'cs');
    assert.equal(
      await p.locator('#install').textContent(),
      'Nainstalovat a aktivovat'
    );
    await p.reload();
    await p.waitForSelector('[data-screen="review"]');
    assert.equal(await p.locator('html').getAttribute('lang'), 'cs');

    await p.locator('#install').focus();
    await p.keyboard.press('ArrowDown');
    assert.notEqual(
      await p.evaluate(() => document.activeElement.id),
      'install'
    );
    await p.locator('#install').focus();
    await p.keyboard.press('Enter');
    await p.waitForSelector('[data-screen="confirm"]');
    await p.keyboard.press('Escape');
    await p.waitForSelector('[data-screen="review"]');
    assert.equal(await p.evaluate(() => document.activeElement.id), 'install');
    assert(
      (await p.evaluate(() => calls)).every((c) => c.includes(' inspect')),
      'cancel never submits'
    );
    await p.locator('#install').click();
    await p.locator('#confirm').click();
    await p.waitForSelector('[data-screen="progress"]');
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) => c.includes(' install '))
        .length,
      1
    );
    const original = await p.evaluate(() =>
      localStorage.getItem('cytv.installer.operation')
    );
    assert(
      (await p.evaluate(() => calls)).some(
        (call) =>
          call.includes(' install ') &&
          call.includes('--prepare-supervisor') &&
          !call.includes('--migrate-packaged-home') &&
          call.includes('--activate-after-install')
      ),
      'one confirmed fresh setup authorizes package installation and Home activation'
    );
    assert(
      /^[a-f0-9]{32}$/.test(original),
      'submission saves the original request'
    );
    await p.reload();
    assert.equal(
      await p.evaluate(() => localStorage.getItem('cytv.installer.operation')),
      original,
      'reload preserves the original request'
    );
    await p.waitForSelector('[data-screen="progress"]');
    assert(
      (await p.evaluate(() => calls)).some((c) =>
        c.includes(' status --operation ' + original)
      ),
      'reopening polls the original request'
    );
    assert(
      (await p.evaluate(() => calls)).every(
        (c) => c.includes(' inspect') || c.includes(' status ')
      ),
      'reopening never resubmits'
    );
    await f.context.close();
    for (const existing of [
      { state: 'fresh', migrateAvailable: true },
      { state: 'installed', legacy: true }
    ]) {
      f = await fixture(existing, 'ru');
      await f.page.waitForSelector('[data-screen="existing-installation"]');
      assert.equal(
        await f.page.locator('#install,#remove,#activate').count(),
        0
      );
      assert(
        (await f.page.evaluate(() => calls)).every((call) =>
          call.includes(' inspect')
        )
      );
      await f.context.close();
    }
    for (const [state, code, textKey] of [
      ['external_setup', 'root_setup_on_computer', 'externalRootSetup'],
      ['external_setup', 'legacy_node_on_computer', 'legacyNodeSetup'],
      ['external_setup', 'no_root_setup_on_computer', 'noRootHandoff'],
      [
        'edition_unconfirmed',
        'home_interfaces_unconfirmed',
        'editionUnconfirmed'
      ]
    ]) {
      const preflight = await fixture({ state, code });
      await preflight.page.waitForSelector('[data-screen="edition-advice"]');
      assert(
        await preflight.page.evaluate(
          (key) =>
            document
              .getElementById('content')
              .innerText.includes(InstallerI18n.t(key)),
          textKey
        )
      );
      assert.equal(
        await preflight.page
          .locator('#install,#activate,#resume,#restore')
          .count(),
        0
      );
      await preflight.context.close();
    }
    for (const [state, current, expectedScreen, textKey] of [
      ['pending', true, 'progress', 'activationPending'],
      ['unverified', true, 'recovery', 'activationUnverified'],
      ['cancelled', true, 'installed', 'activationCancelled'],
      ['finished', false, 'installed', 'readyHome'],
      ['superseded', false, 'review', 'reviewBody'],
      ['active', false, 'recovery', 'activationUnverified'],
      ['active', true, 'installed', 'activationDone']
    ]) {
      const restored = await fixture({
        state: state === 'superseded' ? 'fresh' : 'installed',
        savedOperation: true,
        status: {
          state: 'complete',
          action: 'install',
          current,
          activation: { state }
        }
      });
      await restored.page.waitForSelector(
        '[data-screen="' + expectedScreen + '"]'
      );
      assert.equal(
        await restored.page.evaluate(() =>
          Boolean(localStorage.getItem('cytv.installer.operation'))
        ),
        expectedScreen === 'progress' || expectedScreen === 'recovery'
      );
      assert(
        await restored.page.evaluate(
          (key) =>
            document
              .getElementById('content')
              .innerText.includes(InstallerI18n.t(key)),
          textKey
        )
      );
      assert(
        (await restored.page.evaluate(() => calls)).every(
          (call) => call.includes(' inspect') || call.includes(' status ')
        )
      );
      await restored.context.close();
    }
    f = await fixture({
      state: 'recovery_required',
      active: {
        operation: ID,
        lease: LEASE,
        state: 'pending',
        action: 'remove'
      }
    });
    p = f.page;
    await p.waitForSelector('[data-screen="progress"]');
    assert(
      (await p.evaluate(() => calls)).some((c) =>
        c.includes('--operation ' + ID)
      )
    );
    assert(
      !(await p.evaluate(() => calls)).some((c) =>
        c.includes('--operation ' + LEASE)
      )
    );
    await f.context.close();
    f = await fixture({
      state: 'prerequisites',
      runtime: { privateRuntimeRequired: true, requiredSpace: 335544320 }
    });
    p = f.page;
    await p.waitForSelector('[data-screen="prerequisites"]');
    assert(
      !(await p.evaluate(() => calls)).some((c) =>
        c.includes('prepare-runtime')
      )
    );
    await p.locator('#prepare').click();
    await p.locator('#confirm').click();
    await p.waitForSelector('[data-screen="review"]');
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) =>
        c.endsWith('prepare-runtime')
      ).length,
      1
    );
    await f.context.close();
    for (const [afterPrepare, screen, submits] of [
      [{ state: 'fresh', pin: SHA }, 'progress', 1],
      [
        { state: 'fresh', pin: SHA, migrateAvailable: true },
        'existing-installation',
        0
      ],
      [{ state: 'fresh', pin: SHA, migrateAvailable: null }, 'recovery', 0],
      [{ state: 'fresh', pin: 'd'.repeat(64) }, 'review', 0],
      [{ state: 'installed', pin: SHA }, 'installed', 0],
      [
        {
          state: 'external_setup',
          code: 'no_root_setup_on_computer',
          pin: SHA
        },
        'edition-advice',
        0
      ]
    ]) {
      const prepared = await fixture({
        state: 'prerequisites',
        pin: SHA,
        afterPrepare
      });
      const page = prepared.page;
      await page.locator('#install').click();
      assert(
        (await page.evaluate(() => calls)).every((call) =>
          call.includes(' inspect')
        )
      );
      await page.locator('#confirm').click();
      await page.waitForSelector('[data-screen="' + screen + '"]');
      const calls = await page.evaluate(() => window.calls);
      assert.equal(
        calls.filter((call) => call.endsWith('prepare-runtime')).length,
        1
      );
      const installs = calls.filter((call) => call.includes(' install '));
      assert.equal(installs.length, submits);
      if (submits) {
        assert(installs[0].includes('--prepare-supervisor'));
        assert(installs[0].includes('--activate-after-install'));
        assert.equal(
          installs[0].includes('--migrate-packaged-home'),
          afterPrepare.migrateAvailable === true
        );
      }
      await prepared.context.close();
    }
    f = await fixture({
      state: 'installed',
      versions: { root: '1.2.3', 'root-updater': '2.3.4' }
    });
    p = f.page;
    await p.waitForSelector('[data-screen="installed"]');
    assert((await p.locator('#versions').textContent()).includes('1.2.3'));
    assert(
      !(await p.locator('#versions').textContent()).includes('System Updater')
    );
    assert.equal(await p.locator('#install').count(), 0);
    await p.locator('#remove').click();
    await p.waitForSelector('[data-screen="confirm"]');
    assert(
      !(await p.evaluate(() => calls)).some((c) => c.includes(' remove '))
    );
    await p.keyboard.press('Escape');
    assert.equal(await p.evaluate(() => document.activeElement.id), 'remove');
    await f.context.close();
    f = await fixture({ state: 'installed', loseCleanReply: true });
    p = f.page;
    await p.locator('#remove').click();
    await p.locator('#confirm').click();
    const removal = p.locator('[data-screen="clean-removal"]');
    await removal.locator('#save-report').waitFor();
    const cleanId = await p.evaluate(() =>
      localStorage.getItem('cytv.installer.clean-removal')
    );
    assert.match(cleanId, /^[a-f0-9]{32}$/);
    assert.deepEqual(await p.evaluate(() => cleanRequests), [
      { action: 'homebrew-remove', operation: cleanId, saved: cleanId }
    ]);
    assert.equal(
      await p.evaluate(() => localStorage.getItem('cytv.installer.operation')),
      null
    );
    assert.equal(
      await p.locator('#continue-removal,#remove-installer').count(),
      0
    );
    await p.locator('#save-report').click();
    await p.locator('#diagnostic-json').waitFor();
    assert.equal(
      JSON.parse(await p.locator('#diagnostic-json').textContent()).action,
      'uninstall'
    );
    await p.locator('#back').click();
    await p.reload();
    await p.waitForSelector('[data-clean-stage="requested"]');
    assert.deepEqual(await p.evaluate(() => cleanRequests), [
      { action: 'homebrew-remove-status', operation: cleanId, saved: cleanId }
    ]);
    for (const [status, selector] of [
      [
        {
          state: 'unknown',
          stage: 'unknown',
          code: 'unknown-operation',
          can_resume: false
        },
        '#continue-removal'
      ],
      [
        {
          state: 'pending',
          stage: 'restart-required',
          restart_required: true,
          can_resume: true
        },
        '[data-clean-stage="restart-required"]'
      ],
      [
        {
          state: 'recovery_required',
          stage: 'restart-required',
          can_resume: true
        },
        '#continue-removal'
      ]
    ]) {
      await p.evaluate((status) => {
        model.cleanStatus = { action: 'remove', current: false, ...status };
      }, status);
      await p.locator('#refresh').click();
      await p.locator(selector).waitFor();
      assert.equal(await p.locator('#remove-installer').count(), 0);
      if (status.restart_required)
        assert.equal(
          await p.locator('#continue-removal').textContent(),
          'Continue after restarting'
        );
    }
    assert(
      (await p.evaluate(() => cleanRequests)).every(
        (request) => request.action === 'homebrew-remove-status'
      )
    );
    await p.evaluate(() => {
      model.loseCleanReply = false;
      model.cleanStatus = {
        action: 'remove',
        state: 'unknown',
        can_resume: false
      };
    });
    await p.locator('#continue-removal').click();
    await p.waitForSelector('[data-clean-state="unknown"]');
    assert.deepEqual((await p.evaluate(() => cleanRequests)).at(-1), {
      action: 'homebrew-remove',
      operation: cleanId,
      saved: cleanId
    });
    for (const current of [false, true]) {
      await p.evaluate((current) => {
        model.cleanStatus = {
          action: 'remove',
          state: 'complete',
          stage: 'verified-clean',
          current
        };
      }, current);
      await p.locator('#refresh').click();
      await p.waitForSelector(
        `[data-clean-state="${current ? 'complete' : 'unknown'}"]`
      );
      assert.equal(
        await p.locator('#remove-installer').count(),
        Number(current)
      );
    }
    assert.equal(
      (await p.evaluate(() => cleanRequests)).filter(
        (request) => request.action === 'homebrew-remove-tile'
      ).length,
      0
    );
    await p.evaluate(() => {
      model.tileRemoval = {
        action: 'remove',
        state: 'complete',
        stage: 'verified-clean',
        code: 'installer-removed',
        current: true
      };
    });
    await p.locator('#remove-installer').click();
    await p.waitForSelector('[data-confirm-action="remove-installer"]');
    await p.locator('#confirm').click();
    await p.waitForFunction(
      () => cleanRequests.at(-1).action === 'homebrew-remove-tile'
    );
    assert.deepEqual((await p.evaluate(() => cleanRequests)).at(-1), {
      action: 'homebrew-remove-tile',
      operation: cleanId,
      saved: cleanId
    });
    await p.waitForSelector('[data-clean-state="complete"]');
    assert.equal(await p.locator('#remove-installer,#refresh').count(), 0);
    await f.context.close();
    f = await fixture({ state: 'fresh', loseReply: true });
    p = f.page;
    await p.waitForSelector('#install');
    await p.locator('#install').click();
    await p.locator('#confirm').click();
    await p.waitForSelector('[data-screen="progress"]');
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) => c.includes(' install '))
        .length,
      1
    );
    assert.equal(await p.locator('#install').count(), 0);
    await p.locator('#refresh').click();
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) => c.includes(' install '))
        .length,
      1
    );
    await f.context.close();
    f = await fixture(
      {
        state: 'recovery_required',
        active: {
          operation: ID,
          state: 'recovery_required',
          action: 'install'
        },
        status: {
          operation: ID,
          state: 'recovery_required',
          action: 'install',
          can_resume: true
        }
      },
      'cs'
    );
    p = f.page;
    await p.waitForSelector('#resume');
    assert.equal(
      await p.locator('#resume').textContent(),
      'Pokračovat v původní operaci · Instalovat'
    );
    await p.locator('#resume').click();
    assert(
      (await p.locator('#content').textContent()).includes(
        'Odesílání neznámých balíčků zůstane zablokováno.'
      )
    );
    assert(
      !(await p.evaluate(() => calls)).some((c) => c.includes('--resume'))
    );
    await p.locator('#confirm').click();
    await p.waitForSelector('[data-screen="progress"]');
    assert(
      (await p.evaluate(() => calls)).some((c) =>
        c.endsWith('install --operation ' + 'a'.repeat(32) + ' --resume')
      )
    );
    await f.context.close();
    f = await fixture(
      {
        state: 'recovery_required',
        code: 'operation_requires_recovery',
        reason: 'restart-required',
        failure: {
          inspect_check: 'live_original_worker',
          errorText: 'secret 10.1.2.3'
        }
      },
      'ru'
    );
    p = f.page;
    await p.waitForSelector('#save-report');
    assert.match(
      await p.locator('#diagnostic-reason').textContent(),
      /нужен перезапуск/
    );
    assert.match(
      await p.locator('#diagnostic-next').textContent(),
      /Проверить статус/
    );
    await p.locator('#save-report').focus();
    await p.keyboard.press('Enter');
    await p.waitForSelector('[data-screen="diagnostic-report"]');
    assert.match(
      await p.locator('#diagnostic-storage').textContent(),
      /Отчёт сохранён/
    );
    const reportText = await p.locator('#diagnostic-json').textContent();
    const report = JSON.parse(reportText);
    assert.equal(report.homebrew.detail, 'live_original_worker');
    assert.equal(report.frontend, 'homebrew');
    assert.equal(report.schema, 1);
    assert(!reportText.includes('10.1.2.3') && !reportText.includes('secret'));
    const qr = await p.locator('#diagnostic-qr').evaluate((canvas) => {
      const { width, height } = canvas;
      const pixels = canvas.getContext('2d').getImageData(0, 0, width, height);
      return { width, height, pixels: Array.from(pixels.data) };
    });
    const decoded = require('jsqr')(
      Uint8ClampedArray.from(qr.pixels),
      qr.width,
      qr.height
    );
    assert.ok(decoded, 'the production QR is decodable');
    const reportUrl = new URL(decoded.data);
    assert.equal(reportUrl.origin, 'https://razdva122.github.io');
    assert.equal(
      reportUrl.pathname,
      '/clean-your-tv-lg-webos/support/homebrew/'
    );
    assert.equal(reportUrl.search, '');
    assert.deepEqual(
      require('../app/report-format.js').decode(reportUrl.hash),
      report
    );
    await p.keyboard.press('Escape');
    assert.equal(
      await p.evaluate(() => document.activeElement.id),
      'save-report'
    );
    await p.reload();
    await p.locator('#open-report').click();
    assert.equal(await p.locator('#diagnostic-json').textContent(), reportText);
    await p.locator('#back').click();
    await p.evaluate(() => {
      Storage.prototype.setItem = function () {
        throw new Error('storage not available');
      };
    });
    await p.locator('#save-report').click();
    assert.match(
      await p.locator('#diagnostic-storage').textContent(),
      /не смог сохранить/
    );
    const latestReport = JSON.parse(
      await p.locator('#diagnostic-json').textContent()
    );
    assert.deepEqual(
      { ...latestReport, timestamp_utc: report.timestamp_utc },
      report
    );
    await f.context.close();
    f = await fixture({ state: 'fresh' });
    p = f.page;
    await p.waitForSelector('[data-screen="review"]');
    await p.evaluate(() =>
      document.dispatchEvent(
        new CustomEvent('webOSRelaunch', {
          detail: { params: { cytvDebloat: true } }
        })
      )
    );
    await p.waitForURL('**/debloat.html');
    await p.waitForFunction(() => window.CYTVDebloatPage === true);
    await f.context.close();
    f = await fixture(
      {
        state: 'prerequisites',
        pin: SHA,
        runtimeFailure: true,
        checks: { 'homebrew-access': 'pass', 'python-runtime': 'pending' }
      },
      'ru',
      { width: 1280, height: 720 }
    );
    p = f.page;
    await p.locator('#install').click();
    await p.locator('#confirm').click();
    await p
      .locator(
        '[data-screen="checking"] [data-check="python-runtime"][data-status="running"]'
      )
      .waitFor();
    await p
      .locator('[data-check="python-runtime"][data-status="fail"]')
      .waitFor();
    await p.evaluate(() => document.fonts.ready);
    assert(
      await p
        .locator('#save-report')
        .evaluate((el) => el.getBoundingClientRect().bottom <= innerHeight),
      'the TV offers a visible report action on the failing step at 720p'
    );
    await p.locator('#save-report').click();
    const runtimeReport = JSON.parse(
      await p.locator('#diagnostic-json').textContent()
    );
    assert.equal(runtimeReport.phase, 'python-runtime');
    assert.equal(runtimeReport.reason_code, 'runtime_unconfirmed');
    await f.context.close();
    for (const savedOperation of [false, true]) {
      f = await fixture({ execDenied: true, savedOperation });
      p = f.page;
      await p.waitForSelector('[data-screen="homebrew-access"]');
      assert((await p.locator('#content').textContent()).includes('0.8.0'));
      assert((await p.locator('#content').textContent()).includes('Android'));
      assert.equal(
        await p
          .locator('#install,#activate,#remove,#restore,#prepare,#resume')
          .count(),
        0
      );
      assert.equal(
        await p.evaluate(() =>
          localStorage.getItem('cytv.installer.operation')
        ),
        savedOperation ? ID : null
      );
      assert.equal(
        (await p.evaluate(() => calls)).length,
        1,
        'denied inspect does not start runtime/status/mutation'
      );
      await p.locator('#refresh').focus();
      await p.keyboard.press('ArrowDown');
      assert.equal(
        await p.evaluate(() => document.activeElement.id),
        'save-report',
        'the first recovery action after retry is reachable with the remote'
      );
      await p.locator('#refresh').click();
      assert(
        (await p.evaluate(() => calls)).every((c) =>
          c.endsWith(' inspect --prepare-supervisor')
        ),
        'retry only inspects'
      );
      await p.evaluate(() => {
        model = { state: 'fresh', status: { state: 'unknown' } };
      });
      await p.locator('#refresh').click();
      await p.waitForSelector(
        savedOperation ? '[data-screen="recovery"]' : '[data-screen="review"]'
      );
      assert(
        !(await p.evaluate(() => calls)).some((c) => c.includes(' install ')),
        'recovery never resubmits'
      );
      await f.context.close();
    }
    f = await fixture({ state: 'fresh' });
    p = f.page;
    await p.waitForSelector('#install');
    await p.locator('#install').click();
    await p.evaluate(() => {
      model.execDenied = true;
    });
    await p.locator('#confirm').click();
    await p.waitForSelector('[data-screen="homebrew-access"]');
    assert(
      /^[a-f0-9]{32}$/.test(
        await p.evaluate(() => localStorage.getItem('cytv.installer.operation'))
      )
    );
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) => c.includes(' install '))
        .length,
      1
    );
    assert.equal(await p.locator('#restore,#resume,#install').count(), 0);
    await f.context.close();
    f = await fixture({
      state: 'fresh',
      savedOperation: true,
      denyStatus: true
    });
    p = f.page;
    await p.waitForSelector('[data-screen="homebrew-access"]');
    assert.deepEqual(
      (await p.evaluate(() => calls)).map((c) =>
        c.includes(' status ') ? 'status' : 'inspect'
      ),
      ['inspect', 'status']
    );
    assert.equal(
      await p.evaluate(() => localStorage.getItem('cytv.installer.operation')),
      ID
    );
    assert.equal(await p.locator('#restore,#resume').count(), 0);
    await p.evaluate(() => {
      model.denyStatus = false;
      model.status = { state: 'unknown' };
    });
    await p.locator('#refresh').click();
    await p.waitForSelector('[data-screen="recovery"]');
    await f.context.close();
    f = await fixture({ state: 'fresh', savedOperation: true });
    p = f.page;
    await p.waitForSelector('[data-screen="progress"]');
    await p.evaluate(() => {
      model.denyStatus = true;
    });
    await p.waitForSelector('[data-screen="homebrew-access"]', {
      timeout: 12000
    });
    assert.equal(
      (await p.evaluate(() => calls)).filter((c) => c.includes(' status '))
        .length,
      2,
      'poll denial stops the polling screen'
    );
    assert.equal(
      await p.evaluate(() => localStorage.getItem('cytv.installer.operation')),
      ID
    );
    assert.equal(await p.locator('#restore,#resume').count(), 0);
    await f.context.close();
    f = await fixture({ state: 'fresh', noHbc: true });
    p = f.page;
    await p.waitForSelector('[data-screen="unsupported"]');
    assert.equal(await p.locator('#install').count(), 0);
    await f.context.close();
    f = await fixture({
      state: 'installed',
      versions: { root: '1.2.3', 'root-updater': '2.3.4' },
      status: { state: 'complete', current: false, action: 'install' }
    });
    p = f.page;
    await p.waitForSelector('#activate');
    await p.evaluate(
      (id) => localStorage.setItem('cytv.installer.operation', id),
      ID
    );
    await p.reload();
    await p.waitForSelector('[data-screen="installed"]');
    assert.equal(await p.locator('#install').count(), 0);
    await f.context.close();
    for (const locale of [
      'en',
      'de',
      'es',
      'pt-BR',
      'fr',
      'it',
      'ko',
      'hi',
      'pl',
      'ru',
      'cs',
      'zh-Hans',
      'zh-Hant'
    ])
      for (const size of [
        { width: 1280, height: 720 },
        { width: 1920, height: 1080 }
      ]) {
        f = await fixture(
          {
            state: 'installed',
            versions: { root: '1.2.3', 'root-updater': '2.3.4' }
          },
          locale,
          size
        );
        p = f.page;
        await p.waitForSelector('[data-screen="installed"]');
        await p.evaluate(() => document.fonts.ready);
        const metrics = await p.evaluate(() => ({
          width: innerWidth,
          scroll: document.documentElement.scrollWidth,
          font: parseFloat(
            getComputedStyle(document.querySelector('#content p')).fontSize
          ),
          lang: document.documentElement.lang
        }));
        assert(metrics.scroll <= metrics.width, JSON.stringify(metrics));
        assert(metrics.font >= 24);
        assert.equal(metrics.lang, locale);
        await p.locator('#remove').focus();
        await p.keyboard.press('ArrowDown');
        const rect = await p.evaluate(() => {
          const r = document.activeElement.getBoundingClientRect();
          return { top: r.top, bottom: r.bottom };
        });
        assert(
          rect.top >= 0 && rect.bottom <= size.height,
          'remote focus remains visible'
        );
        if (
          process.env.CYTV_SCREENSHOTS &&
          ['de', 'hi', 'ko'].includes(locale)
        ) {
          const dest = path.join(
            process.env.CYTV_SCREENSHOTS,
            locale + '-' + size.width + '.png'
          );
          await p.screenshot({ path: dest });
          console.log('SCREENSHOT', dest, JSON.stringify(metrics));
        }
        await p.evaluate(() => {
          model.execDenied = true;
          document.dispatchEvent(new Event('visibilitychange'));
        });
        await p.waitForSelector('[data-screen="homebrew-access"]');
        assert.equal(await p.locator('#install,#restore,#prepare').count(), 0);
        assert(
          (await p.locator('#content').textContent()).includes('0.8.0'),
          locale + ' localized prerequisite'
        );
        await p.locator('#refresh').focus();
        await p.keyboard.press('ArrowDown');
        const denialRect = await p.locator('#close').boundingBox();
        assert(
          denialRect.y >= 0 && denialRect.y + denialRect.height <= size.height,
          locale + ' denial focus visible'
        );
        if (process.env.CYTV_SCREENSHOTS && ['de', 'hi', 'ko'].includes(locale))
          await p.screenshot({
            path: path.join(
              process.env.CYTV_SCREENSHOTS,
              'denied-' + locale + '-' + size.width + '.png'
            )
          });
        await f.context.close();
      }
    console.log(
      'PASS TV UI: exact exec denial at inspect/submit/status/poll, retained-request recovery, inspect-only reopen, durable foreign request, explicit runtime, cancellation, one submission/lost reply, installed versions, D-pad/Back/focus, thirteen locales at 720p/1080p'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
