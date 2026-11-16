'use strict';
const assert = require('node:assert/strict');
const http = require('node:http');
const { test } = require('node:test');

test('popup transport accepts only the current session and closes stale renderers', async () => {
  assert.equal(
    typeof require('node:fs').existsSync(
      require('node:path').join(__dirname, '../screensaver/transport.js')
    ) && typeof require('../screensaver/transport').listen,
    'function'
  );
  const { listen } = require('../screensaver/transport');
  const token = 'a'.repeat(48);
  const next = 'b'.repeat(48);
  let session = { sessionId: token, generation: 3 };
  const received = [];
  const transport = await new Promise((resolve, reject) =>
    listen(
      () => session,
      (event) => {
        received.push(event);
        return { close: false, content: { mode: 'clock' } };
      },
      (err, server) => (err ? reject(err) : resolve(server)),
      (identity, req, res) => {
        assert.equal(identity, session);
        res.end('leased media');
        return true;
      }
    )
  );
  function post(header, payload, origin = 'null') {
    return new Promise((resolve, reject) => {
      const req = http.request(
        transport.endpoint,
        {
          method: 'POST',
          headers: {
            'X-CYTV-Session': header,
            'Content-Type': 'application/json',
            Origin: origin
          }
        },
        (res) => {
          let body = '';
          res.on('data', (b) => {
            body += b;
          });
          res.on('end', () => resolve([res.statusCode, JSON.parse(body)]));
        }
      );
      req.on('error', reject);
      req.end(JSON.stringify(payload));
    });
  }
  function media(id) {
    return new Promise((resolve, reject) => {
      http
        .get(transport.endpoint + '/media/' + id, (res) => {
          let body = '';
          res.on('data', (chunk) => {
            body += chunk;
          });
          res.on('end', () => resolve([res.statusCode, body]));
        })
        .on('error', reject);
    });
  }
  const event = {
    schema: 1,
    sessionId: token,
    generation: 3,
    visible: true,
    focused: true,
    mediaState: 'ready'
  };
  try {
    assert.deepEqual(await post(next, event), [403, { close: true }]);
    assert.deepEqual(await post(token, { ...event, visible: 'yes' }), [
      400,
      { close: true }
    ]);
    assert.deepEqual(await post(token, event), [
      200,
      { close: false, content: { mode: 'clock' } }
    ]);
    assert.equal((await media(next))[0], 404);
    assert.deepEqual(await media(token), [200, 'leased media']);
    session = { sessionId: next, generation: 4 };
    assert.deepEqual(await post(token, event), [403, { close: true }]);
    assert.equal((await media(token))[0], 404);
    assert.deepEqual(received, [event]);
  } finally {
    transport.close();
  }
});
