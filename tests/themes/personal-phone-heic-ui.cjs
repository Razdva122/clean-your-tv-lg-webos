'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const { webkit, chromium } = require('playwright');
const core = require('../../theme-receiver/core');
const photo = fs.readFileSync(__dirname + '/fixtures/heic/photo.heic');
async function run(engine, supported) {
  const receiver = core.create({ port: 0 });
  const session = await receiver.start({ kind: 'wallpaper' });
  const browser = await engine.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 390, height: 844 }
    });
    const origin = 'http://127.0.0.1:' + session.port;
    const requests = [];
    page.on('request', (request) => requests.push(request.url()));
    await page.goto(origin + '/wallpaper#pin=' + session.pin);
    assert.match(
      await page.locator('#file').getAttribute('accept'),
      /image\/heic/
    );
    // Extensions and MIME labels alone must not bypass content checks.
    for (const buffer of [
      Buffer.from('not an image'),
      Buffer.from([
        0, 0, 0, 24, 102, 116, 121, 112, 105, 115, 111, 109, 0, 0, 0, 0, 105,
        115, 111, 109, 0, 0, 0, 0
      ])
    ]) {
      await page
        .locator('#file')
        .setInputFiles({ name: 'fake.heic', mimeType: 'image/heic', buffer });
      await page.getByText(/Choose a valid JPG, PNG or HEIC/).waitFor();
      assert.equal(await page.locator('#send').isDisabled(), true);
    }
    // A recognized but truncated HEIC must fail decoding without enabling upload.
    await page.locator('#file').setInputFiles({
      name: 'broken.heic',
      mimeType: 'image/heic',
      buffer: photo.subarray(0, photo.readUInt32BE(0))
    });
    await page.getByText(/Could not open this HEIC photo/).waitFor();
    assert.equal(await page.locator('#send').isDisabled(), true);
    // iPhone's Files picker may report no MIME type or a generic MIME type.
    for (const mimeType of [
      '',
      'application/octet-stream',
      'image/heif',
      'image/heic'
    ]) {
      await page
        .locator('#file')
        .setInputFiles({ name: 'iPhone.HEIC', mimeType, buffer: photo });
      if (supported)
        await page.waitForFunction(
          () => !document.querySelector('#zoom').disabled
        );
      else await page.getByText(/Could not open this HEIC photo/).waitFor();
    }
    if (!supported) {
      await page.getByText(/Could not open this HEIC photo/).waitFor();
      assert.equal(await page.locator('#send').isDisabled(), true);
      assert.equal(receiver.status(session.sessionId).state, 'waiting');
    } else {
      await page.waitForFunction(
        () => !document.querySelector('#zoom').disabled
      );
      assert.match(await page.locator('#status').textContent(), /Photo ready/);
      assert.equal(
        await page.locator('#send').isDisabled(),
        true,
        'quality warning still requires acknowledgement'
      );
      // Real default iPhone 24 MP dimensions exceed the former 24,000,000 guard.
      await page.locator('#file').setInputFiles({
        name: 'iPhone-24MP.HEIC',
        mimeType: 'image/heic',
        buffer: fs.readFileSync(__dirname + '/fixtures/heic/iphone-24mp.heic')
      });
      await page.waitForFunction(
        () => !document.querySelector('#zoom').disabled
      );
      assert.equal(
        await page.locator('#preview').getAttribute('width'),
        '1920'
      );
      assert.equal(
        await page.locator('#preview').getAttribute('height'),
        '1080'
      );
      await page.locator('#ack').check();
      await page.locator('#send').click();
      await page.getByText(/Received by TV/).waitFor();
      const chunks = [];
      let offset = 0,
        part;
      do {
        part = receiver.read(session.sessionId, offset);
        chunks.push(Buffer.from(part.data, 'base64'));
        offset = part.nextOffset;
      } while (!part.done);
      const envelope = JSON.parse(Buffer.concat(chunks));
      assert.equal(envelope.image.mediaType, 'image/jpeg');
      assert.equal(envelope.image.width, 1920);
      assert.equal(envelope.image.height, 1080);
      const jpeg = Buffer.from(envelope.image.data, 'base64');
      assert.equal(jpeg[0], 255);
      assert.equal(jpeg[1], 216);
      assert.equal(
        crypto.createHash('sha256').update(jpeg).digest('hex'),
        envelope.image.sha256
      );
      assert.deepEqual(envelope.variants, []);
      assert.equal(await page.locator('#pin').inputValue(), '');
    }
    assert(
      !requests.some(
        (url) =>
          !url.startsWith(origin + '/') &&
          !url.startsWith('blob:' + origin + '/')
      ),
      'no external conversion service or remote decoder'
    );
    await page.close();
  } finally {
    await browser.close();
    await receiver.stop(session.sessionId).catch(() => {});
  }
}
(async () => {
  await run(webkit, true);
  await run(chromium, false);
  console.log(
    'PASS actual HEIC decoding, phone crop/JPEG upload and unsupported-browser guidance'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
