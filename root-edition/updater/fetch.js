'use strict';
// Standalone pinned verifier/downloader; no application package code is executed.
var crypto = require('crypto'),
  https = require('https'),
  fs = require('fs');
var URL = require('url').URL;
var REPO = 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/';
var APP = 'com.cleanyourtv.root.preview',
  MAX = 32 * 1024 * 1024;
function version(v) {
  if (typeof v !== 'string' || !/^\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(v))
    throw Error('invalid-version');
  return v.split('.').map(Number);
}
function compare(a, b) {
  a = version(a);
  b = version(b);
  for (var i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] > b[i] ? 1 : -1;
  return 0;
}
function allowed(raw) {
  try {
    var u = new URL(raw);
    return (
      u.protocol === 'https:' &&
      !u.username &&
      !u.password &&
      !u.port &&
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
function feedName(resolution) {
  if (['1280x720', '1920x1080'].indexOf(resolution) < 0)
    throw Error('invalid-graphics-selection');
  return 'root-update' + (resolution === '1280x720' ? '-720p' : '') + '.json';
}
function graphics(m, resolution) {
  feedName(resolution);
  if (
    m.url !==
    REPO +
      'download/' +
      m.release +
      '/' +
      APP +
      '_' +
      m.version +
      (resolution === '1280x720' ? '_720p' : '') +
      '_all.ipk'
  )
    throw Error('signed-graphics-mismatch');
  return m;
}
function validate(m) {
  if (!m || typeof m !== 'object') throw Error('invalid-manifest');
  version(m.version);
  var fields = [
    'schema',
    'edition',
    'application',
    'release',
    'version',
    'runtime',
    'updater',
    'profile',
    'url',
    'sha256',
    'size',
    'notes'
  ];
  if (
    Object.keys(m).some(function (k) {
      return fields.indexOf(k) < 0;
    }) ||
    m.schema !== 1 ||
    m.edition !== 'root' ||
    m.application !== APP ||
    m.runtime !== 1 ||
    m.updater !== 1 ||
    m.profile !== 1 ||
    typeof m.release !== 'string' ||
    !/^v\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(m.release) ||
    [
      REPO + 'download/' + m.release + '/' + APP + '_' + m.version + '_all.ipk',
      REPO +
        'download/' +
        m.release +
        '/' +
        APP +
        '_' +
        m.version +
        '_720p_all.ipk'
    ].indexOf(m.url) < 0 ||
    !/^([a-f0-9]{64})$/.test(m.sha256) ||
    !Number.isInteger(m.size) ||
    m.size < 1 ||
    m.size > MAX ||
    typeof m.notes !== 'string' ||
    m.notes.length > 4000
  )
    throw Error('incompatible-root-release');
  return m;
}
function verify(e, key) {
  if (
    !e ||
    typeof e.payload !== 'string' ||
    typeof e.signature !== 'string' ||
    e.payload.length > 32768 ||
    e.signature.length > 2048
  )
    throw Error('invalid-envelope');
  var bytes = Buffer.from(e.payload, 'base64'),
    sig = Buffer.from(e.signature, 'base64');
  if (
    bytes.toString('base64') !== e.payload ||
    sig.toString('base64') !== e.signature
  )
    throw Error('invalid-envelope');
  var verifier = crypto.createVerify('RSA-SHA256');
  verifier.update(bytes);
  verifier.end();
  if (!verifier.verify(key, sig)) throw Error('invalid-signature');
  return validate(JSON.parse(bytes.toString('utf8')));
}
function get(url, limit, redirects) {
  return new Promise(function (resolve, reject) {
    if (!allowed(url) || (redirects || 0) > 3)
      return reject(Error('url-rejected'));
    var done = false,
      total = 0,
      chunks = [],
      req,
      timer;
    function finish(error, value) {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (error) {
        if (req) req.destroy();
        reject(error);
      } else resolve(value);
    }
    var options = Object.assign(require('url').parse(url), {
      rejectUnauthorized: true,
      ca: fs.readFileSync(__dirname + '/ca-bundle.crt', 'utf8'),
      headers: {
        'User-Agent': 'CleanYourTV-Root-Updater',
        'Accept': 'application/octet-stream'
      }
    });
    req = https.get(options, function (res) {
      if ([301, 302, 303, 307, 308].indexOf(res.statusCode) >= 0) {
        res.resume();
        try {
          var next = new URL(res.headers.location, url).href;
          get(next, limit, (redirects || 0) + 1).then(function (b) {
            finish(null, b);
          }, finish);
        } catch (e) {
          finish(e);
        }
        return;
      }
      if (res.statusCode !== 200) {
        res.resume();
        finish(Error('download-http'));
        return;
      }
      res.on('data', function (b) {
        total += b.length;
        if (total > limit) {
          res.destroy();
          finish(Error('download-too-large'));
        } else chunks.push(b);
      });
      res.on('end', function () {
        finish(null, Buffer.concat(chunks));
      });
      res.on('error', finish);
      res.on('aborted', function () {
        finish(Error('download-interrupted'));
      });
    });
    timer = setTimeout(function () {
      finish(Error('download-timeout'));
    }, 60000);
    req.on('error', finish);
  });
}
module.exports = {
  feedName: feedName,
  graphics: graphics,
  verify: verify,
  validate: validate,
  compare: compare,
  allowed: allowed,
  get: get
};
if (require.main === module) {
  var input = '',
    method = process.argv[2];
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', function (s) {
    input += s;
    if (Buffer.byteLength(input) > 65536) process.exit(2);
  });
  process.stdin.on('end', async function () {
    try {
      var key = fs.readFileSync(__dirname + '/release-public.pem'),
        p = JSON.parse(input || '{}'),
        result;
      if (method === 'offer') {
        var raw = JSON.parse(
          (
            await get(REPO + 'latest/download/' + feedName(p.resolution), 65536)
          ).toString('utf8')
        );
        result = {
          candidate: Object.assign(
            {},
            graphics(verify(raw, key), p.resolution),
            { proof: { payload: raw.payload, signature: raw.signature } }
          )
        };
      } else if (method === 'verify') result = verify(p.proof, key);
      else if (method === 'package') {
        var m = verify(p.proof, key),
          bytes = await get(m.url, m.size);
        if (
          bytes.length !== m.size ||
          crypto.createHash('sha256').update(bytes).digest('hex') !== m.sha256
        )
          throw Error('package-hash-mismatch');
        process.stdout.write(bytes);
        return;
      } else throw Error('unknown-operation');
      process.stdout.write(JSON.stringify(result));
    } catch (e) {
      process.stderr.write(String(e.message) + '\n');
      process.exitCode = 1;
    }
  });
}
