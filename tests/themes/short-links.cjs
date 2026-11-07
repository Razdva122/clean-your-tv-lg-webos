'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  path = require('node:path');
const data = require('../../launcher/theme-data.js'),
  entry = require('../../scripts/check-theme-submissions.cjs')
    .loadRegistry()
    .find((e) => e.record.title === 'Channel');
const descriptor = fs.readFileSync(
    path.resolve('showcase', entry.base, 'cytv-theme.json')
  ),
  url = entry.record.descriptorUrl;
let calls = [],
  target = url,
  error = null,
  pending = false,
  redirect = false;
global.XMLHttpRequest = class {
  open(method, url) {
    this.url = url;
    calls.push(url);
  }
  abort() {
    this.onabort();
  }
  send() {
    if (pending) return;
    this.status = 200;
    this.responseURL = redirect ? 'https://evil.test/' : this.url;
    this.response = Uint8Array.from(
      this.url.startsWith('https://da.gd/')
        ? Buffer.from(error || target + '\n')
        : descriptor
    ).buffer;
    this.onload();
  }
};
(async () => {
  for (const short of ['test12', 'da.gd/test12', 'https://da.gd/test12']) {
    calls = [];
    const entries = await data.resolve(short);
    assert.equal(entries[0].id, entry.record.id);
    assert.equal(entries[0].url, url);
    assert.equal(calls[0], 'https://da.gd/coshorten/test12');
    assert.equal(calls.length, 2);
  }
  for (const bad of [
    'http://192.168.1.2/p',
    'https://evil.test/theme',
    'https://da.gd/nested',
    'https://raw.githubusercontent.com/a/b/main/cytv-theme.json'
  ]) {
    target = bad;
    calls = [];
    await assert.rejects(data.resolve('da.gd/test12'));
    assert.equal(calls.length, 1, 'invalid targets never receive a request');
  }
  target = url;
  error = 'invalid provider response';
  await assert.rejects(data.resolve('da.gd/test12'));
  error = null;
  target = 'x'.repeat(4097);
  await assert.rejects(data.resolve('test12'), /size limit/);
  target = url;
  redirect = true;
  await assert.rejects(data.resolve('da.gd/test12'), /redirect/);
  redirect = false;
  for (const bad of [
    'https://da.gd.evil/test12',
    'https://da.gd@evil/test12',
    'https://da.gd/test12?x=y',
    'http://da.gd/test12',
    'https://is.gd/test12'
  ]) {
    calls = [];
    await assert.rejects(data.resolve(bad));
    assert.equal(calls.length, 0);
  }
  pending = true;
  const signal = { cancelled: false },
    result = data.resolve('da.gd/test12', signal);
  await new Promise((r) => setImmediate(r));
  signal.cancelled = true;
  signal.cancel();
  await assert.rejects(result, /Cancelled/);
  console.log(
    'PASS short-link expansion, pinned GitHub target, provider failure, redirects and cancellation'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
