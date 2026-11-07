'use strict';
var https = require('https');
var urls = require('url');
// Only the fixed project's release assets may be requested. Redirects are limited
// to GitHub's asset CDN. No cookies, authorization headers or private addresses.
function allowed(raw) {
  try {
    if (typeof raw !== 'string') return false;
    var u = urls.parse(raw);
    return (
      u.protocol === 'https:' &&
      !u.auth &&
      (!u.port || u.port === '443') &&
      !/(^|\/)(\.|%2e){1,2}(\/|$)/i.test(u.pathname || '') &&
      ((u.hostname === 'github.com' &&
        u.pathname.indexOf('/Razdva122/clean-your-tv-lg-webos/releases/') ===
          0) ||
        u.hostname === 'release-assets.githubusercontent.com' ||
        u.hostname === 'objects.githubusercontent.com')
    );
  } catch (_) {
    return false;
  }
}
function get(url, redirects) {
  return new Promise(function (resolve, reject) {
    if (!allowed(url) || (redirects || 0) > 3)
      return reject(Error('url-rejected'));
    var settled = false,
      total = 0,
      chunks = [],
      timer;
    function done(e, data) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (e) reject(Error('download-failed'));
      else resolve(data);
    }
    var options = Object.assign(urls.parse(url), {
      rejectUnauthorized: true,
      ca: require('fs').readFileSync(__dirname + '/ca-bundle.crt', 'utf8'),
      headers: {
        'User-Agent': 'CleanYourTV-Updater',
        'Accept': 'application/json'
      }
    });
    var req = https.get(options, function (res) {
      if ([301, 302, 303, 307, 308].indexOf(res.statusCode) >= 0) {
        res.resume();
        clearTimeout(timer);
        if (typeof res.headers.location !== 'string' || !res.headers.location) {
          done(Error('redirect'));
          return;
        }
        get(urls.resolve(url, res.headers.location), (redirects || 0) + 1).then(
          function (x) {
            done(null, x);
          },
          done
        );
        return;
      }
      if (res.statusCode !== 200) {
        res.resume();
        done(Error('http'));
        return;
      }
      res.on('data', function (c) {
        total += c.length;
        if (total > 65536) {
          res.destroy();
          done(Error('size'));
        } else chunks.push(c);
      });
      res.on('end', function () {
        done(null, Buffer.concat(chunks).toString('utf8'));
      });
      res.on('error', done);
    });
    timer = setTimeout(function () {
      req.destroy();
      done(Error('timeout'));
    }, 15000);
    req.on('error', done);
  });
}
module.exports = { get: get, allowed: allowed };
