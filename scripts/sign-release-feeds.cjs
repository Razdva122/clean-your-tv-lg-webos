#!/usr/bin/env node
'use strict';
const fs = require('node:fs'),
  path = require('node:path'),
  crypto = require('node:crypto');
const rootPolicy = require('../root-edition/updater/fetch'),
  homePolicy = require('../updater-service/policy'),
  systemPolicy = require('../system-updater/policy');
function signBootstrap(
  catalog,
  releases,
  privateKey,
  publicKey,
  keyChain = [],
  generation = 1
) {
  if (!require('node:util').isDeepStrictEqual(catalog.releases, releases))
    throw Error('engine-product-manifests-mismatch');
  if (generation === 1 && Object.values(releases).some((m) => m.schema === 2))
    throw Error('generation-2-release-on-legacy-channel');
  const bytes = Buffer.from(JSON.stringify(catalog, null, 2) + '\n');
  const envelope = {
    payload: bytes.toString('base64'),
    signature: crypto.sign('RSA-SHA256', bytes, privateKey).toString('base64')
  };
  if (keyChain.length) envelope.keyChain = keyChain;
  require('../system-updater/engine-policy').verify(
    envelope,
    publicKey,
    generation
  );
  return envelope;
}
function signFeeds(
  manifests,
  privateKey,
  publicKey = fs.readFileSync(
    path.join(__dirname, '../updater-service/release-public.pem')
  ),
  bootstrap = {}
) {
  function sign(manifest, policy, generation = 1) {
    const bytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n');
    const envelope = {
      payload: bytes.toString('base64'),
      signature: crypto.sign('RSA-SHA256', bytes, privateKey).toString('base64')
    };
    policy.verify(envelope, publicKey, generation);
    return envelope;
  }
  if (manifests.productSchema === 2) {
    // A generation-B release must never publish a v1 engine catalog or
    // legacy Home-only offer; neither older client knows the new baseline.
    const allowed = ['bootstrap', 'graphics', 'productSchema', 'system'];
    if (Object.keys(manifests).some((key) => !allowed.includes(key)))
      throw Error('legacy-feeds-forbidden-for-generation-2');
    const catalog = signBootstrap(
      manifests.bootstrap,
      manifests.system,
      bootstrap.privateKey || privateKey,
      bootstrap.publicKey || publicKey,
      bootstrap.keyChain || [],
      2
    );
    const result = { 'system-bootstrap-v2.json': catalog };
    for (const [key, manifest] of Object.entries(manifests.system))
      result['system-update-v2-' + key + '.json'] = sign(
        manifest,
        systemPolicy,
        2
      );
    return result;
  }
  function graphicsSlot(manifest, hd, app, version) {
    if (
      !manifest ||
      manifest.url !==
        'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/' +
          manifest.release +
          '/' +
          app +
          '_' +
          version +
          (hd ? '_720p' : '') +
          '_all.ipk'
    )
      throw Error('legacy-graphics-mismatch');
  }
  for (const suffix of ['', '-720p']) {
    const root = manifests['root' + suffix],
      home = manifests['home' + suffix],
      prior = manifests['previous' + suffix];
    if (root)
      graphicsSlot(
        root,
        !!suffix,
        'com.cleanyourtv.root.preview',
        root.version
      );
    if (home) {
      graphicsSlot(home, !!suffix, 'com.gathin.tvhome', home.home);
      graphicsSlot(prior, !!suffix, 'com.gathin.tvhome', prior && prior.home);
    }
  }
  if (
    manifests.graphics &&
    (!manifests['root-720p'] ||
      !manifests.system ||
      Object.keys(manifests.system).sort().join() !==
        ['no-root', 'no-root-720p', 'root', 'root-720p'].join())
  )
    throw Error('graphics-release-set-required');
  const root = sign(manifests.root, rootPolicy),
    home = sign(manifests.home, homePolicy),
    previous = sign(manifests.previous, homePolicy);
  if (
    manifests.previous.helper !== manifests.home.helper ||
    homePolicy.compare(manifests.previous.home, manifests.home.home) >= 0
  )
    throw Error('incompatible-home-rollback');
  const result = {
    'root-update.json': root,
    'update.json': { ...home, previous },
    'previous-update.json': previous
  };
  if (manifests['root-720p'])
    result['root-update-720p.json'] = sign(manifests['root-720p'], rootPolicy);
  if (manifests['home-720p']) {
    const candidate = manifests['home-720p'],
      prior = manifests['previous-720p'];
    if (
      !prior ||
      prior.helper !== candidate.helper ||
      homePolicy.compare(prior.home, candidate.home) >= 0
    )
      throw Error('incompatible-home-rollback');
    const previous = sign(prior, homePolicy);
    result['update-720p.json'] = { ...sign(candidate, homePolicy), previous };
    result['previous-update-720p.json'] = previous;
  }
  if (manifests.system) {
    const keys = Object.keys(manifests.system),
      expected = keys.some((k) => k.endsWith('-720p'))
        ? ['root', 'no-root', 'root-720p', 'no-root-720p']
        : ['root', 'no-root'];
    if (keys.sort().join() !== expected.sort().join())
      throw Error('system-release-set-required');
    for (const key of keys) {
      const edition = key.replace(/-720p$/, '');
      if (
        !manifests.system[key] ||
        manifests.system[key].edition !== edition ||
        manifests.system[key].release !== manifests.root.release
      )
        throw Error('system-release-set-required');
      if (
        edition === 'root' &&
        manifests.system[key].minimumSupervisorVersion !==
          (manifests.system[key].supervisor === 2 ? '1.2.10' : '1.1.1')
      )
        throw Error('root-minimum-supervisor-required');
      const launcher = manifests.system[key].components.find(
        (c) => c.name === (edition === 'root' ? 'root' : 'home')
      );
      const suffix = key.endsWith('-720p') ? '_720p_all.ipk' : '_all.ipk';
      if (
        !launcher ||
        !launcher.url.endsWith(
          '/' + launcher.application + '_' + launcher.version + suffix
        )
      )
        throw Error('system-graphics-mismatch');
      result['system-update-' + key + '.json'] = sign(
        manifests.system[key],
        systemPolicy
      );
    }
  }
  if (manifests.bootstrap)
    result['system-bootstrap-v1.json'] = signBootstrap(
      manifests.bootstrap,
      manifests.system,
      bootstrap.privateKey || privateKey,
      bootstrap.publicKey || publicKey,
      bootstrap.keyChain || []
    );
  return result;
}
module.exports = { signFeeds, signBootstrap };
if (require.main === module) {
  try {
    const [input, output] = process.argv.slice(2);
    if (!input || !output || !process.env.UPDATE_SIGNING_PRIVATE_KEY)
      throw Error('Manifest paths and UPDATE_SIGNING_PRIVATE_KEY are required');
    const key = process.env.UPDATE_SIGNING_PRIVATE_KEY;
    delete process.env.UPDATE_SIGNING_PRIVATE_KEY;
    const manifests = JSON.parse(fs.readFileSync(input));
    const graphics = {
      '1920x1080': { launcher: 'launcher.ipk', root: 'root' },
      '1280x720': { launcher: 'launcher-720p.ipk', root: 'root-720p' }
    };
    if (!require('node:util').isDeepStrictEqual(manifests.graphics, graphics))
      throw Error('graphics-release-contract-required');
    const bootstrapKey = process.env.BOOTSTRAP_SIGNING_PRIVATE_KEY || key;
    delete process.env.BOOTSTRAP_SIGNING_PRIVATE_KEY;
    const keyChain = JSON.parse(
      process.env.BOOTSTRAP_SIGNING_KEY_CHAIN || '[]'
    );
    delete process.env.BOOTSTRAP_SIGNING_KEY_CHAIN;
    const feeds = signFeeds(manifests, key, undefined, {
      privateKey: bootstrapKey,
      keyChain,
      publicKey: fs.readFileSync(
        path.join(__dirname, '../system-updater/bootstrap-public.pem')
      )
    });
    fs.mkdirSync(output, { recursive: true });
    for (const [name, feed] of Object.entries(feeds))
      fs.writeFileSync(
        path.join(output, name),
        JSON.stringify(feed, null, 2) + '\n',
        { flag: 'wx' }
      );
    process.stdout.write(
      'Signed and verified Root, Home, rollback and system release feeds with the pinned release key.\n'
    );
  } catch (error) {
    process.stderr.write(error.message + '\n');
    process.exitCode = 1;
  }
}
