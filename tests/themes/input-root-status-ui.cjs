// Real Root launcher with denied direct EIM and bounded broker snapshots; no TV access.
const { assert, chromium, stage, open } = require('./browser.cjs');
(async () => {
  const site = stage(),
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
  try {
    const context = await browser.newContext({ locale: 'en-US' });
    await context.addInitScript(() => {
      let ctor, inventory;
      Object.defineProperty(window, 'TV_APPS', {
        configurable: true,
        get() {
          return inventory;
        },
        set(value) {
          inventory = value;
          inventory.inputs = inventory.inputs.map((input) => ({
            ...input,
            appId: input.appId.replace('preview.hdmi', 'com.webos.app.hdmi')
          }));
        }
      });
      window.inputReads = [];
      window.pendingInputs = [];
      window.holdInputs = false;
      window.inputSnapshot = {
        returnValue: true,
        devices: [
          {
            id: 'HDMI_1',
            appId: 'com.webos.app.hdmi1',
            label: 'HDMI 1',
            connected: true
          },
          {
            id: 'HDMI_2',
            appId: 'com.webos.app.hdmi2',
            label: 'HDMI 2',
            connected: false
          }
        ]
      };
      Object.defineProperty(window, 'PalmServiceBridge', {
        configurable: true,
        set(value) {
          ctor = value;
        },
        get() {
          if (ctor && !ctor.inputRecorded && ctor.prototype.call) {
            const call = ctor.prototype.call;
            ctor.prototype.call = function (uri, raw) {
              if (uri === 'luna://com.webos.service.eim/getAllInputStatus') {
                inputReads.push({ uri, payload: JSON.parse(raw) });
                this.onservicecallback(
                  JSON.stringify({
                    returnValue: false,
                    errorText:
                      'Denied method call getAllInputStatus for category /'
                  })
                );
                return;
              }
              if (
                uri ===
                  'luna://com.cleanyourtv.root.preview.service/listApps' &&
                JSON.parse(raw).inputs === true
              ) {
                inputReads.push({ uri, payload: JSON.parse(raw) });
                const answer = () =>
                  this.onservicecallback(JSON.stringify(inputSnapshot));
                if (holdInputs) pendingInputs.push(answer);
                else setTimeout(answer, 30);
                return;
              }
              return call.apply(this, arguments);
            };
            ctor.inputRecorded = true;
          }
          return ctor;
        }
      });
    });
    const { page, errors } = await open(context, site, 'root-launcher');
    const reads = () => page.evaluate(() => inputReads);
    assert.deepEqual(
      await reads(),
      [
        {
          uri: 'luna://com.cleanyourtv.root.preview.service/listApps',
          payload: { inputs: true }
        }
      ],
      'Root never calls permission-denied direct EIM'
    );
    await page.evaluate(() => (holdInputs = true));
    await page.evaluate(() =>
      HomeLayoutState.setThemeLayout({
        preset: 'dock-grid',
        columns: 5,
        spacingScale: 1,
        textScale: 1,
        focusScale: 1.1,
        inputs: 'shelf'
      })
    );
    assert.deepEqual(
      await page.locator('.ctv-input-status').allTextContents(),
      ['Connected', 'Not connected', '']
    );
    await page.evaluate(() => {
      holdInputs = true;
      document.dispatchEvent(new Event('visibilitychange'));
      document.dispatchEvent(new Event('webOSRelaunch'));
      window.dispatchEvent(new Event('focus'));
    });
    assert.equal(
      await page.evaluate(() => pendingInputs.length),
      1,
      'foreground lifecycle events coalesce one pending snapshot'
    );
    await page.evaluate(() => pendingInputs.shift()());
    await page.waitForTimeout(100);
    assert.equal(
      (await reads()).length,
      2,
      'snapshot render does not feed another read'
    );
    await page.keyboard.press('ArrowUp');
    assert.equal(
      await page.evaluate(() => pendingInputs.length),
      1,
      'a new shelf selection explicitly refreshes status'
    );
    await page.evaluate(() => {
      inputSnapshot.devices[0].deviceName = 'Console';
      pendingInputs.shift()();
    });
    assert.equal(
      await page
        .locator('.ctv-input-tile.is-focused .ctv-input-status')
        .textContent(),
      'Console'
    );
    await page.waitForTimeout(100);
    assert.equal(
      (await reads()).length,
      3,
      'a changed snapshot remounts selection without another read'
    );
    await page.waitForFunction(() =>
      document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview')
    );
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await page.locator('.ctv-input-preview').count(),
      0,
      'known disconnected source stops media'
    );
    assert.equal(
      await page.evaluate(() => pendingInputs.length),
      1,
      'moving to another source reads a fresh snapshot'
    );
    await page.evaluate(() => {
      inputSnapshot = { returnValue: false };
      pendingInputs.shift()();
    });
    assert.equal(
      await page
        .locator('.ctv-input-tile.is-connected,.ctv-input-tile.is-disconnected')
        .count(),
      0,
      'failed read clears stale connection state'
    );
    assert.deepEqual(
      await page.locator('.ctv-input-status').allTextContents(),
      ['', ''],
      'inventory fallback has unknown status'
    );
    assert.equal(
      (await reads()).length,
      4,
      'failure has no retry or render feedback'
    );
    await page.locator('.ctv-input-tile').first().hover();
    await page.evaluate(() => pendingInputs.shift()());
    await page.waitForFunction(() =>
      document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview')
    );
    assert.equal(
      await page.locator('.ctv-input-preview').count(),
      1,
      'unknown metadata preserves existing HDMI preview behavior'
    );
    assert.equal(
      (await reads()).length,
      5,
      'selecting the unknown real HDMI port reads once without retries'
    );
    await page.locator('#btnSettings').click();
    assert.equal(
      await page.evaluate(() => pendingInputs.length),
      1,
      'opening Settings reads one fresh Root snapshot'
    );
    await page.evaluate(() => HomeInputShelf.refresh());
    assert.equal(
      await page.evaluate(() => pendingInputs.length),
      1,
      'Settings refreshes coalesce while pending'
    );
    await page.evaluate(() => {
      inputSnapshot = {
        returnValue: true,
        devices: [
          {
            id: 'HDMI_1',
            appId: 'com.webos.app.hdmi1',
            label: 'HDMI 1',
            connected: true
          }
        ]
      };
      pendingInputs.shift()();
    });
    await page.waitForTimeout(1200);
    assert.equal(
      await page.locator('.ctv-input-preview').count(),
      0,
      'snapshot response cannot start media beneath Settings'
    );
    assert.equal(
      (await reads()).length,
      6,
      'Settings snapshot rendering makes no feedback read'
    );
    await page.evaluate(() => (holdInputs = false));
    await page.keyboard.press('Escape');
    await page.locator('.ctv-input-tile').first().hover();
    await page.waitForFunction(() =>
      document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview')
    );
    await page.evaluate(() => window.dispatchEvent(new Event('blur')));
    assert.equal(
      await page.locator('.ctv-input-preview').count(),
      0,
      'blur stops real HDMI media'
    );
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await page.waitForFunction(() =>
      document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview')
    );
    const beforeHidden = (await reads()).length;
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event('focus'));
    });
    assert.equal(
      await page.locator('.ctv-input-preview').count(),
      0,
      'hidden Home stops real HDMI media'
    );
    assert.equal(
      (await reads()).length,
      beforeHidden,
      'hidden Home makes no interaction refresh'
    );
    assert.deepEqual(errors, []);
    await context.close();
  } finally {
    await browser.close();
  }
  console.log(
    'PASS Root broker input snapshot, interaction coalescence, no render loop and failure clears stale status'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
