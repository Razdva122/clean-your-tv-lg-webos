'use strict';
const assert = require('assert/strict'),
  { chromium } = require('playwright'),
  crypto = require('crypto');
const core = require('../../theme-receiver/core');
(async () => {
  const r = core.create({ port: 0 }),
    s = await r.start({ kind: 'wallpaper' }),
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
  try {
    const page = await browser.newPage({
        viewport: { width: 390, height: 844 },
        locale: 'ru-RU'
      }),
      requests = [];
    page.on('request', (q) => requests.push(q.url()));
    const url = 'http://127.0.0.1:' + s.port;
    await page.goto(url + '/wallpaper#pin=' + s.pin);
    assert.equal(await page.locator('#send').isDisabled(), true);
    assert.match(await page.locator('#warning').innerText(), /1080p/);
    assert.match(await page.locator('h1').innerText(), /Обои/);
    const png = await page.evaluate(() => {
      let c = document.createElement('canvas');
      c.width = 2400;
      c.height = 1600;
      let x = c.getContext('2d');
      x.fillStyle = '#408080';
      x.fillRect(0, 0, 2400, 1600);
      return c.toDataURL('image/png').split(',')[1];
    });
    await page.locator('#file').setInputFiles({
      name: 'video.mp4',
      mimeType: 'video/mp4',
      buffer: Buffer.from('not a photo')
    });
    assert.equal(await page.locator('#send').isDisabled(), true);
    assert.match(await page.locator('#status').innerText(), /HEIC/);
    await page.locator('#file').setInputFiles({
      name: 'fake.png',
      mimeType: 'image/png',
      buffer: Buffer.from('invalid image')
    });
    await page.waitForFunction(() =>
      /HEIC/.test(document.querySelector('#status').textContent)
    );
    assert.equal(await page.locator('#send').isDisabled(), true);
    await page.locator('#file').setInputFiles({
      name: 'photo.png',
      mimeType: 'image/png',
      buffer: Buffer.from(png, 'base64')
    });
    await page.waitForFunction(() => !document.querySelector('#zoom').disabled);
    assert.equal(await page.locator('#send').isDisabled(), true);
    await page.locator('#ack').check();
    assert.equal(await page.locator('#send').isDisabled(), false);
    await page.locator('#zoom').fill('1.5');
    await page.locator('#x').fill('30');
    await page.locator('#y').fill('60');
    await page.locator('#send').click();
    await page.waitForFunction(() =>
      /Received|Получено/.test(document.querySelector('#status').textContent)
    );
    let chunks = [],
      offset = 0,
      part;
    do {
      part = r.read(s.sessionId, offset);
      chunks.push(Buffer.from(part.data, 'base64'));
      offset = part.nextOffset;
    } while (!part.done);
    let v = JSON.parse(Buffer.concat(chunks));
    assert.equal(v.source, 'phone');
    assert.deepEqual(v.variants, []);
    assert(v.image.width <= 1920 && v.image.height <= 1080);
    assert.equal(v.image.width / v.image.height, 16 / 9);
    const bytes = Buffer.from(v.image.data, 'base64');
    assert(bytes.length <= 2 * 1024 * 1024);
    assert.equal(
      crypto.createHash('sha256').update(bytes).digest('hex'),
      v.image.sha256
    );
    assert.equal(await page.locator('#pin').inputValue(), '');
    assert(
      !requests.some((url) => url.endsWith('/wallpaper-heic-worker.js')),
      'PNG does not load the HEIC decoder'
    );
    assert(
      !requests.some(
        (x) => !x.startsWith(url + '/') && !x.startsWith('blob:' + url + '/')
      ),
      'offline assets and same-origin upload only'
    );
    assert(
      !(await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth
      ))
    );
    await page.close();
    await r.stop(s.sessionId);
    const next = await r.start({ kind: 'wallpaper' }),
      second = await browser.newPage({ locale: 'en-US' });
    await second.goto(
      'http://127.0.0.1:' + next.port + '/wallpaper#pin=' + next.pin
    );
    await second.locator('#file').setInputFiles({
      name: 'photo.png',
      mimeType: 'image/png',
      buffer: Buffer.from(png, 'base64')
    });
    await second.waitForFunction(
      () => !document.querySelector('#zoom').disabled
    );
    await second.locator('#ack').check();
    await second.locator('#cancel').click();
    assert.equal(await second.locator('#pin').inputValue(), '');
    assert.equal(await second.locator('#file').inputValue(), '');
    assert.equal(await second.locator('#send').isDisabled(), true);
    assert.equal(r.status(next.sessionId).state, 'waiting');
    await second.close();
    await r.stop(next.sessionId);
    const exp = core.create({ port: 0, ttlMs: 250 }),
      short = await exp.start({ kind: 'wallpaper' }),
      third = await browser.newPage();
    await third.goto(
      'http://127.0.0.1:' + short.port + '/wallpaper#pin=' + short.pin
    );
    await third.waitForFunction(
      () => document.querySelector('#pin').value === ''
    );
    await third.close();
  } finally {
    await browser.close();
    await r.stop(s.sessionId).catch(() => {});
  }
  console.log(
    'PASS phone actual file input, canvas crop/JPEG/hash, warning gate and real receiver upload'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
