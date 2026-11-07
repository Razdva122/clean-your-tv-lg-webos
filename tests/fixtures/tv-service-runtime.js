// ES5 fixture executed by the TV's actual Node runtimes against compiled files.
'use strict';
var assert = require('assert');
var path = require('path');
var https = require('https');
var EventEmitter = require('events').EventEmitter;
var transport = require(path.join(process.argv[2], 'transport'));
var address =
  'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/update.json';
assert.strictEqual(
  transport.allowed(address),
  true,
  'old Node must accept the fixed release URL'
);
[
  'https://release-assets.githubusercontent.com/asset?token=fixture',
  'https://objects.githubusercontent.com/asset',
  address.replace('github.com/', 'github.com:443/')
].forEach(function (url) {
  assert.strictEqual(transport.allowed(url), true, url);
});
[
  'http://github.com/Razdva122/clean-your-tv-lg-webos/releases/foo',
  'https://github.com/other/project/releases/foo',
  'https://user:pass@github.com/Razdva122/clean-your-tv-lg-webos/releases/foo',
  'https://github.com:444/Razdva122/clean-your-tv-lg-webos/releases/foo',
  'https://github.com.evil.example/Razdva122/clean-your-tv-lg-webos/releases/foo',
  'https://127.0.0.1/asset',
  'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/../private',
  'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/%2e%2e/private',
  '//github.com/Razdva122/clean-your-tv-lg-webos/releases/foo'
].forEach(function (url) {
  assert.strictEqual(transport.allowed(url), false, url);
});
var original = https.get;
var responses, requested;
https.get = function (options, callback) {
  requested.push(options);
  assert.strictEqual(options.rejectUnauthorized, true);
  assert.ok(options.ca.indexOf('BEGIN CERTIFICATE') >= 0);
  var reply = responses.shift();
  assert.ok(reply, 'unexpected network request');
  var request = new EventEmitter();
  request.destroy = function () {};
  setImmediate(function () {
    var response = new EventEmitter();
    response.statusCode = reply.status;
    response.headers =
      reply.location === undefined ? {} : { location: reply.location };
    response.resume = response.destroy = function () {};
    callback(response);
    if (reply.status === 200) {
      response.emit('data', Buffer.from(reply.body));
      response.emit('end');
    }
  });
  return request;
};
function download(replies) {
  responses = replies;
  requested = [];
  return transport.get(address);
}
function rejected(replies, requests) {
  return download(replies).then(
    function () {
      throw Error('unexpected accepted redirect');
    },
    function () {
      assert.strictEqual(
        requested.length,
        requests,
        'reject before contacting an unapproved destination'
      );
    }
  );
}
download([
  {
    status: 302,
    location:
      '/Razdva122/clean-your-tv-lg-webos/releases/download/test/update.json'
  },
  { status: 302, location: '//release-assets.githubusercontent.com/fixture' },
  { status: 200, body: '{"ok":true}' }
])
  .then(function (body) {
    assert.strictEqual(body, '{"ok":true}');
    assert.strictEqual(
      requested[1].path,
      '/Razdva122/clean-your-tv-lg-webos/releases/download/test/update.json'
    );
    assert.strictEqual(
      requested[2].hostname,
      'release-assets.githubusercontent.com'
    );
    return rejected(
      [{ status: 302, location: 'https://127.0.0.1/private' }],
      1
    );
  })
  .then(function () {
    return rejected([{ status: 302, location: '../../../private' }], 1);
  })
  .then(function () {
    return rejected([{ status: 302 }], 1);
  })
  .then(function () {
    return rejected(
      [
        { status: 302, location: address },
        { status: 302, location: address },
        { status: 302, location: address },
        { status: 302, location: address }
      ],
      4
    );
  })
  .then(
    function () {
      https.get = original;
      console.log(
        'PASS updater transport: old-Node URL policy, HTTPS options and bounded redirects'
      );
    },
    function (error) {
      https.get = original;
      console.error(error.stack);
      process.exitCode = 1;
    }
  );
