/* Synthetic TV filesystem/process fixture; never touches a real runtime slot. */
'use strict';
var assert = require('assert'),
  fs = require('fs'),
  os = require('os'),
  path = require('path'),
  vm = require('vm'),
  crypto = require('crypto');
var runtimeSource = fs.readFileSync(
  process.env.CYTV_RUNTIME_SOURCE || path.join(__dirname, '../runtime.js'),
  'utf8'
);
var DRIVER_CODE = 'import support\nprint(support.VALUE)\n',
  SUPPORT_CODE = 'VALUE = "ORIGINAL_IMPORT"\n';
var PIN = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
function remove(folder) {
  if (!fs.existsSync(folder)) return;
  fs.readdirSync(folder).forEach(function (entry) {
    var full = path.join(folder, entry);
    if (fs.lstatSync(full).isDirectory()) remove(full);
    else fs.unlinkSync(full);
  });
  fs.rmdirSync(folder);
}
async function rejects(promise) {
  var failed = false;
  try {
    await promise;
  } catch (error) {
    failed = true;
  }
  assert(failed, 'expected rejection');
}
function digest(raw) {
  return crypto.createHash('sha256').update(raw).digest('hex');
}
function fixture(shared) {
  var base = fs.mkdtempSync(
      path.join(fs.realpathSync(os.tmpdir()), 'cytv-node-offline-')
    ),
    root = shared
      ? path.join(
          base,
          'media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/payload'
        )
      : path.join(base, 'payload'),
    runtimeBase = path.join(base, 'private'),
    execBase = path.join(base, 'exec');
  var parents = [],
    cursor = root;
  while (cursor !== base) {
    parents.unshift(cursor);
    cursor = path.dirname(cursor);
  }
  parents.forEach(function (folder) {
    fs.mkdirSync(folder);
    if (shared && folder.indexOf('/com.cleanyourtv.installer') < 0)
      fs.chmodSync(folder, 511);
  });
  var calls = [],
    system = false,
    space = true,
    platform = 'linux',
    arch = 'arm',
    machine = 'armv7l',
    badOwner = null;
  var files = {},
    runtimeFiles = {};
  var binding = {
    schema: 1,
    archive_sha256: PIN,
    files: { 'bin/python3.13': digest('candidate') }
  };
  runtimeFiles['bin/python3.13'] = {
    sha256: digest('candidate'),
    size: 9,
    mode: 493
  };
  var bindraw = JSON.stringify(binding);
  runtimeFiles['.cytv-runtime.json'] = {
    sha256: digest(bindraw),
    size: Buffer.byteLength(bindraw),
    mode: 420
  };
  function write(name, raw) {
    fs.writeFileSync(path.join(root, name), raw);
    files[name] = { sha256: digest(raw), size: Buffer.byteLength(raw) };
  }
  fs.mkdirSync(path.join(root, 'root-updater'));
  fs.mkdirSync(path.join(root, 'root'));
  fs.mkdirSync(path.join(root, 'supervisor'));
  fs.mkdirSync(path.join(root, 'baseline'));
  write('root-updater/install_driver.py', DRIVER_CODE);
  write('root-updater/support.py', SUPPORT_CODE);
  write('root-updater/root-updater.ipk', 'IPK');
  write('root/bundle.json', 'ROOT_DATA');
  write('supervisor/bundle.json', 'SUPERVISOR_DATA');
  write('baseline/baseline.json', 'BASELINE_DATA');
  write('runtime.tar.gz', 'verified normalized archive');
  write('runtime-binding.json', bindraw);
  write(
    'runtime-provenance.json',
    JSON.stringify({
      sha256: PIN,
      normalized_sha256: files['runtime.tar.gz'].sha256
    })
  );
  write(
    'runtime-bootstrap.json',
    JSON.stringify({
      shell: 'FIXED SHELL\n',
      smoke: 'SMOKE',
      inspect_probe: 'INSPECT',
      system_probe: 'SYSTEM',
      promote: 'PROMOTE'
    })
  );
  var manifest = {
    schema: 1,
    files: files,
    runtime: {
      archive_sha256: PIN,
      files: runtimeFiles,
      max_unpacked: 160 * 1024 * 1024,
      max_files: 12000,
      required_space: 320 * 1024 * 1024
    }
  };
  function save() {
    fs.writeFileSync(
      path.join(root, 'manifest.json'),
      JSON.stringify(manifest)
    );
  }
  save();
  var fakefs = Object.create(fs);
  fakefs.lstatSync = function (name) {
    var st =
      name === '/var' ||
      name === '/var/lib' ||
      name === '/bin' ||
      name === '/usr' ||
      name === '/usr/bin'
        ? fs.lstatSync(base)
        : name === '/bin/sh' || name === '/usr/bin/python3'
          ? fs.lstatSync(path.join(root, 'runtime.tar.gz'))
          : fs.lstatSync(name);
    st.uid = name === badOwner ? 1000 : 0;
    if (!String(name).startsWith(base)) st.mode &= ~18;
    return st;
  };
  fakefs.fstatSync = function (fd) {
    var st = fs.fstatSync(fd);
    st.uid = 0;
    return st;
  };
  fakefs.realpathSync = function (name) {
    return name === '/bin/sh' || name === '/usr/bin/python3'
      ? name
      : fs.realpathSync(name);
  };
  var elf = Buffer.alloc(40);
  elf.write('7f454c46', 0, 'hex');
  elf[4] = 1;
  elf[5] = 1;
  elf.writeUInt16LE(40, 18);
  elf[39] = 5;
  fakefs.openSync = function (name, flags) {
    return name === '/bin/sh' ? 999 : fs.openSync.apply(fs, arguments);
  };
  fakefs.readSync = function (fd, buffer) {
    if (fd === 999) {
      elf.copy(buffer);
      return 40;
    }
    return fs.readSync.apply(fs, arguments);
  };
  fakefs.closeSync = function (fd) {
    if (fd !== 999) fs.closeSync(fd);
  };
  function exec(executable, args, options, callback) {
    calls.push({ executable: executable, args: args });
    if (executable === '/usr/bin/python3')
      return callback(
        system ? null : new Error('missing'),
        system
          ? args.indexOf('SMOKE') >= 0
            ? 'CYTV_RUNTIME_SMOKE'
            : 'CYTV_SYSTEM_PYTHON'
          : ''
      );
    if (executable === '/bin/sh') {
      var script = args[1];
      if (script.indexOf('uname -m') >= 0) {
        var kernels = script.match(/case \"\$\(uname -m\)\" in ([a-z0-9|]+)\)/);
        var accepted = kernels && kernels[1].split('|').indexOf(machine) >= 0;
        return callback(
          accepted ? null : new Error('unsupported machine'),
          accepted ? 'CYTV_MACHINE_READY' : ''
        );
      }
      if (script.indexOf('df -Pk') >= 0)
        return callback(
          space ? null : new Error('space'),
          space ? 'CYTV_SPACE_READY' : ''
        );
      if (script.indexOf('mktemp -d') >= 0) {
        var stage = path.join(runtimeBase, '.stage-123456789abc');
        fs.mkdirSync(stage);
        return callback(null, stage);
      }
      if (script.indexOf('tar -xzf') >= 0) {
        assert(
          script.indexOf(path.join(root, 'runtime.tar.gz')) < 0,
          'runtime extraction consumes a private authenticated archive'
        );
        var tree = path.join(runtimeBase, '.stage-123456789abc/tree');
        fs.mkdirSync(tree);
        fs.mkdirSync(path.join(tree, 'bin'));
        fs.writeFileSync(path.join(tree, 'bin/python3.13'), 'candidate');
        fs.chmodSync(path.join(tree, 'bin/python3.13'), 493);
        fs.writeFileSync(path.join(tree, '.cytv-runtime.json'), bindraw);
        return callback(null, '');
      }
      if (script.indexOf('rm -rf') >= 0) {
        var stage2 = path.join(runtimeBase, '.stage-123456789abc');
        if (fs.existsSync(stage2)) remove(stage2);
        return callback(null, '');
      }
    }
    if (args.indexOf('PROMOTE') >= 0) {
      fs.renameSync(args[args.length - 2], args[args.length - 1]);
      return callback(null, 'CYTV_RUNTIME_PROMOTED');
    }
    if (args.indexOf('SMOKE') >= 0) return callback(null, 'CYTV_RUNTIME_SMOKE');
    if (args.indexOf('INSPECT') >= 0)
      return callback(null, 'CYTV_SYSTEM_PYTHON');
    callback(new Error('Unexpected operation'));
  }
  var sandbox = {
    require: function (name) {
      if (name === 'fs') return fakefs;
      if (name === 'child_process') return { execFile: exec };
      return require(name);
    },
    process: {
      geteuid: function () {
        return 0;
      },
      platform: platform,
      arch: arch
    },
    Promise: Promise,
    Buffer: Buffer,
    module: { exports: {} }
  };
  var originalPin = digest(fs.readFileSync(path.join(root, 'manifest.json')));
  vm.runInNewContext(
    runtimeSource
      .replace(/'\/media([^']*)'/g, function (all, suffix) {
        return JSON.stringify(base + '/media' + suffix);
      })
      .replace("'/var/lib/clean-your-tv-python'", JSON.stringify(runtimeBase))
      .replace("'/var/lib/clean-your-tv-installer'", JSON.stringify(execBase)),
    sandbox
  );
  return {
    root: root,
    manifest: manifest,
    save: save,
    calls: calls,
    api: {
      inspect: function (root, recovery) {
        return sandbox.module.exports.inspect(root, recovery, originalPin);
      },
      prepare: function (root) {
        return sandbox.module.exports.prepare(root, originalPin);
      },
      stage: sandbox.module.exports.stage
    },
    base: base,
    runtimeBase: runtimeBase,
    execBase: execBase,
    setMachine: function (value) {
      machine = value;
    },
    setSystem: function (value) {
      system = value !== false;
    },
    setSpace: function () {
      space = false;
    },
    setArch: function () {
      sandbox.process.arch = 'x64';
    },
    badOwner: function (name) {
      badOwner = name;
    },
    clean: function () {
      remove(base);
    }
  };
}
async function rejection(change) {
  var f = fixture();
  try {
    change(f);
    await rejects(f.api.prepare(f.root));
    assert.strictEqual(
      f.calls.filter(function (c) {
        return c.args.join(' ').indexOf('mktemp -d') >= 0;
      }).length,
      0
    );
    assert(
      f.calls.every(function (c) {
        return (
          c.executable === '/usr/bin/python3' || c.executable === '/bin/sh'
        );
      }),
      'preflight failure must not execute a candidate'
    );
  } finally {
    f.clean();
  }
}
(async function () {
  for (var mutate of [
    function (f) {
      fs.unlinkSync(path.join(f.root, 'runtime.tar.gz'));
    },
    function (f) {
      fs.writeFileSync(path.join(f.root, 'extra'), 'x');
    },
    function (f) {
      fs.appendFileSync(path.join(f.root, 'runtime.tar.gz'), 'x');
    },
    function (f) {
      fs.writeFileSync(path.join(f.root, 'runtime.tar.gz'), 'x'.repeat(27));
    },
    function (f) {
      fs.unlinkSync(path.join(f.root, 'runtime.tar.gz'));
      fs.symlinkSync(
        'runtime-binding.json',
        path.join(f.root, 'runtime.tar.gz')
      );
    },
    function (f) {
      f.manifest.files['../escape'] = { sha256: '0'.repeat(64), size: 1 };
      f.save();
    },
    function (f) {
      f.manifest.runtime.archive_sha256 = '0'.repeat(64);
      f.save();
    },
    function (f) {
      fs.linkSync(
        path.join(f.root, 'runtime.tar.gz'),
        path.join(f.base, 'linked')
      );
    },
    function (f) {
      fs.chmodSync(path.join(f.root, 'root-updater'), 511);
    },
    function (f) {
      f.setArch();
    },
    function (f) {
      f.setSpace();
    },
    function (f) {
      f.badOwner(path.join(f.root, 'runtime.tar.gz'));
    }
  ])
    await rejection(mutate);
  await rejection(function (f) {
    f.setMachine('armv6l');
  });
  await rejection(function (f) {
    f.setSystem();
    f.setArch();
  });
  await rejection(function (f) {
    f.setSystem();
    f.setMachine('armv6l');
  });
  for (var machine of ['armv7l', 'armv8l', 'aarch64']) {
    var supported = fixture();
    try {
      supported.setMachine(machine);
      assert.strictEqual(
        (await supported.api.inspect(supported.root)).privateRuntimeRequired,
        true
      );
      assert(!fs.existsSync(supported.runtimeBase));
    } finally {
      supported.clean();
    }
  }
  var native64 = fixture();
  try {
    native64.setMachine('aarch64');
    native64.setSystem();
    assert.strictEqual(
      (await native64.api.inspect(native64.root)).python,
      '/usr/bin/python3'
    );
    assert(!fs.existsSync(native64.runtimeBase));
  } finally {
    native64.clean();
  }
  var cold = fixture(true);
  try {
    cold.setSystem();
    function writable(folder) {
      fs.chmodSync(folder, 511);
      fs.readdirSync(folder).forEach(function (entry) {
        var full = path.join(folder, entry);
        if (fs.statSync(full).isDirectory()) writable(full);
        else fs.chmodSync(full, 511);
      });
    }
    writable(path.dirname(cold.root));
    var data = await cold.api.inspect(cold.root);
    var privateCopy = await cold.api.stage(data, true);
    assert.equal(fs.statSync(privateCopy.driver).mode & 511, 384);
    assert.equal(fs.readFileSync(privateCopy.driver, 'utf8'), DRIVER_CODE);
    await privateCopy.cleanup();
    cold.setSystem(false);
    assert.equal(
      await cold.api.prepare(cold.root),
      path.join(cold.runtimeBase, PIN, 'bin/python3.13')
    );
    fs.writeFileSync(
      path.join(cold.root, 'root-updater/install_driver.py'),
      'X'.repeat(DRIVER_CODE.length)
    );
    await rejects(cold.api.inspect(cold.root));
  } finally {
    cold.clean();
  }
  var shared = fixture(true);
  try {
    shared.setSystem();
    assert.equal(
      (await shared.api.inspect(shared.root)).python,
      '/usr/bin/python3'
    );
    fs.chmodSync(path.dirname(shared.root), 511);
    assert.equal(
      (await shared.api.inspect(shared.root)).python,
      '/usr/bin/python3'
    );
  } finally {
    shared.clean();
  }
  for (var boundary of [
    'media',
    'media/developer',
    'media/developer/apps',
    'media/developer/apps/usr',
    'media/developer/apps/usr/palm',
    'media/developer/apps/usr/palm/applications',
    'media/developer/apps/usr/palm/applications/com.cleanyourtv.installer'
  ]) {
    var foreign = fixture(true);
    try {
      foreign.badOwner(path.join(foreign.base, boundary));
      await rejects(foreign.api.inspect(foreign.root));
    } finally {
      foreign.clean();
    }
  }
  for (var linkedBoundary of [
    'media',
    'media/developer',
    'media/developer/apps',
    'media/developer/apps/usr',
    'media/developer/apps/usr/palm',
    'media/developer/apps/usr/palm/applications',
    'media/developer/apps/usr/palm/applications/com.cleanyourtv.installer'
  ]) {
    var linked = fixture(true);
    try {
      var boundaryPath = path.join(linked.base, linkedBoundary);
      fs.renameSync(boundaryPath, boundaryPath + '-saved');
      fs.symlinkSync(path.basename(boundaryPath) + '-saved', boundaryPath);
      await rejects(linked.api.inspect(linked.root));
    } finally {
      linked.clean();
    }
  }
  var reanchored = fixture();
  try {
    reanchored.setSystem();
    reanchored.manifest.files['root-updater/install_driver.py'] = {
      sha256: digest('SUBSTITUTE_CODE'),
      size: 15
    };
    fs.writeFileSync(
      path.join(reanchored.root, 'root-updater/install_driver.py'),
      'SUBSTITUTE_CODE'
    );
    reanchored.save();
    await rejects(reanchored.api.inspect(reanchored.root));
  } finally {
    reanchored.clean();
  }
  var staged = fixture();
  try {
    staged.setSystem();
    var loaded = await staged.api.inspect(staged.root);
    var snapshot = await staged.api.stage(loaded, true);
    assert.equal(fs.readFileSync(snapshot.driver, 'utf8'), DRIVER_CODE);
    assert(!fs.existsSync(path.join(snapshot.root, 'runtime.tar.gz')));
    assert(
      fs.existsSync(path.join(snapshot.root, 'root-updater/root-updater.ipk'))
    );
    assert.equal(fs.statSync(snapshot.root).mode & 511, 448);
    fs.renameSync(staged.root, staged.root + '-deleted');
    assert.equal(fs.readFileSync(snapshot.driver, 'utf8'), DRIVER_CODE);
    assert.equal(
      require('child_process')
        .execFileSync('/usr/bin/python3', ['-E', '-s', '-B', snapshot.driver], {
          encoding: 'utf8'
        })
        .trim(),
      'ORIGINAL_IMPORT',
      'Python imports only the private original closure after source deletion'
    );
    await snapshot.cleanup();
    assert(!fs.existsSync(snapshot.root));
    fs.renameSync(staged.root + '-deleted', staged.root);
  } finally {
    staged.clean();
  }
  for (var sourceChange of ['file', 'manifest', 'leaf', 'parent']) {
    var changed = fixture(sourceChange === 'parent');
    try {
      changed.setSystem();
      var anchored = await changed.api.inspect(changed.root);
      if (sourceChange === 'parent') {
        var ancestor = path.dirname(path.dirname(changed.root));
        fs.renameSync(ancestor, ancestor + '-old');
        fs.mkdirSync(ancestor);
        fs.mkdirSync(path.dirname(changed.root));
        fs.mkdirSync(changed.root);
        fs.mkdirSync(path.join(changed.root, 'root-updater'));
      } else if (sourceChange === 'leaf') {
        var moved = changed.root + '-old';
        fs.renameSync(changed.root, moved);
        fs.mkdirSync(changed.root);
        fs.mkdirSync(path.join(changed.root, 'root-updater'));
      }
      fs.writeFileSync(
        path.join(changed.root, 'root-updater/install_driver.py'),
        'SUBSTITUTE_CODE'
      );
      if (sourceChange === 'manifest') {
        changed.manifest.files['root-updater/install_driver.py'] = {
          sha256: digest('SUBSTITUTE_CODE'),
          size: 15
        };
        changed.save();
      }
      await rejects(changed.api.stage(anchored, true));
      assert.equal(fs.readdirSync(changed.execBase).length, 0);
    } finally {
      changed.clean();
    }
  }
  var codeOnly = fixture();
  try {
    codeOnly.setSystem();
    var cs = await codeOnly.api.stage(
      await codeOnly.api.inspect(codeOnly.root, true),
      false
    );
    assert(!fs.existsSync(path.join(cs.root, 'root-updater/root-updater.ipk')));
    assert(fs.existsSync(path.join(cs.root, 'root-updater/support.py')));
    assert(!fs.existsSync(path.join(cs.root, 'root')));
    fs.writeFileSync(path.join(cs.root, 'unknown'), 'retain');
    await rejects(cs.cleanup());
    assert(
      fs.existsSync(cs.driver),
      'unknown drift preserves owned files until diagnosis'
    );
    fs.unlinkSync(path.join(cs.root, 'unknown'));
    await cs.cleanup();
  } finally {
    codeOnly.clean();
  }
  var unsafe = fixture();
  try {
    fs.chmodSync(unsafe.root, 511);
    await rejects(unsafe.api.inspect(unsafe.root));
  } finally {
    unsafe.clean();
  }
  var f = fixture();
  try {
    var state = await f.api.inspect(f.root);
    assert.strictEqual(state.privateRuntimeRequired, true);
    assert(!fs.existsSync(f.runtimeBase));
    assert(
      f.calls.every(function (c) {
        return (
          c.args.indexOf('SMOKE') < 0 &&
          c.args.join(' ').indexOf('mktemp -d') < 0
        );
      })
    );
    var selected = await f.api.prepare(f.root);
    assert.strictEqual(
      selected,
      path.join(f.runtimeBase, PIN, 'bin/python3.13')
    );
    assert(!fs.existsSync(path.join(f.runtimeBase, '.stage-123456789abc')));
    var count = f.calls.length;
    assert.strictEqual((await f.api.inspect(f.root)).python, selected);
    assert(
      f.calls.slice(count).every(function (c) {
        return c.args.indexOf('SMOKE') < 0;
      })
    );
  } finally {
    f.clean();
  }
  f = fixture();
  try {
    f.setSystem();
    assert.strictEqual(await f.api.prepare(f.root), '/usr/bin/python3');
    assert(!fs.existsSync(f.runtimeBase));
  } finally {
    f.clean();
  }
  f = fixture();
  try {
    f.setSystem();
    f.setArch();
    assert.strictEqual(
      (await f.api.inspect(f.root, true)).python,
      '/usr/bin/python3'
    );
    assert(!fs.existsSync(f.runtimeBase));
    assert(
      f.calls.every(function (c) {
        return c.executable === '/usr/bin/python3';
      })
    );
  } finally {
    f.clean();
  }
  console.log(
    'Offline runtime: corruption, ownership, ABI, space, read-only inspect, system skip, staging/promotion/readback passed'
  );
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
