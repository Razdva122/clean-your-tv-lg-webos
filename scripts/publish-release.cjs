#!/usr/bin/env node
'use strict';
// Normal publication delegates signing to the protected GitHub environment.
const fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path'),
  crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const policy = require('../root-edition/updater/fetch'),
  homePolicy = require('../updater-service/policy'),
  systemPolicy = require('../system-updater/policy');
// v1.5.4 is the immutable last published release before dual graphics packaging.
function verifyGraphicsInventory(build) {
  const required = systemPolicy.compare(build.tag.slice(1), '1.5.4') > 0;
  if (!required && !Object.prototype.hasOwnProperty.call(build, 'graphics'))
    return false;
  const expected = {
    '1920x1080': { launcher: 'launcher.ipk', root: 'root' },
    '1280x720': { launcher: 'launcher-720p.ipk', root: 'root-720p' }
  };
  if (!require('node:util').isDeepStrictEqual(build.graphics, expected))
    throw Error('release-graphics-inventory-required');
  if (!Object.prototype.hasOwnProperty.call(build, 'no_root_ota_720p'))
    throw Error('home-hd-lineage-required');
  return true;
}
function verifyHdHomeInventory(build, assets) {
  const present = assets.some((a) => a.name === 'update-720p.json'),
    prior = assets.some((a) => a.name === 'previous-update-720p.json'),
    record = build.no_root_ota_720p;
  if (present !== prior || present !== (record !== null))
    throw Error('home-hd-lineage-assets-mismatch');
  if (record === null) return false;
  if (
    !record ||
    record.version !== build.versions.home ||
    record.helper !== build.versions.helper ||
    !['sha256', 'previous_sha256', 'feed_sha256'].every((k) =>
      /^[a-f0-9]{64}$/.test(record[k] || '')
    ) ||
    homePolicy.compare(record.previous_version, record.version) >= 0
  )
    throw Error('home-hd-lineage-metadata-mismatch');
  return true;
}
function verifyRootRelease(
  feed,
  build,
  bytes,
  key = fs.readFileSync(
    path.join(__dirname, '../updater-service/release-public.pem')
  ),
  graphics = '1920x1080'
) {
  if (!build.versions || typeof build.versions.root !== 'string')
    throw Error('release-root-version-missing');
  const candidate = policy.verify(feed, key);
  if (
    path.basename(new URL(candidate.url).pathname) !==
    'com.cleanyourtv.root.preview_' +
      candidate.version +
      (graphics === '1280x720' ? '_720p' : '') +
      '_all.ipk'
  )
    throw Error('root-graphics-mismatch');
  if (candidate.version !== build.versions.root)
    throw Error(
      'stale-root-feed: signed ' +
        candidate.version +
        ', release ' +
        build.versions.root
    );
  if (
    bytes.length !== candidate.size ||
    crypto.createHash('sha256').update(bytes).digest('hex') !== candidate.sha256
  )
    throw Error('root-package-mismatch');
  return candidate;
}
function verifyHomeRelease(
  feed,
  build,
  bytes,
  key = fs.readFileSync(
    path.join(__dirname, '../updater-service/release-public.pem')
  ),
  graphics = '1920x1080'
) {
  if (
    !build.versions ||
    typeof build.versions.home !== 'string' ||
    typeof build.versions.helper !== 'string'
  )
    throw Error('release-home-version-missing');
  const candidate = homePolicy.verify(feed, key);
  if (
    path.basename(new URL(candidate.url).pathname) !==
    'com.gathin.tvhome_' +
      candidate.home +
      (graphics === '1280x720' ? '_720p' : '') +
      '_all.ipk'
  )
    throw Error('home-graphics-mismatch');
  if (candidate.home !== build.versions.home)
    throw Error(
      'stale-home-feed: signed ' +
        candidate.home +
        ', release ' +
        build.versions.home
    );
  if (candidate.helper !== build.versions.helper)
    throw Error('helper-feed-mismatch');
  if (
    crypto.createHash('sha256').update(bytes).digest('hex') !== candidate.sha256
  )
    throw Error('home-package-mismatch');
  const prior = homePolicy.verify(feed.previous, key);
  if (
    path.basename(new URL(prior.url).pathname) !==
    'com.gathin.tvhome_' +
      prior.home +
      (graphics === '1280x720' ? '_720p' : '') +
      '_all.ipk'
  )
    throw Error('home-graphics-mismatch');
  if (
    prior.helper !== candidate.helper ||
    homePolicy.compare(prior.home, candidate.home) >= 0
  )
    throw Error('incompatible-home-rollback');
  return candidate;
}
function verifySystemRelease(
  feed,
  build,
  assets,
  key = fs.readFileSync(
    path.join(__dirname, '../updater-service/release-public.pem')
  ),
  graphics = '1920x1080'
) {
  const manifest = systemPolicy.verify(feed, key);
  if (
    manifest.edition === 'root' &&
    systemPolicy.compare(manifest.release.slice(1), '1.4.1') >= 0 &&
    manifest.minimumSupervisorVersion !== '1.1.1'
  )
    throw Error('root-minimum-supervisor-required');
  if (manifest.release !== build.tag)
    throw Error('system-release-tag-mismatch');
  for (const item of manifest.components) {
    const version =
      build.versions[
        { 'root-infrastructure': 'root', 'root-updater': 'updater' }[
          item.name
        ] || item.name
      ];
    if (typeof version !== 'string' || item.version !== version)
      throw Error('system-release-version-mismatch');
    const filename = path.basename(new URL(item.url).pathname),
      raw = assets[filename];
    if (item.name === 'root' || item.name === 'home') {
      const suffix = graphics === '1280x720' ? '_720p_all.ipk' : '_all.ipk';
      if (
        !['1280x720', '1920x1080'].includes(graphics) ||
        filename !== item.application + '_' + item.version + suffix
      )
        throw Error('system-graphics-mismatch');
    }
    if (
      !raw ||
      raw.length !== item.size ||
      crypto.createHash('sha256').update(raw).digest('hex') !== item.sha256
    )
      throw Error('system-release-package-mismatch');
  }
  return manifest;
}
function verifyHomebrewApproval(build, committed) {
  if (!require('node:util').isDeepStrictEqual(build.homebrew, committed))
    throw Error('homebrew-source-approval-mismatch');
}
function verifyHomebrewSource(build, provider) {
  if (!/^[a-f0-9]{40}$/.test(build.source_commit || ''))
    throw Error('homebrew-source-commit-missing');
  const source = JSON.parse(
    provider([
      'api',
      'repos/Razdva122/clean-your-tv-lg-webos/contents/homebrew/release.json?ref=' +
        build.source_commit
    ])
  );
  verifyHomebrewApproval(
    build,
    JSON.parse(Buffer.from(source.content, 'base64').toString('utf8'))
  );
}
function verifyHomebrewRelease(folder, build) {
  const file = path.join(folder, 'homebrew-manifest.json');
  if (!build.homebrew) {
    if (fs.existsSync(file)) throw Error('unaccepted-homebrew-asset');
    return null;
  }
  const manifest = JSON.parse(fs.readFileSync(file));
  const match =
    /^https:\/\/github\.com\/Razdva122\/clean-your-tv-lg-webos\/releases\/download\/(v\d{1,4}\.\d{1,4}\.\d{1,4})\/(com\.cleanyourtv\.installer_\d+\.\d+\.\d+_all\.ipk)$/.exec(
      manifest.ipkUrl
    );
  if (!match) throw Error('invalid-homebrew-url');
  // Repository-owned verifier reads archive data only, including the embedded offline inventory.
  execFileSync(
    process.env.PYTHON || 'python3',
    [
      path.join(__dirname, 'homebrew-manifest.py'),
      '--ipk',
      path.join(folder, match[2]),
      '--verify',
      file,
      '--build',
      path.join(folder, 'BUILD-INFO.json'),
      '--sums',
      path.join(folder, 'SHA256SUMS')
    ],
    { stdio: 'pipe' }
  );
  return { tag: match[1], filename: match[2], sha256: manifest.ipkHash.sha256 };
}
function verifyHomebrewOrigin(installer, folder, download) {
  const origin = path.join(folder, 'homebrew-origin');
  fs.mkdirSync(origin, { recursive: true });
  download([
    'release',
    'download',
    installer.tag,
    '--pattern',
    installer.filename,
    '--dir',
    origin
  ]);
  if (
    crypto
      .createHash('sha256')
      .update(fs.readFileSync(path.join(origin, installer.filename)))
      .digest('hex') !== installer.sha256
  )
    throw Error('homebrew-origin-package-mismatch');
}
function main(args) {
  const [tag, option] = args;
  if (
    !/^v\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(tag || '') ||
    args.length > 2 ||
    (option && !['--check-only', '--publish-verified'].includes(option))
  )
    throw Error(
      'Usage: node scripts/publish-release.cjs vX.Y.Z [--check-only|--publish-verified]'
    );
  if (!option) {
    execFileSync(
      'gh',
      [
        'workflow',
        'run',
        'publish-release.yml',
        '--ref',
        'main',
        '-f',
        'tag=' + tag,
        '-f',
        'publish=true'
      ],
      { stdio: 'inherit' }
    );
    process.stdout.write(
      'Queued signing and checked publication of ' +
        tag +
        '. Follow the Sign and publish release workflow in GitHub Actions.\n'
    );
    return;
  }
  if (option === '--publish-verified' && process.env.GITHUB_ACTIONS !== 'true')
    throw Error('Publication requires the protected signing workflow');
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-release-'));
  const gh = (argv) =>
    execFileSync('gh', argv, {
      encoding: 'utf8',
      maxBuffer: 1024 * 1024,
      stdio: ['ignore', 'pipe', 'pipe']
    });
  try {
    gh([
      'release',
      'download',
      tag,
      '--pattern',
      'root-update.json',
      '--pattern',
      'BUILD-INFO.json',
      '--pattern',
      'SHA256SUMS',
      '--pattern',
      'update.json',
      '--pattern',
      'previous-update.json',
      '--pattern',
      'system-update-root.json',
      '--pattern',
      'system-update-no-root.json',
      '--dir',
      folder
    ]);
    const feed = JSON.parse(
      fs.readFileSync(path.join(folder, 'root-update.json'))
    );
    const build = JSON.parse(
      fs.readFileSync(path.join(folder, 'BUILD-INFO.json'))
    );
    if (build.tag !== tag) throw Error('release-tag-mismatch');
    const dualGraphics = verifyGraphicsInventory(build);
    const releaseAssets = JSON.parse(
      gh(['release', 'view', tag, '--json', 'assets'])
    ).assets;
    const homebrewAssets = releaseAssets.filter(
      (a) =>
        a.name === 'homebrew-manifest.json' ||
        a.name.startsWith('com.cleanyourtv.installer_')
    );
    if (!build.homebrew && homebrewAssets.length)
      throw Error('unaccepted-homebrew-asset');
    if (build.homebrew) {
      verifyHomebrewSource(build, gh);
      gh([
        'release',
        'download',
        tag,
        '--pattern',
        'homebrew-manifest.json',
        '--pattern',
        'com.cleanyourtv.installer_*.ipk',
        '--dir',
        folder
      ]);
      const installer = verifyHomebrewRelease(folder, build);
      if (
        homebrewAssets.length !== 2 ||
        !homebrewAssets.some((a) => a.name === installer.filename)
      )
        throw Error('unexpected-homebrew-assets');
      // Also verify the immutable URL retained by a carried manifest, not just the latest copy.
      verifyHomebrewOrigin(installer, folder, gh);
    }

    const candidate = policy.verify(
      feed,
      fs.readFileSync(
        path.join(__dirname, '../updater-service/release-public.pem')
      )
    );
    const filename = path.basename(new URL(candidate.url).pathname);
    gh([
      'release',
      'download',
      candidate.release,
      '--pattern',
      filename,
      '--dir',
      folder
    ]);
    verifyRootRelease(
      feed,
      build,
      fs.readFileSync(path.join(folder, filename))
    );
    const homeFeed = JSON.parse(
      fs.readFileSync(path.join(folder, 'update.json'))
    );
    const previous = JSON.parse(
      fs.readFileSync(path.join(folder, 'previous-update.json'))
    );
    const key = fs.readFileSync(
      path.join(__dirname, '../updater-service/release-public.pem')
    );
    const home = homePolicy.verify(homeFeed, key),
      prior = homePolicy.verify(homeFeed.previous, key);
    if (
      previous.payload !== homeFeed.previous.payload ||
      previous.signature !== homeFeed.previous.signature
    )
      throw Error('home-rollback-feed-mismatch');
    for (const item of [home, prior]) {
      const file = path.basename(new URL(item.url).pathname);
      gh([
        'release',
        'download',
        item.release,
        '--pattern',
        file,
        '--dir',
        folder
      ]);
      const raw = fs.readFileSync(path.join(folder, file));
      if (crypto.createHash('sha256').update(raw).digest('hex') !== item.sha256)
        throw Error('home-package-mismatch');
      if (item === home) verifyHomeRelease(homeFeed, build, raw, key);
    }
    const variants = dualGraphics
      ? ['root', 'no-root', 'root-720p', 'no-root-720p']
      : ['root', 'no-root'];
    if (dualGraphics) {
      const expected = {
        '1920x1080': { launcher: 'launcher.ipk', root: 'root' },
        '1280x720': { launcher: 'launcher-720p.ipk', root: 'root-720p' }
      };
      if (!require('node:util').isDeepStrictEqual(build.graphics, expected))
        throw Error('release-graphics-inventory-mismatch');
      gh([
        'release',
        'download',
        tag,
        '--pattern',
        'system-update-root-720p.json',
        '--pattern',
        'system-update-no-root-720p.json',
        '--pattern',
        'root-update-720p.json',
        '--dir',
        folder
      ]);
      const hdFeed = JSON.parse(
          fs.readFileSync(path.join(folder, 'root-update-720p.json'))
        ),
        hd = policy.verify(hdFeed, key),
        name = path.basename(new URL(hd.url).pathname);
      if (
        hd.release !== tag ||
        name !==
          'com.cleanyourtv.root.preview_' +
            build.versions.root +
            '_720p_all.ipk'
      )
        throw Error('root-graphics-mismatch');
      gh(['release', 'download', tag, '--pattern', name, '--dir', folder]);
      verifyRootRelease(
        hdFeed,
        build,
        fs.readFileSync(path.join(folder, name)),
        key,
        '1280x720'
      );
      const hdHomePresent = verifyHdHomeInventory(build, releaseAssets);
      if (hdHomePresent) {
        gh([
          'release',
          'download',
          tag,
          '--pattern',
          'update-720p.json',
          '--pattern',
          'previous-update-720p.json',
          '--dir',
          folder
        ]);
        const feed = JSON.parse(
            fs.readFileSync(path.join(folder, 'update-720p.json'))
          ),
          previous = JSON.parse(
            fs.readFileSync(path.join(folder, 'previous-update-720p.json'))
          );
        if (!require('node:util').isDeepStrictEqual(feed.previous, previous))
          throw Error('home-rollback-feed-mismatch');
        const candidate = homePolicy.verify(feed, key),
          prior = homePolicy.verify(previous, key),
          record = build.no_root_ota_720p;
        if (
          candidate.home !== record.version ||
          candidate.helper !== record.helper ||
          candidate.sha256 !== record.sha256 ||
          prior.home !== record.previous_version ||
          prior.sha256 !== record.previous_sha256 ||
          crypto
            .createHash('sha256')
            .update(fs.readFileSync(path.join(folder, 'update-720p.json')))
            .digest('hex') !== record.feed_sha256
        )
          throw Error('home-hd-lineage-proof-mismatch');
        for (const m of [candidate, prior]) {
          const name = path.basename(new URL(m.url).pathname);
          if (
            m.release !== tag ||
            name !== 'com.gathin.tvhome_' + m.home + '_720p_all.ipk'
          )
            throw Error('home-graphics-mismatch');
          gh(['release', 'download', tag, '--pattern', name, '--dir', folder]);
          const raw = fs.readFileSync(path.join(folder, name));
          if (
            crypto.createHash('sha256').update(raw).digest('hex') !== m.sha256
          )
            throw Error('home-package-mismatch');
          if (m === candidate)
            verifyHomeRelease(feed, build, raw, key, '1280x720');
        }
      }
    }
    for (const variant of variants) {
      const edition = variant.replace(/-720p$/, '');
      const envelope = JSON.parse(
        fs.readFileSync(path.join(folder, 'system-update-' + variant + '.json'))
      );
      const system = systemPolicy.verify(envelope, key),
        assets = {};
      if (system.edition !== edition) throw Error('system-edition-mismatch');
      for (const item of system.components) {
        const filename = path.basename(new URL(item.url).pathname);
        if (!fs.existsSync(path.join(folder, filename)))
          gh([
            'release',
            'download',
            tag,
            '--pattern',
            filename,
            '--dir',
            folder
          ]);
        assets[filename] = fs.readFileSync(path.join(folder, filename));
      }
      verifySystemRelease(
        envelope,
        build,
        assets,
        key,
        variant.endsWith('-720p') ? '1280x720' : '1920x1080'
      );
    }
    process.stdout.write(
      'Verified ' +
        tag +
        ': Root ' +
        candidate.version +
        ', Home ' +
        home.home +
        ', Helper ' +
        home.helper +
        ' and signed rollback ' +
        prior.home +
        ' match release metadata and packages.\n'
    );
    if (option !== '--check-only')
      process.stdout.write(
        gh(['release', 'edit', tag, '--draft=false', '--latest'])
      );
  } finally {
    fs.rmSync(folder, { recursive: true, force: true });
  }
}
module.exports = {
  verifyHdHomeInventory,
  verifyGraphicsInventory,
  verifyRootRelease,
  verifyHomeRelease,
  verifySystemRelease,
  verifyHomebrewRelease,
  verifyHomebrewOrigin,
  verifyHomebrewApproval,
  verifyHomebrewSource
};
if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(String(error.message) + '\n');
    process.exitCode = 1;
  }
}
