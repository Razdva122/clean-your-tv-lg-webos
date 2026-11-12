'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs'),
  path = require('node:path'),
  vm = require('node:vm');
const EventEmitter = require('node:events'),
  tls = require('node:tls');
const createRequire = require('node:module').createRequire;

(async function () {
  let reference;
  for (const file of [
    'renewal-service/transport.js',
    'updater-service/transport.js',
    'root-edition/updater/fetch.js'
  ]) {
    const filename = path.resolve(file),
      localRequire = createRequire(filename);
    const calls = [];
    function request(options, callback) {
      calls.push(options);
      const req = new EventEmitter();
      req.destroy = function () {};
      req.end = function () {
        setImmediate(function () {
          const res = new EventEmitter();
          res.statusCode = 200;
          callback(res);
          res.emit('data', Buffer.from('{"result":"success"}'));
          res.emit('end');
        });
      };
      return req;
    }
    const https = {
      request,
      get: function (options, callback) {
        assert.equal(
          arguments.length,
          2,
          'Node 8 HTTPS requires get(options, callback)'
        );
        const req = request(options, callback);
        req.end();
        return req;
      }
    };
    const context = {
      require: (n) => (n === 'https' ? https : localRequire(n)),
      module: { exports: {} },
      __dirname: path.dirname(filename),
      URL: undefined,
      Buffer,
      setTimeout,
      clearTimeout
    };
    vm.runInNewContext(fs.readFileSync(filename, 'utf8'), context, {
      filename
    });
    const api = context.module.exports;
    if (api.createRequest) await api.createRequest()('check', 'TestToken');
    else
      await api.get(
        'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/update.json',
        file.startsWith('root-edition/') ? 65536 : undefined
      );
    assert.equal(calls.length, 1, file);
    const options = calls[0];
    assert.equal(
      options.rejectUnauthorized,
      true,
      file + ' must verify certificates'
    );
    assert.equal(
      options.checkServerIdentity,
      undefined,
      file + ' must retain hostname validation'
    );
    const bundle = fs.readFileSync(
      path.join(path.dirname(filename), 'ca-bundle.crt'),
      'utf8'
    );
    const certificates = bundle.match(
      /-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----/g
    );
    assert(certificates.length > 1, file);
    if (!file.startsWith('root-edition/')) {
      assert(Array.isArray(options.ca), file + ' must support legacy Node');
      assert.deepEqual(Array.from(options.ca), certificates, file);
    } else {
      assert.equal(options.ca, bundle, file);
    }
    tls.createSecureContext({ ca: options.ca });
    if (reference)
      assert.deepEqual(
        certificates,
        reference,
        'clients must use the same CA snapshot'
      );
    reference = certificates;
  }
  console.log(
    'PASS all outbound HTTPS clients use a parseable CA bundle and strict TLS'
  );
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
