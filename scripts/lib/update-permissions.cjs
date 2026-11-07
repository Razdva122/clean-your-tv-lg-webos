'use strict';
const fs = require('fs'),
  path = require('path');
function plan(o) {
  if (!o || ['lab', 'production'].indexOf(o.variant) < 0)
    throw Error('explicit variant required');
  let p = require('../../updater-service/permissions')(
    o.root || '/var/luna-service2-dev'
  );
  if (o.variant === 'lab')
    p = JSON.parse(
      JSON.stringify(p)
        .replace(/com\.gathin\.tvhome/g, 'com.cleanyourtv.updatetest')
        .replace(/com\.cleanyourtv\.updater/g, 'com.cleanyourtv.updaterlab')
    );
  p.files.forEach((f) => {
    f.sha256 = require('crypto')
      .createHash('sha256')
      .update(f.content)
      .digest('hex');
  });
  return p;
}
function context(o, legacy, withoutRenewal) {
  const p = plan(o),
    prefix = o.prefix || '',
    root = o.root || '/var/luna-service2-dev';
  if (legacy) {
    for (const f of p.files) {
      f.content = f.content.replace(
        'com.cleanyourtv.updater' +
          (o.variant === 'lab' ? 'lab' : '') +
          '.service*',
        'com.cleanyourtv.updater' +
          (o.variant === 'lab' ? 'lab' : '') +
          '.service'
      );
      f.sha256 = require('crypto')
        .createHash('sha256')
        .update(f.content)
        .digest('hex');
    }
  }
  if (withoutRenewal) {
    for (const f of p.files) {
      if (
        f.path.includes('/api-permissions.d/') ||
        f.path.includes('/client-permissions.d/')
      ) {
        const value = JSON.parse(f.content);
        delete value[
          'com.cleanyourtv.updater' +
            (o.variant === 'lab' ? 'lab' : '') +
            '.renewalActivity'
        ];
        delete value[
          (o.variant === 'lab'
            ? 'com.cleanyourtv.updatetest'
            : 'com.gathin.tvhome') + '.renewal*'
        ];
        f.content = JSON.stringify(value, null, 2) + '\n';
        f.sha256 = require('crypto')
          .createHash('sha256')
          .update(f.content)
          .digest('hex');
      }
    }
  }
  const name =
    o.variant === 'lab'
      ? 'com.cleanyourtv.updaterlab'
      : 'com.cleanyourtv.updater';
  const receipt = prefix + root + '/' + name + '.permissions.receipt.json',
    lock = receipt + '.lock';
  function safe(file) {
    let dir = path.dirname(file);
    while (dir !== prefix && dir !== '/') {
      const s = fs.lstatSync(dir);
      if (!s.isDirectory() || s.isSymbolicLink()) throw Error('unsafe parent');
      dir = path.dirname(dir);
    }
  }
  function exists(file) {
    try {
      return fs.lstatSync(file);
    } catch (e) {
      if (e.code === 'ENOENT') return null;
      throw e;
    }
  }
  function exact(file, bytes) {
    const s = exists(file);
    if (!s) return false;
    if (
      !s.isFile() ||
      s.isSymbolicLink() ||
      fs.readFileSync(file, 'utf8') !== bytes
    )
      throw Error('managed file changed: ' + file);
    return true;
  }
  function write(file, bytes) {
    safe(file);
    const temp = file + '.cytv-stage';
    if (exists(temp)) throw Error('staged file collision');
    const fd = fs.openSync(temp, 'wx', 0o600);
    try {
      fs.writeFileSync(fd, bytes);
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    try {
      fs.linkSync(temp, file);
    } finally {
      fs.unlinkSync(temp);
    }
    const d = fs.openSync(path.dirname(file), 'r');
    try {
      fs.fsyncSync(d);
    } finally {
      fs.closeSync(d);
    }
  }
  return {
    p,
    prefix,
    receipt,
    lock,
    safe,
    exists,
    exact,
    write,
    bytes: JSON.stringify({ schema: 1, files: p.files }) + '\n'
  };
}
function run(o, remove) {
  let c = context(o);
  c.safe(c.receipt);
  fs.mkdirSync(c.lock, 0o700);
  try {
    let owned;
    try {
      owned = c.exact(c.receipt, c.bytes);
    } catch (e) {
      if (!remove) throw e;
      // Accept only the previous known generated plan, never arbitrary receipt paths.
      let previous;
      for (const variant of [
        [true, false],
        [false, true],
        [true, true]
      ]) {
        const candidate = context(o, ...variant);
        try {
          if (candidate.exact(candidate.receipt, candidate.bytes)) {
            previous = candidate;
            break;
          }
        } catch (ignore) {}
      }
      if (!previous) throw e;
      c = previous;
      owned = true;
    }
    if (!owned) {
      if (remove) return { status: 'not-installed' };
      for (const f of c.p.files)
        if (c.exists(c.prefix + f.path))
          throw Error('permission filename collision');
      c.write(c.receipt, c.bytes);
    }
    // Preflight all files before any removal; never erase someone else's changes.
    for (const f of c.p.files) {
      c.safe(c.prefix + f.path);
      c.exact(c.prefix + f.path, f.content);
    }
    if (remove) {
      for (const f of c.p.files.slice().reverse())
        if (c.exists(c.prefix + f.path)) fs.unlinkSync(c.prefix + f.path);
      o.refresh();
      fs.unlinkSync(c.receipt);
      return { status: 'removed' };
    }
    // Manifest is last, so a scanner cannot observe incomplete new permission files.
    for (const f of c.p.files)
      if (!c.exists(c.prefix + f.path)) c.write(c.prefix + f.path, f.content);
    o.refresh();
    return { status: 'installed', files: c.p.files.map((f) => f.path) };
  } finally {
    fs.rmdirSync(c.lock);
  }
}
module.exports = {
  plan,
  apply: (o) => run(o, false),
  remove: (o) => run(o, true)
};
