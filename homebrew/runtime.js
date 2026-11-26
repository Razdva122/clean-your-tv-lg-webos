/* Node 8 backend: fixed offline Python bootstrap; no browser command surface. */
'use strict';
var fs = require('fs'),
  path = require('path'),
  crypto = require('crypto'),
  cp = require('child_process');
var BASE = '/var/lib/clean-your-tv-python';
var PIN = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
var EXEC_BASE = '/var/lib/clean-your-tv-root-staging';
var SHARED = [
  '/media',
  '/media/developer',
  '/media/developer/apps',
  '/media/developer/apps/usr',
  '/media/developer/apps/usr/palm',
  '/media/developer/apps/usr/palm/applications'
];
var MAX = 160 * 1024 * 1024,
  COUNT = 12000;
function fail(message) {
  throw new Error(message);
}
function exists(name) {
  try {
    fs.lstatSync(name);
    return true;
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    return false;
  }
}
function safeName(name) {
  if (
    typeof name !== 'string' ||
    name.length > 512 ||
    !/^[A-Za-z0-9_+.,@=/-]+$/.test(name) ||
    name.split('/').some(function (p) {
      return !p || p === '.' || p === '..';
    })
  )
    fail('Unsafe payload path');
  return name;
}
function sdkData(name) {
  var app =
    '/media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller';
  return name === app || name.indexOf(app + '/') === 0;
}
function owned(name, directory, packageData) {
  var s = fs.lstatSync(name);
  if (
    s.uid !== 0 ||
    (s.mode & 18 &&
      !(
        packageData &&
        ((directory && SHARED.indexOf(name) >= 0) || sdkData(name))
      )) ||
    (sdkData(name) && s.mode & 3584) ||
    s.isSymbolicLink() ||
    (directory ? !s.isDirectory() : !s.isFile() || s.nlink !== 1)
  )
    fail('Unsafe root-owned path: ' + name);
  return s;
}
function ancestors(name, packageData) {
  name = path.resolve(name);
  while (true) {
    owned(name, true, packageData);
    var parent = path.dirname(name);
    if (parent === name) return;
    name = parent;
  }
}
function checkedBytes(name, limit, packageData, expected) {
  if (packageData && (!expected || !/^[0-9a-f]{64}$/.test(expected.sha256)))
    fail('Independent SDK DATA digest required');
  ancestors(path.dirname(name), packageData);
  var bindings = [],
    parent = path.dirname(name);
  while (true) {
    var item = owned(parent, true, packageData);
    bindings.push([parent, item.dev, item.ino]);
    if (parent === path.dirname(parent)) break;
    parent = path.dirname(parent);
  }
  var fd = fs.openSync(
    name,
    fs.constants.O_RDONLY |
      (fs.constants.O_NOFOLLOW || 0) |
      (fs.constants.O_NONBLOCK || 0)
  );
  try {
    var before = fs.fstatSync(fd);
    if (
      !before.isFile() ||
      before.uid !== 0 ||
      (before.mode & 18 && !(packageData && sdkData(name))) ||
      before.mode & 3584 ||
      before.nlink !== 1 ||
      before.size > limit
    )
      fail('Unsafe payload file');
    var raw = Buffer.alloc(before.size + 1),
      count = 0,
      n;
    while ((n = fs.readSync(fd, raw, count, raw.length - count, null)) > 0) {
      count += n;
      if (count > before.size) fail('Payload grew');
    }
    var after = fs.fstatSync(fd),
      now = owned(name, false, packageData);
    function same(a, b) {
      return (
        a.dev === b.dev &&
        a.ino === b.ino &&
        a.size === b.size &&
        a.mtime.getTime() === b.mtime.getTime() &&
        a.ctime.getTime() === b.ctime.getTime()
      );
    }
    if (count !== before.size || !same(before, after) || !same(before, now))
      fail('Payload file binding changed');
    bindings.forEach(function (b) {
      var st = owned(b[0], true, packageData);
      if (st.dev !== b[1] || st.ino !== b[2]) fail('Payload ancestor changed');
    });
    raw = raw.slice(0, count);
    if (
      packageData &&
      (crypto.createHash('sha256').update(raw).digest('hex') !==
        expected.sha256 ||
        (expected.size !== undefined && raw.length !== expected.size))
    )
      fail('SDK DATA digest mismatch');
    return raw;
  } finally {
    fs.closeSync(fd);
  }
}
function json(name, expected) {
  var raw = checkedBytes(name, 4 * 1024 * 1024, true, expected);
  if (
    expected &&
    (raw.length !== expected.size ||
      crypto.createHash('sha256').update(raw).digest('hex') !== expected.sha256)
  )
    fail('Payload metadata changed');
  return JSON.parse(raw.toString('utf8'));
}
function hash(name, expected, destination, packageData) {
  return new Promise(function (resolve, reject) {
    if (!expected || !/^[0-9a-f]{64}$/.test(expected.sha256))
      return reject(new Error('Independent DATA digest required'));
    var bindings = [],
      parent = path.dirname(name);
    try {
      while (true) {
        var item = owned(parent, true, packageData);
        bindings.push([parent, item.dev, item.ino]);
        if (parent === path.dirname(parent)) break;
        parent = path.dirname(parent);
      }
    } catch (e) {
      return reject(e);
    }
    var flags =
      fs.constants.O_RDONLY |
      (fs.constants.O_NOFOLLOW || 0) |
      (fs.constants.O_NONBLOCK || 0);
    fs.open(name, flags, function (error, fd) {
      if (error) return reject(error);
      var before;
      try {
        before = fs.fstatSync(fd);
        if (
          !before.isFile() ||
          before.nlink !== 1 ||
          before.uid !== 0 ||
          (before.mode & 18 && !(packageData && sdkData(name))) ||
          before.mode & 3584 ||
          before.size !== expected.size
        )
          fail('Payload size or ownership mismatch');
      } catch (e) {
        fs.closeSync(fd);
        return reject(e);
      }
      var output;
      try {
        if (destination)
          output = fs.openSync(
            destination,
            fs.constants.O_WRONLY |
              fs.constants.O_CREAT |
              fs.constants.O_EXCL |
              (fs.constants.O_NOFOLLOW || 0),
            384
          );
      } catch (e) {
        fs.closeSync(fd);
        return reject(e);
      }
      function closeOutput() {
        if (output !== undefined) {
          fs.fsyncSync(output);
          fs.closeSync(output);
          output = undefined;
        }
      }
      var h = crypto.createHash('sha256'),
        bytes = 0;
      var stream = fs.createReadStream(name, { fd: fd, autoClose: false });
      stream.on('data', function (chunk) {
        try {
          bytes += chunk.length;
          if (bytes > expected.size) fail('Payload grew during verification');
          h.update(chunk);
          if (output !== undefined) {
            var offset = 0;
            while (offset < chunk.length)
              offset += fs.writeSync(
                output,
                chunk,
                offset,
                chunk.length - offset
              );
          }
        } catch (e) {
          stream.destroy(e);
        }
      });
      stream.on('error', function (e) {
        closeOutput();
        fs.closeSync(fd);
        reject(e);
      });
      stream.on('end', function () {
        try {
          closeOutput();
          var after = owned(name, false, packageData),
            finalFd = fs.fstatSync(fd);
          if (
            before.ino !== finalFd.ino ||
            before.dev !== finalFd.dev ||
            before.size !== finalFd.size ||
            before.ctime.getTime() !== finalFd.ctime.getTime()
          )
            fail('Payload fd changed');
          bindings.forEach(function (b) {
            var st = owned(b[0], true, packageData);
            if (st.dev !== b[1] || st.ino !== b[2])
              fail('Payload ancestor changed');
          });
          if (
            bytes !== expected.size ||
            h.digest('hex') !== expected.sha256 ||
            before.ino !== after.ino ||
            before.dev !== after.dev ||
            before.mtime.getTime() !== after.mtime.getTime() ||
            before.ctime.getTime() !== after.ctime.getTime()
          )
            fail('Payload hash or binding mismatch');
          fs.closeSync(fd);
          resolve();
        } catch (e) {
          fs.closeSync(fd);
          reject(e);
        }
      });
    });
  });
}
function walk(root, expected, packageData) {
  ancestors(root, packageData);
  var seen = {},
    dirs = {},
    total = 0,
    names = Object.keys(expected);
  names.forEach(function (name) {
    safeName(name);
    var r = expected[name];
    if (
      !r ||
      !Number.isSafeInteger(r.size) ||
      r.size < 0 ||
      !/^[0-9a-f]{64}$/.test(r.sha256)
    )
      fail('Invalid file record');
    var parent = path.posix.dirname(name);
    while (parent !== '.') {
      dirs[parent] = true;
      parent = path.posix.dirname(parent);
    }
  });
  function visit(folder, prefix) {
    fs.readdirSync(folder)
      .sort()
      .forEach(function (entry) {
        var name = prefix + entry,
          full = path.join(folder, entry);
        safeName(name);
        var s = fs.lstatSync(full);
        if (s.isDirectory()) {
          if (!dirs[name]) fail('Unexpected payload directory');
          owned(full, true, packageData);
          visit(full, name + '/');
        } else {
          owned(full, false, packageData);
          if (!Object.prototype.hasOwnProperty.call(expected, name))
            fail('Unexpected payload file');
          seen[name] = true;
          total += s.size;
        }
      });
  }
  visit(root, '');
  if (Object.keys(seen).length !== names.length) fail('Missing payload file');
  // Sequential streaming keeps memory and descriptor usage bounded on the TV.
  return names
    .reduce(function (promise, name) {
      return promise.then(function () {
        return hash(
          path.join(root, name),
          expected[name],
          undefined,
          packageData
        );
      });
    }, Promise.resolve())
    .then(function () {
      return total;
    });
}
function run(executable, args, marker) {
  return new Promise(function (resolve, reject) {
    cp.execFile(
      executable,
      args,
      {
        timeout: 90000,
        maxBuffer: 65536,
        env: { PATH: '/usr/sbin:/usr/bin:/sbin:/bin', LC_ALL: 'C' }
      },
      function (error, stdout) {
        if (error || (marker && stdout.trim() !== marker))
          return reject(new Error('Verified runtime operation failed'));
        resolve(stdout.trim());
      }
    );
  });
}
function quote(value) {
  return "'" + value.replace(/'/g, "'\\''") + "'";
}
function shell(bootstrap, script) {
  return run('/bin/sh', ['-c', bootstrap.shell + script]);
}
function abi(bootstrap) {
  if (process.platform !== 'linux' || process.arch !== 'arm')
    fail('Private Python requires ARMv7 little-endian soft-float EABI5 Linux');
  // /bin/sh can be the distribution's expected symlink; validate its real target.
  var executable = fs.realpathSync('/bin/sh');
  ancestors(path.dirname(executable));
  owned(executable, false);
  var fd = fs.openSync(executable, 'r'),
    header = Buffer.alloc(40);
  try {
    if (fs.readSync(fd, header, 0, 40, 0) !== 40) fail('Unknown Linux ABI');
  } finally {
    fs.closeSync(fd);
  }
  if (
    header.toString('hex', 0, 4) !== '7f454c46' ||
    header[4] !== 1 ||
    header[5] !== 1 ||
    header.readUInt16LE(18) !== 40 ||
    header[37] & 4 ||
    header[39] !== 5
  )
    fail('Unsupported ARM ABI; private Python was not installed');
  return shell(
    bootstrap,
    'case "$(uname -m)" in armv7l|armv8l|aarch64) ;; *) exit 1;; esac\nprintf CYTV_MACHINE_READY\n'
  ).then(
    function (result) {
      if (result !== 'CYTV_MACHINE_READY')
        fail(
          'Unsupported ARM machine; private Python requires ARMv7 or ARMv8 little-endian Linux'
        );
    },
    function () {
      fail(
        'Private Python requires ARMv7 or ARMv8 little-endian Linux and verified system tools'
      );
    }
  );
}
function verifiedPayload(root, pin) {
  root = path.resolve(root);
  ancestors(root, true);
  var raw = checkedBytes(
    path.join(root, 'manifest.json'),
    4 * 1024 * 1024,
    true,
    { sha256: pin }
  );
  if (
    !/^[0-9a-f]{64}$/.test(pin || '') ||
    crypto.createHash('sha256').update(raw).digest('hex') !== pin
  )
    fail('Payload manifest identity changed');
  var manifest = JSON.parse(raw.toString('utf8'));
  if (
    manifest.schema !== 1 ||
    !manifest.runtime ||
    manifest.runtime.archive_sha256 !== PIN ||
    manifest.runtime.max_unpacked !== MAX ||
    manifest.runtime.max_files !== COUNT ||
    !Number.isSafeInteger(manifest.runtime.required_space) ||
    manifest.runtime.required_space < 320 * 1024 * 1024
  )
    fail('Invalid runtime binding');
  var expected = manifest.files;
  if (
    !expected ||
    Object.keys(expected).length > COUNT * 3 ||
    expected['manifest.json']
  )
    fail('Invalid payload inventory');
  // The built bootstrap pins these original bytes, including every later copied file.
  expected['manifest.json'] = { size: raw.length, sha256: pin };
  return walk(root, expected, true).then(function () {
    var binding = json(
        path.join(root, 'runtime-binding.json'),
        expected['runtime-binding.json']
      ),
      provenance = json(
        path.join(root, 'runtime-provenance.json'),
        expected['runtime-provenance.json']
      );
    var files = manifest.runtime.files;
    if (
      !files ||
      Object.keys(files).length > COUNT ||
      binding.schema !== 1 ||
      binding.archive_sha256 !== PIN ||
      provenance.sha256 !== PIN ||
      provenance.normalized_sha256 !== expected['runtime.tar.gz'].sha256
    )
      fail('Runtime provenance mismatch');
    var total = 0;
    Object.keys(files).forEach(function (name) {
      safeName(name);
      var record = files[name];
      if (
        !record ||
        !Number.isSafeInteger(record.size) ||
        record.size < 0 ||
        !/^[0-9a-f]{64}$/.test(record.sha256) ||
        (record.mode !== 420 && record.mode !== 493)
      )
        fail('Invalid runtime file metadata');
      total += record.size;
      if (
        name !== '.cytv-runtime.json' &&
        binding.files[name] !== files[name].sha256
      )
        fail('Runtime inventory binding mismatch');
    });
    if (
      !files['.cytv-runtime.json'] ||
      files['.cytv-runtime.json'].sha256 !==
        expected['runtime-binding.json'].sha256 ||
      files['.cytv-runtime.json'].size !==
        expected['runtime-binding.json'].size ||
      Object.keys(files).length !== Object.keys(binding.files).length + 1 ||
      total > MAX ||
      !files['bin/python3.13'] ||
      !(files['bin/python3.13'].mode & 73)
    )
      fail('Invalid runtime inventory');
    var bootstrap = json(
      path.join(root, 'runtime-bootstrap.json'),
      expected['runtime-bootstrap.json']
    );
    ['shell', 'smoke', 'inspect_probe', 'system_probe', 'promote'].forEach(
      function (key) {
        if (typeof bootstrap[key] !== 'string' || !bootstrap[key])
          fail('Missing fixed runtime bootstrap');
      }
    );
    return { root: root, manifest: manifest, bootstrap: bootstrap };
  });
}
function inspectInternal(payloadRoot, recovery, pin, payloadVerified) {
  return Promise.resolve()
    .then(function () {
      if (!process.geteuid || process.geteuid() !== 0)
        fail('Root execution is required');
      return verifiedPayload(payloadRoot, pin);
    })
    .then(function (context) {
      if (payloadVerified) payloadVerified();
      return (
        recovery === true ? Promise.resolve() : abi(context.bootstrap)
      ).then(function () {
        var systemSafe = Promise.resolve().then(function () {
          var executable = fs.realpathSync('/usr/bin/python3');
          ancestors(path.dirname(executable));
          owned(executable, false);
          return run(
            '/usr/bin/python3',
            ['-I', '-B', '-c', context.bootstrap.inspect_probe],
            'CYTV_SYSTEM_PYTHON'
          );
        });
        return systemSafe.then(
          function () {
            return {
              python: '/usr/bin/python3',
              privateRuntimeRequired: false,
              context: context
            };
          },
          function () {
            return abi(context.bootstrap).then(function () {
              ancestors('/var/lib');
              var slot = BASE + '/' + PIN;
              if (fs.existsSync(BASE)) ancestors(BASE);
              if (
                fs.existsSync(slot) ||
                (function () {
                  try {
                    fs.lstatSync(slot);
                    return true;
                  } catch (e) {
                    if (e.code !== 'ENOENT') throw e;
                    return false;
                  }
                })()
              ) {
                return walk(slot, context.manifest.runtime.files)
                  .then(function () {
                    return run(
                      slot + '/bin/python3.13',
                      ['-I', '-B', '-c', context.bootstrap.inspect_probe],
                      'CYTV_SYSTEM_PYTHON'
                    );
                  })
                  .then(function () {
                    return {
                      python: slot + '/bin/python3.13',
                      privateRuntimeRequired: false,
                      context: context
                    };
                  });
              }
              return shell(
                context.bootstrap,
                'ancestors /var/lib\navailable=$(df -Pk /var/lib | awk \'END {print $4}\')\ncase "$available" in \'\'|*[!0-9]*) exit 1;; esac\n[ "$available" -ge ' +
                  Math.ceil(context.manifest.runtime.required_space / 1024) +
                  ' ] || exit 1\nprintf CYTV_SPACE_READY\n'
              ).then(
                function (result) {
                  if (result !== 'CYTV_SPACE_READY')
                    fail(
                      'Insufficient storage; private Python needs at least 320 MiB free'
                    );
                  return {
                    python: null,
                    privateRuntimeRequired: true,
                    requiredSpace: context.manifest.runtime.required_space,
                    context: context
                  };
                },
                function () {
                  fail(
                    'Private Python needs safe system tools and at least 320 MiB free in /var/lib'
                  );
                }
              );
            });
          }
        );
      });
    });
}
function removeStage(bootstrap, stage) {
  if (
    !stage ||
    !new RegExp('^' + BASE + '/\\.stage-[A-Za-z0-9]{6,32}$').test(stage)
  )
    return Promise.resolve();
  return shell(
    bootstrap,
    'ancestors ' + quote(stage) + '\nrm -rf ' + quote(stage) + '\n'
  ).catch(function () {
    /* Preserve untrusted drift for diagnosis. */
  });
}
function prepare(payloadRoot, pin) {
  var context, stage;
  return inspectInternal(payloadRoot, false, pin)
    .then(function (state) {
      if (state.python)
        return run(
          state.python,
          ['-I', '-B', '-c', state.context.bootstrap.smoke],
          'CYTV_RUNTIME_SMOKE'
        ).then(function () {
          return state.python;
        });
      context = state.context;
      // No product lease here: candidate Python takes the existing immutable-slot promotion lock.
      // The caller must acquire the shared product lease and re-inspect before product mutations.
      if (!fs.existsSync(BASE)) fs.mkdirSync(BASE, 493);
      ancestors(BASE);
      return shell(
        context.bootstrap,
        'ancestors ' +
          quote(BASE) +
          '\nstage=$(mktemp -d ' +
          quote(BASE + '/.stage-XXXXXXXXXXXX') +
          ')\nprintf "%s" "$stage"\n'
      )
        .then(function (created) {
          if (
            !new RegExp('^' + BASE + '/\\.stage-[A-Za-z0-9]{6,32}$').test(
              created
            )
          )
            fail('Unsafe runtime staging result');
          stage = created;
          return hash(
            path.join(context.root, 'runtime.tar.gz'),
            context.manifest.files['runtime.tar.gz'],
            stage + '/runtime.tar.gz',
            true
          );
        })
        .then(function () {
          return shell(
            context.bootstrap,
            'ancestors ' +
              quote(stage) +
              '\nmkdir -m 755 ' +
              quote(stage + '/tree') +
              '\ntar -xzf ' +
              quote(stage + '/runtime.tar.gz') +
              ' -C ' +
              quote(stage + '/tree') +
              '\n'
          );
        })
        .then(function () {
          return walk(stage + '/tree', context.manifest.runtime.files);
        })
        .then(function () {
          return run(
            stage + '/tree/bin/python3.13',
            ['-I', '-B', '-c', context.bootstrap.smoke],
            'CYTV_RUNTIME_SMOKE'
          );
        })
        .then(function () {
          return run(stage + '/tree/bin/python3.13', [
            '-I',
            '-B',
            '-c',
            context.bootstrap.promote,
            BASE,
            stage + '/tree',
            BASE + '/' + PIN
          ]);
        })
        .then(function (result) {
          if (
            result !== 'CYTV_RUNTIME_PROMOTED' &&
            result !== 'CYTV_RUNTIME_EXISTS'
          )
            fail('Runtime promotion failed');
          return walk(BASE + '/' + PIN, context.manifest.runtime.files);
        })
        .then(function () {
          return run(
            BASE + '/' + PIN + '/bin/python3.13',
            ['-I', '-B', '-c', context.bootstrap.smoke],
            'CYTV_RUNTIME_SMOKE'
          );
        })
        .then(function () {
          return BASE + '/' + PIN + '/bin/python3.13';
        });
    })
    .then(
      function (python) {
        return context
          ? removeStage(context.bootstrap, stage).then(function () {
              return python;
            })
          : python;
      },
      function (error) {
        return (
          context ? removeStage(context.bootstrap, stage) : Promise.resolve()
        ).then(function () {
          throw error;
        });
      }
    );
}
function inspect(payloadRoot, recovery, pin, payloadVerified) {
  return inspectInternal(payloadRoot, recovery, pin, payloadVerified).then(
    function (state) {
      var result = {
        python: state.python,
        privateRuntimeRequired: state.privateRuntimeRequired,
        requiredSpace: state.requiredSpace || 0
      };
      Object.defineProperty(result, 'context', { value: state.context });
      return result;
    }
  );
}
function executionBase() {
  ancestors('/var/lib');
  var createdBase;
  try {
    fs.mkdirSync(EXEC_BASE, 448);
    createdBase = owned(EXEC_BASE, true);
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
  }
  ancestors(EXEC_BASE);
  var base = owned(EXEC_BASE, true);
  if ((base.mode & 4095) !== 448 || base.dev !== owned('/var/lib', true).dev)
    fail('Unsafe execution staging directory');
  return createdBase;
}
function stage(state, full) {
  return Promise.resolve().then(function () {
    var context = state.context,
      expected = context.manifest.files;
    var createdBase = executionBase();
    var removing = full === 'removal';
    var root =
      EXEC_BASE +
      (removing ? '/cytv-product-' : '/cytv-homebrew-') +
      crypto.randomBytes(16).toString('hex');
    fs.mkdirSync(root, 448);
    var identityRoot = owned(root, true);
    var saved = [],
      directories = [root];
    function cleanup() {
      // Only exact invocation-owned private entries are removed; drift is retained.
      return Promise.resolve().then(function () {
        // The lock-held cleanup tail may retire the full removal snapshot.
        if (removing && !exists(root)) return;
        ancestors(root);
        var current = owned(root, true);
        if (
          current.dev !== identityRoot.dev ||
          current.ino !== identityRoot.ino
        )
          fail('Execution staging drift');
        // An interrupted tail can empty the root before releasing the receipt.
        if (removing && !fs.readdirSync(root).length && saved.length) {
          fs.rmdirSync(root);
          return;
        }
        saved.forEach(function (r) {
          var st = owned(r[0], false);
          if (st.dev !== r[1] || st.ino !== r[2])
            fail('Execution staging drift');
        });
        directories.forEach(function (folder) {
          owned(folder, true);
          fs.readdirSync(folder).forEach(function (entry) {
            var full = path.join(folder, entry);
            if (
              directories.indexOf(full) < 0 &&
              !saved.some(function (r) {
                return r[0] === full;
              })
            )
              fail('Unknown execution staging entry');
          });
        });
        saved
          .slice()
          .reverse()
          .forEach(function (r) {
            fs.unlinkSync(r[0]);
          });
        directories
          .slice()
          .reverse()
          .forEach(function (folder) {
            fs.rmdirSync(folder);
          });
        if (createdBase) {
          // The computer installer shares this directory. Never remove its
          // contents or a replacement directory, even when the name matches.
          try {
            var currentBase = owned(EXEC_BASE, true);
            if (
              currentBase.dev === createdBase.dev &&
              currentBase.ino === createdBase.ino
            )
              fs.rmdirSync(EXEC_BASE);
          } catch (error) {
            if (['ENOENT', 'ENOTEMPTY', 'EEXIST'].indexOf(error.code) < 0)
              throw error;
          }
        }
      });
    }
    function mkdir(folder) {
      if (directories.indexOf(folder) >= 0) return;
      mkdir(path.dirname(folder));
      fs.mkdirSync(folder, 448);
      directories.push(folder);
    }
    try {
      var names = Object.keys(expected).filter(function (name) {
          if (removing) return /^(root|root-updater)\//.test(name);
          if (full)
            return /^(root|root-updater|supervisor|baseline|edition)\//.test(
              name
            );
          return (
            (name.indexOf('root-updater/') === 0 && !/\.ipk$/.test(name)) ||
            name === 'edition/debloat.py' ||
            name === 'edition/cytv/__init__.py' ||
            name === 'edition/cytv/debloat_policy.py'
          );
        }),
        ordinaryBytes = 0;
      var version = (context.manifest.versions || {}).root;
      var rootIpk =
        typeof version === 'string' && /^\d+\.\d+\.\d+$/.test(version)
          ? 'root/com.cleanyourtv.root.preview_' + version + '_all.ipk'
          : null;
      var rootRecord = rootIpk && expected[rootIpk];
      var rollbackCopy = rootRecord && 'baseline/cache/' + rootRecord.sha256;
      if (!names.length || names.indexOf('root-updater/install_driver.py') < 0)
        fail('Missing execution closure');
      names.forEach(function (name) {
        safeName(name);
        var record = expected[name];
        // The package and its identical rollback copy may each contain Root media.
        var rootMedia =
          name === rootIpk ||
          (name === rollbackCopy &&
            record.sha256 === rootRecord.sha256 &&
            record.size === rootRecord.size);
        if (!rootMedia) ordinaryBytes += record.size;
        if (
          !Number.isSafeInteger(record.size) ||
          record.size < 0 ||
          record.size > (rootMedia ? 64 : 16) * 1024 * 1024 ||
          ordinaryBytes > 32 * 1024 * 1024
        )
          fail('Execution snapshot too large');
        var raw = checkedBytes(
          path.join(context.root, name),
          record.size,
          true,
          record
        );
        if (
          raw.length !== record.size ||
          crypto.createHash('sha256').update(raw).digest('hex') !==
            record.sha256
        )
          fail('Execution source changed');
        var destination = path.join(root, name);
        mkdir(path.dirname(destination));
        var fd = fs.openSync(
          destination,
          fs.constants.O_WRONLY |
            fs.constants.O_CREAT |
            fs.constants.O_EXCL |
            (fs.constants.O_NOFOLLOW || 0),
          384
        );
        try {
          var offset = 0;
          while (offset < raw.length)
            offset += fs.writeSync(fd, raw, offset, raw.length - offset);
          fs.fsyncSync(fd);
        } finally {
          fs.closeSync(fd);
        }
        var st = owned(destination, false);
        saved.push([destination, st.dev, st.ino]);
        var copied = checkedBytes(destination, record.size, false);
        if (
          copied.length !== record.size ||
          crypto.createHash('sha256').update(copied).digest('hex') !==
            record.sha256
        )
          fail('Execution copy changed');
      });
      return {
        root: root,
        driver: root + '/root-updater/install_driver.py',
        editionInspector: root + '/edition/edition.py',
        debloat: root + '/edition/debloat.py',
        cleanup: cleanup
      };
    } catch (error) {
      return cleanup()
        .catch(function () {})
        .then(function () {
          throw error;
        });
    }
  });
}
var PRODUCT = '/var/lib/clean-your-tv-installation';
var ID = /^[a-f0-9]{32}$/;
function removalRecord(name, size) {
  try {
    return JSON.parse(
      checkedBytes(PRODUCT + '/' + name, size, false).toString('utf8')
    );
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    return null;
  }
}
function observedRemoval(operation) {
  if (!ID.test(operation)) fail('Invalid removal intent');
  var binding = removalRecord('homebrew-removal-' + operation + '.json', 2048);
  if (!binding) return null;
  if (
    Object.keys(binding).sort().join(',') !== 'lease,operation,schema,target' ||
    binding.schema !== 1 ||
    binding.operation !== operation ||
    !ID.test(binding.target) ||
    (binding.lease !== '-' && !ID.test(binding.lease))
  )
    fail('Unverified removal intent');
  var record = removalRecord(
    'clean-removal-' + binding.target + '.json',
    4 * 1024 * 1024
  );
  var lease = removalRecord('operation.json', 2048);
  // The target can already have a historical receipt. It belongs to this
  // operation only when the independent removal intent matches exactly.
  if (!record || record.removal !== operation) return null;
  if (
    record.schema !== 1 ||
    record.protocol !== 'clean-removal-v1' ||
    record.operation !== binding.target ||
    !ID.test(record.lease) ||
    (binding.lease !== '-' && binding.lease !== record.lease)
  )
    fail('Unverified removal receipt');
  var current =
    lease &&
    lease.schema === 1 &&
    lease.owner === 'clean-removal' &&
    lease.journal === 'product-' + binding.target + '.json' &&
    (lease.id === record.lease ||
      (ID.test(record.final_fence) &&
        record.final_original_lease === record.lease &&
        lease.id === record.final_fence));
  // The locked writer saves the receipt before transferring the ownership
  // record. Only its exact predecessor may still finish that handoff.
  if (
    !current &&
    record.stage === 'requested' &&
    lease &&
    lease.id === binding.lease &&
    record.lease === lease.id &&
    lease.owner !== 'clean-removal'
  )
    return null;
  return {
    target: binding.target,
    intent: operation,
    record: record,
    current: current,
    ownerStage: current ? lease.stage : null,
    ownerLease: current ? lease.id : null
  };
}
function pinnedFile(context, name) {
  var expected = context.manifest.files[name];
  if (
    !expected ||
    !Number.isSafeInteger(expected.size) ||
    expected.size < 1 ||
    expected.size > 1024 * 1024
  )
    fail('Missing cleanup support');
  var bytes = checkedBytes(
    path.join(context.root, name),
    expected.size,
    true,
    expected
  );
  if (
    bytes.length !== expected.size ||
    crypto.createHash('sha256').update(bytes).digest('hex') !== expected.sha256
  )
    fail('Cleanup support changed');
  return bytes;
}
function invokeTail(context, work, mode) {
  var source = pinnedFile(context, 'root-updater/cleanup_tail.js');
  var node = '/usr/bin/node',
    command = node,
    scratch,
    identity,
    gate,
    pidLocks = ['0', '-1', '-1'],
    gateHash = '-';
  if (mode !== 'inspect') {
    gate = pinnedFile(context, 'installer-support/lifecycle-gate');
    executionBase();
    scratch =
      EXEC_BASE + '/cytv-root-tail-' + crypto.randomBytes(16).toString('hex');
    fs.mkdirSync(scratch, 448);
    identity = owned(scratch, true);
    command = scratch + '/gate';
    fs.writeFileSync(command, gate, { flag: 'wx', mode: 448 });
    if (!checkedBytes(command, gate.length, false).equals(gate))
      fail('Cleanup gate copy changed');
    pidLocks = ['3', '4', '5'];
    gateHash = crypto.createHash('sha256').update(gate).digest('hex');
  }
  var argv = (scratch ? ['root-clean-lock', node] : []).concat(
    [
      '-e',
      "var parts=[];process.stdin.on('data',function(b){parts.push(b);});process.stdin.on('end',function(){eval(Buffer.concat(parts).toString('utf8'));});",
      'cytv-cleanup-tail',
      mode,
      work.target,
      scratch || '-'
    ],
    pidLocks,
    [gateHash, work.intent]
  );
  return new Promise(function (resolve, reject) {
    var child = cp.execFile(
      command,
      argv,
      {
        env: { PATH: '/usr/sbin:/usr/bin:/sbin:/bin', LC_ALL: 'C' },
        timeout: 110000,
        maxBuffer: 65536
      },
      function (error, stdout) {
        try {
          if (scratch && exists(scratch)) {
            var info = owned(scratch, true);
            if (info.dev !== identity.dev || info.ino !== identity.ino)
              fail('Cleanup staging changed');
            if (exists(command)) {
              if (!checkedBytes(command, gate.length, false).equals(gate))
                fail('Cleanup gate changed');
              fs.unlinkSync(command);
            }
            fs.rmdirSync(scratch);
          }
          var reply = JSON.parse(stdout);
          if (reply.operation !== work.target || reply.removal !== work.intent)
            fail('Cleanup result does not match the confirmed operation');
          if (error && reply.state !== 'recovery_required') throw error;
          resolve(reply);
        } catch (failure) {
          reject(failure);
        }
      }
    );
    child.stdin.on('error', function () {});
    child.stdin.end(source);
  });
}
function removal(payloadRoot, pin, operation, action) {
  return Promise.resolve().then(function () {
    var work = observedRemoval(operation);
    var removeTile = action === 'homebrew-remove-tile';
    function answer(state, stage, code, current, resume) {
      return {
        action: 'remove',
        state: state,
        stage: stage,
        code: code,
        current: current,
        can_resume: resume
      };
    }
    function stale() {
      return answer(
        'recovery_required',
        'verified-clean',
        'removal-not-current',
        false,
        false
      );
    }
    if (!work) return removeTile ? stale() : null;
    if (!work.current) return stale();
    if (
      work.record.stage === 'verified-clean' &&
      work.record.state === 'complete'
    ) {
      if (
        !ID.test(work.record.final_fence) ||
        work.record.final_fence !== work.ownerLease
      )
        return stale();
      if (work.ownerStage === 'final-fence-pending') {
        if (removeTile) return stale();
        if (action === 'homebrew-remove-status')
          return answer(
            'recovery_required',
            'private-cleanup',
            'cleanup-check-failed',
            false,
            true
          );
        return verifiedPayload(payloadRoot, pin)
          .then(function (context) {
            return invokeTail(context, work, 'finish');
          })
          .then(function (result) {
            return result.state === 'complete' && result.current === true
              ? answer(
                  'complete',
                  'verified-clean',
                  'removal-verified',
                  true,
                  false
                )
              : answer(
                  'recovery_required',
                  'private-cleanup',
                  'cleanup-check-failed',
                  false,
                  true
                );
          });
      }
      if (work.ownerStage !== 'verified-clean') return stale();
      return verifiedPayload(payloadRoot, pin)
        .then(function (context) {
          return invokeTail(
            context,
            work,
            removeTile ? 'remove-installer' : 'verify'
          );
        })
        .then(function (result) {
          return result.state === 'verified-clean'
            ? answer(
                'complete',
                'verified-clean',
                removeTile ? 'installer-removed' : 'removal-verified',
                true,
                false
              )
            : stale();
        });
    }
    if (removeTile) return stale();
    if (!work.record.runtime_cleanup) return null;
    return verifiedPayload(payloadRoot, pin).then(function (context) {
      return invokeTail(context, work, 'inspect').then(function (result) {
        if (result.state !== 'tail-ready') return null;
        if (action === 'homebrew-remove-status')
          return answer(
            'recovery_required',
            'private-cleanup',
            'cleanup-check-failed',
            false,
            true
          );
        return invokeTail(context, work, 'finish').then(function (completed) {
          if (completed.state === 'complete' && completed.current === true)
            return answer(
              'complete',
              'verified-clean',
              'removal-verified',
              true,
              false
            );
          var pending = answer(
            'recovery_required',
            'private-cleanup',
            'cleanup-check-failed',
            false,
            true
          );
          if (completed.restart_required === true)
            pending.restart_required = true;
          return pending;
        });
      });
    });
  });
}
module.exports = {
  inspect: inspect,
  prepare: prepare,
  stage: stage,
  removal: removal
};
