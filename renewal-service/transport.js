'use strict';
var validToken = require('./renewal').validToken;
function createRequest(https, timeoutMs) {
  https = https || require('https');
  timeoutMs = timeoutMs || 10000;
  return function request(operation, token) {
    return new Promise(function (resolve, reject) {
      if (
        (operation !== 'check' && operation !== 'reset') ||
        !validToken(token)
      ) {
        reject(new Error('invalid-request'));
        return;
      }
      var finished = false,
        req,
        timer;
      function fail(code) {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        if (req) req.destroy();
        reject(new Error(code));
      }
      timer = setTimeout(function () {
        fail('timeout');
      }, timeoutMs);
      try {
        // Legacy Node reads one certificate per entry in the ca option.
        var ca = require('fs').readFileSync(
          __dirname + '/ca-bundle.crt',
          'utf8'
        );
        req = https.request(
          {
            hostname: 'developer.lge.com',
            port: 443,
            method: 'GET',
            path:
              '/secure/' +
              (operation === 'check' ? 'Check' : 'Reset') +
              'DevModeSession.dev?sessionToken=' +
              encodeURIComponent(token),
            rejectUnauthorized: true,
            agent: false,
            ca:
              ca.match(
                /-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----/g
              ) || [],
            headers: { Accept: 'application/json' }
          },
          function (res) {
            if (res.statusCode !== 200) {
              fail('http-status');
              return;
            }
            var chunks = [],
              size = 0;
            res.on('data', function (chunk) {
              if (finished) return;
              size += chunk.length;
              if (size > 16384) {
                fail('response-too-large');
                return;
              }
              chunks.push(chunk);
            });
            res.on('error', function () {
              fail('network-error');
            });
            res.on('aborted', function () {
              fail('network-error');
            });
            res.on('end', function () {
              if (finished) return;
              var data;
              try {
                data = JSON.parse(Buffer.concat(chunks).toString('utf8'));
              } catch (_) {
                fail('invalid-response');
                return;
              }
              if (!data || typeof data !== 'object' || Array.isArray(data)) {
                fail('invalid-response');
                return;
              }
              finished = true;
              clearTimeout(timer);
              resolve(data);
            });
          }
        );
        req.on('error', function () {
          fail('network-error');
        });
        req.end();
      } catch (_) {
        fail('network-error');
      }
    });
  };
}
module.exports = { createRequest: createRequest };
