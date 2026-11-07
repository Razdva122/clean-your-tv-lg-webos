'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
const {
    validateRecord,
    loadRegistry,
    verifyRemote
  } = require('../../scripts/check-theme-submissions.cjs'),
  fixture = require('./fixture.cjs');
(async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-showcase-remote-'));
  try {
    const { record, base } = fixture(root),
      entries = loadRegistry(root),
      seen = [];
    // Generated distribution B can refer to source A without a commit/hash cycle.
    validateRecord({
      ...record,
      descriptorUrl: record.descriptorUrl.replace(
        record.sourceCommit,
        'b'.repeat(40)
      )
    });
    const mock = async (url, options) => {
      seen.push(url);
      assert.equal(options.redirect, 'error');
      assert.equal(options.credentials, 'omit');
      assert.ok(
        url.startsWith(
          record.descriptorUrl.slice(
            0,
            record.descriptorUrl.lastIndexOf('/') + 1
          )
        )
      );
      return new Response(
        fs.readFileSync(
          path.join(root, base, url.slice(url.lastIndexOf('/') + 1))
        )
      );
    };
    assert.equal(await verifyRemote(entries, mock), 1);
    assert.equal(seen.length, 5);
    await assert.rejects(
      () => verifyRemote(entries, async () => new Response('wrong bytes')),
      /hash mismatch/
    );
    await assert.rejects(
      () =>
        verifyRemote(
          entries,
          async () =>
            new Response('x', { headers: { 'content-length': '999999999' } })
        ),
      /too large/
    );
    await assert.rejects(
      () => verifyRemote(entries, async () => ({ ok: true, redirected: true })),
      /unavailable/
    );
    await assert.rejects(
      () =>
        verifyRemote(entries, async () => ({
          ok: true,
          redirected: false,
          headers: new Headers(),
          body: (async function* () {
            yield Buffer.alloc(65537);
          })()
        })),
      /budget exceeded/
    );
    console.log(
      'Showcase remote transport: fixed source/distribution commits, no redirects/credentials, hashes and stream budgets passed'
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
