'use strict';
// Stable bootstrap v1 deliberately does not interpret the product protocol.
var crypto = require('crypto'),
  fs = require('fs'),
  transport = require('./policy');
var REPO = 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/';
var CATALOG =
  REPO +
  'latest/download/system-bootstrap-v' +
  transport.generation() +
  '.json';
var VARIANTS = ['no-root', 'no-root-720p', 'root', 'root-720p'];
function fields(value, names) {
  return (
    value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value).sort().join() === names.slice().sort().join()
  );
}
function version(value) {
  if (
    typeof value !== 'string' ||
    !/^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$/.test(
      value
    )
  )
    throw Error('invalid-engine-version');
}
function validate(catalog, schema = transport.generation()) {
  if (
    !fields(catalog, ['schema', 'engine', 'releases']) ||
    (schema !== 1 && schema !== 2) ||
    catalog.schema !== schema ||
    !fields(catalog.releases, VARIANTS)
  )
    throw Error('invalid-bootstrap-catalog');
  var e = catalog.engine;
  if (
    !fields(e, [
      'version',
      'bootstrap',
      'minimumPython',
      'minimumNode',
      'sha256',
      'size',
      'url'
    ]) ||
    e.bootstrap !== schema ||
    !Number.isInteger(e.minimumNode) ||
    e.minimumNode < 8 ||
    e.minimumNode > 100 ||
    !Number.isInteger(e.size) ||
    e.size < 1 ||
    e.size > 64 * 1024 * 1024 ||
    typeof e.sha256 !== 'string' ||
    !/^[a-f0-9]{64}$/.test(e.sha256)
  )
    throw Error('invalid-engine-descriptor');
  version(e.version);
  version(e.minimumPython);
  var release;
  VARIANTS.forEach(function (variant) {
    var m = catalog.releases[variant],
      edition = variant.replace(/-720p$/, '');
    if (
      !m ||
      m.edition !== edition ||
      typeof m.release !== 'string' ||
      m.release[0] !== 'v' ||
      typeof m.notes !== 'string' ||
      m.notes.length > 4000 ||
      !Array.isArray(m.components) ||
      !m.components.length ||
      m.components.length > 32
    )
      throw Error('invalid-engine-release');
    if (schema === 2) {
      transport.validate(m, schema);
      transport.graphics(
        m,
        variant.endsWith('-720p') ? '1280x720' : '1920x1080'
      );
    }
    version(m.release.slice(1));
    if (release && release !== m.release)
      throw Error('engine-release-conflict');
    release = m.release;
    var seen = {};
    m.components.forEach(function (c) {
      if (
        !c ||
        typeof c.name !== 'string' ||
        !/^[a-z][a-z0-9-]{0,63}$/.test(c.name) ||
        seen[c.name]
      )
        throw Error('invalid-engine-components');
      seen[c.name] = true;
      version(c.version);
    });
  });
  if (
    e.url !==
    REPO + 'download/' + release + '/system-engine_' + e.version + '.tar.gz'
  )
    throw Error('invalid-engine-url');
  return catalog;
}
function verify(envelope, key, schema = transport.generation()) {
  var raw = require('./bootstrap-trust').verify(envelope, key);
  return validate(JSON.parse(raw.toString('utf8')), schema);
}
module.exports = { validate: validate, verify: verify, catalogUrl: CATALOG };
if (require.main === module) {
  var input = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', function (chunk) {
    input += chunk;
    if (Buffer.byteLength(input) > 524288) process.exit(2);
  });
  process.stdin.on('end', async function () {
    try {
      var p = JSON.parse(input || '{}'),
        method = process.argv[2];
      var key = fs.readFileSync(__dirname + '/bootstrap-public.pem');
      if (method.indexOf('product-') === 0) {
        if (
          !fields(p.proof, ['bootstrap', 'variant']) ||
          VARIANTS.indexOf(p.proof.variant) < 0
        )
          throw Error('invalid-product-proof');
        var trusted = verify(p.proof.bootstrap, key),
          manifest = trusted.releases[p.proof.variant];
        transport.validate(manifest);
        if (method === 'product-verify')
          process.stdout.write(JSON.stringify(manifest));
        else if (method === 'product-offer')
          process.stdout.write(
            JSON.stringify({
              candidate: Object.assign({}, manifest, { proof: p.proof })
            })
          );
        else if (method === 'product-package') {
          var component = manifest.components.filter(function (item) {
            return item.name === p.name;
          })[0];
          if (!component) throw Error('unknown-component');
          var content = await transport.get(component.url, component.size);
          if (
            content.length !== component.size ||
            crypto.createHash('sha256').update(content).digest('hex') !==
              component.sha256
          )
            throw Error('product-hash-mismatch');
          process.stdout.write(content);
        } else throw Error('unknown-product-operation');
        return;
      }
      var proof =
        method === 'offer'
          ? JSON.parse((await transport.get(CATALOG, 524288)).toString('utf8'))
          : p.proof;
      var catalog = verify(proof, key);
      if (method === 'package') {
        var raw = await transport.get(catalog.engine.url, catalog.engine.size);
        if (
          raw.length !== catalog.engine.size ||
          crypto.createHash('sha256').update(raw).digest('hex') !==
            catalog.engine.sha256
        )
          throw Error('engine-package-hash-mismatch');
        process.stdout.write(raw);
      } else if (method === 'offer')
        process.stdout.write(
          JSON.stringify({ catalog: catalog, proof: proof })
        );
      else if (method === 'verify')
        process.stdout.write(JSON.stringify(catalog));
      else throw Error('unknown-engine-operation');
    } catch (error) {
      process.stdout.write(
        JSON.stringify({ error: error.updateError || 'verification-error' })
      );
      process.exitCode = 1;
    }
  });
}
