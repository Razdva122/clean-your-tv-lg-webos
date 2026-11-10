'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');
const core = require('../../theme-receiver/core');
(async function () {
  const receiver = core.create({ port: 0 }),
    session = await receiver.start({ kind: 'wallpaper' });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.addInitScript(function () {
      var OriginalWorker = window.Worker;
      window.workerStops = 0;
      window.Worker = function (url) {
        var worker = new OriginalWorker(url),
          stop = worker.terminate.bind(worker);
        worker.terminate = function () {
          window.workerStops++;
          stop();
        };
        return worker;
      };
    });
    var pending;
    await page.route('**/wallpaper-heic-worker.js', (route) => {
      pending = route;
    });
    await page.goto(
      'http://127.0.0.1:' + session.port + '/wallpaper#pin=' + session.pin
    );
    const heic = {
      name: 'photo.heic',
      mimeType: 'image/heic',
      buffer: fs.readFileSync(__dirname + '/fixtures/heic/photo.heic')
    };
    await page.locator('#file').setInputFiles(heic);
    await page.getByText('Converting HEIC…', { exact: true }).waitFor();
    const png = await page.evaluate(function () {
      var canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 360;
      return canvas.toDataURL().split(',')[1];
    });
    await page.locator('#file').setInputFiles({
      name: 'replacement.png',
      mimeType: 'image/png',
      buffer: Buffer.from(png, 'base64')
    });
    await page
      .getByText('Photo ready. Check the crop and acknowledge the warning.', {
        exact: true
      })
      .waitFor();
    assert.equal(
      await page.evaluate(() => workerStops),
      1,
      'file replacement terminates old decode'
    );
    if (pending)
      await pending
        .fulfill({
          body: 'self.postMessage({error:true});',
          contentType: 'application/javascript'
        })
        .catch(() => {});
    await page.locator('#file').setInputFiles(heic);
    await page.getByText('Converting HEIC…', { exact: true }).waitFor();
    await page.locator('#cancel').click();
    assert.equal(
      await page.evaluate(() => workerStops),
      2,
      'cancel terminates decode'
    );
    assert.equal(await page.locator('#send').isDisabled(), true);
    assert.equal(await page.locator('#pin').inputValue(), '');
    if (pending)
      await pending
        .fulfill({
          body: 'self.postMessage({error:true});',
          contentType: 'application/javascript'
        })
        .catch(() => {});
    assert.match(await page.locator('#status').textContent(), /Cancelled/);
    assert.equal(receiver.status(session.sessionId).state, 'waiting');
  } finally {
    await browser.close();
    await receiver.stop(session.sessionId).catch(() => {});
  }
  console.log(
    'PASS HEIC worker replacement, cancellation and stale response handling'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
