'use strict';
const assert = require('node:assert/strict');
const EventEmitter = require('node:events');
const { createRequest } = require('../renewal-service/transport');
async function scenario(status, chunks, expectedError) {
  let options,
    destroyed = false;
  const transport = {
    request: (opts, callback) => {
      options = opts;
      const req = new EventEmitter();
      req.destroy = () => {
        destroyed = true;
      };
      req.end = () =>
        process.nextTick(() => {
          const res = new EventEmitter();
          res.statusCode = status;
          callback(res);
          chunks.forEach((x) => res.emit('data', Buffer.from(x)));
          res.emit('end');
        });
      return req;
    }
  };
  const promise = createRequest(transport)('check', 'Secret123');
  if (expectedError) await assert.rejects(promise, { message: expectedError });
  else assert.deepEqual(await promise, { result: 'success' });
  assert.equal(options.hostname, 'developer.lge.com');
  assert.equal(options.rejectUnauthorized, true);
  assert.equal(
    options.path,
    '/secure/CheckDevModeSession.dev?sessionToken=Secret123'
  );
  if (expectedError) assert.equal(destroyed, true);
}
(async () => {
  await scenario(200, ['{"result":"success"}']);
  await scenario(302, [], 'http-status');
  await scenario(500, [], 'http-status');
  await scenario(200, ['invalid Secret123'], 'invalid-response');
  await scenario(200, ['x'.repeat(16385)], 'response-too-large');
  let touched = false;
  const request = createRequest({
    request: () => {
      touched = true;
    }
  });
  await assert.rejects(request('other', 'abc'), { message: 'invalid-request' });
  await assert.rejects(request('check', 'abc&foo=bar'), {
    message: 'invalid-request'
  });
  assert.equal(touched, false);
  const hanging = createRequest(
    {
      request: () => {
        const req = new EventEmitter();
        req.end = () => {};
        req.destroy = () => {};
        return req;
      }
    },
    20
  );
  await assert.rejects(hanging('check', 'abc'), { message: 'timeout' });
  console.log('8 transport scenarios passed');
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
