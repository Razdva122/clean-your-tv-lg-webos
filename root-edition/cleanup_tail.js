'use strict';
// Current verified Node 8 support; runs under the ORIGINAL Ownership flock.
// Python must never rewrite completion after this process starts retirement.
var fs = require('fs'),
  nodeCrypto = require('crypto'),
  cp = require('child_process');
var C = fs.constants,
  uid = process.getuid(),
  mode = process.argv[2],
  id = process.argv[3],
  removal = process.argv[9];
var state = '/var/lib/clean-your-tv-installation',
  bootRoot = '/tmp/clean-your-tv-root-boot';
var runtime =
  '/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
var apps = [
  'com.cleanyourtv.root.preview',
  'com.cleanyourtv.root.updater',
  'com.cleanyourtv.system.updater',
  'com.cleanyourtv.updater',
  'com.local.nativehome',
  'com.gathin.tvhome'
];
var opened = [],
  directory,
  record,
  lease;
// Filled with the current shared cleaner by build_updater; no retained code.
var privateCleanupSource = null;
function at(fd, name) {
  return '/proc/self/fd/' + fd + (name ? '/' + name : '');
}
function identity(a, b) {
  return a.dev === b.dev && a.ino === b.ino;
}
function owned(info, dir) {
  if (
    info.uid !== uid ||
    info.mode & 18 ||
    (dir ? !info.isDirectory() : !info.isFile() || info.nlink !== 1)
  )
    throw Error('unsafe-cleanup-member');
}
function openDir(path, parent) {
  var fd = fs.openSync('/', C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW);
  opened.push(fd);
  path
    .split('/')
    .filter(Boolean)
    .forEach(function (name) {
      fd = fs.openSync(at(fd, name), C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW);
      opened.push(fd);
      var info = fs.fstatSync(fd);
      if (
        !info.isDirectory() ||
        (info.uid !== 0 && info.uid !== uid) ||
        (info.mode & 18 && !(info.mode & 512))
      )
        throw Error('unsafe-cleanup-directory');
    });
  var info = fs.fstatSync(fd);
  if (!(
    parent &&
    path === '/tmp' &&
    info.uid === 0 &&
    (info.mode & 4095) === 1023
  ))
    owned(info, true);
  return fd;
}
function read(fd, name) {
  var file = fs.openSync(
    at(fd, name),
    C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK
  );
  try {
    var info = fs.fstatSync(file);
    owned(info, false);
    if (info.size > 4194304) throw Error('oversized-cleanup-record');
    return fs.readFileSync(file);
  } finally {
    fs.closeSync(file);
  }
}
function json(fd, name) {
  return JSON.parse(read(fd, name).toString());
}
function write(fd, name, value) {
  var temp = '.clean-tail-' + nodeCrypto.randomBytes(16).toString('hex'),
    file = fs.openSync(
      at(fd, temp),
      C.O_WRONLY | C.O_CREAT | C.O_EXCL | C.O_NOFOLLOW,
      384
    );
  try {
    fs.writeFileSync(file, JSON.stringify(value));
    fs.fsyncSync(file);
  } finally {
    fs.closeSync(file);
  }
  fs.renameSync(at(fd, temp), at(fd, name));
  fs.fsyncSync(fd);
}
function exists(path) {
  try {
    fs.lstatSync(path);
    return true;
  } catch (e) {
    if (e.code === 'ENOENT') return false;
    throw e;
  }
}
function inheritedLock(value, path) {
  var fd = Number(value);
  if (!Number.isInteger(fd) || fd < 3) throw Error('original-lock-required');
  var info = fs.fstatSync(fd);
  owned(info, false);
  if (!identity(info, fs.lstatSync(path))) throw Error('original-lock-changed');
}
function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function packageReceipts() {
  if (
    !object(record.packages) ||
    Object.keys(record.packages).sort().join(',') !==
      apps.slice().sort().join(',')
  )
    throw Error('incomplete-removal-receipts');
  apps.forEach(function (app) {
    var item = record.packages[app];
    if (
      !object(item) ||
      item.state !== 'absent' ||
      !object(item.readback) ||
      item.readback.app !== app ||
      item.readback.absent !== true
    )
      throw Error('package-absence-unverified');
  });
  function format(value) {
    if (typeof value !== 'string') return null;
    var found =
      /^([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})(:session-[a-f0-9]{32})?$/.exec(
        value
      );
    return found &&
      found[0] === value &&
      found[1] !== '00000000-0000-0000-0000-000000000000'
      ? found[2]
        ? 'session'
        : 'kernel'
      : null;
  }
  var baseline = record.cleanup_boot_id,
    verified = record.cleanup_verified_boot_id;
  if (
    !format(baseline) ||
    format(baseline) !== format(verified) ||
    baseline === verified
  )
    throw Error('restart-required');
}
function rpc(method, payload) {
  var result = cp.spawnSync(
    '/usr/bin/luna-send',
    ['-n', '1', 'luna://' + method, JSON.stringify(payload)],
    { timeout: 15000, maxBuffer: 2097152 }
  );
  if (result.error || result.status !== 0)
    throw Error('cleanup-readback-unavailable');
  var value;
  try {
    value = JSON.parse(result.stdout.toString());
  } catch (_) {
    throw Error('cleanup-readback-malformed');
  }
  if (!object(value) || typeof value.returnValue !== 'boolean')
    throw Error('cleanup-readback-malformed');
  if (value.returnValue !== true) {
    var error = Error('cleanup-readback-unavailable');
    error.systemprofile_missing =
      method === 'com.webos.service.systemprofile/getProfiles' &&
      value.errorCode === -1 &&
      value.errorText ===
        'Service does not exist: com.webos.service.systemprofile.';
    throw error;
  }
  return value;
}
function absent(final) {
  if (final && exists(bootRoot)) throw Error('boot-session-remains');
  var inventory;
  try {
    inventory = rpc('com.webos.applicationManager/dev/listApps', {}).apps;
  } catch (error) {
    if (error.message !== 'cleanup-readback-unavailable') throw error;
    inventory = rpc('com.webos.applicationManager/listApps', {}).apps;
  }
  if (
    !Array.isArray(inventory) ||
    inventory.some(function (a) {
      return (
        !object(a) ||
        typeof a.id !== 'string' ||
        !a.id ||
        apps.indexOf(a.id) !== -1
      );
    })
  )
    throw Error('package-remains');
  apps.forEach(function (app) {
    [
      'applications/' + app,
      'packages/' + app,
      'services/' +
        app +
        (app === 'com.gathin.tvhome' ? '.renewal' : '.service')
    ].forEach(function (name) {
      if (exists('/media/developer/apps/usr/palm/' + name))
        throw Error('package-remains');
    });
  });
  [
    '50-clean-your-tv-root',
    '51-clean-your-tv-root-updater',
    '52-clean-your-tv-system-updater'
  ].forEach(function (name) {
    if (exists('/var/lib/webosbrew/init.d/' + name))
      throw Error('startup-remains');
  });
  [
    '/var/luna-service2/manifests.d/com.cleanyourtv.root.preview.recovery.json',
    '/var/webos-profile/override/clean-your-tv-root.json',
    '/media/developer/.cytv-installer'
  ].forEach(function (path) {
    if (exists(path)) throw Error('owned-private-registration-remains');
  });
  if (privateCleanupSource) {
    var inspected = cp.spawnSync(
      '/usr/bin/node',
      [
        '-e',
        privateCleanupSource,
        JSON.stringify({
          action: 'inventory',
          staging_ids: record.cleanup_staging_ids || []
        })
      ],
      { timeout: 90000, maxBuffer: 2097152 }
    );
    if (inspected.error || inspected.status !== 0)
      throw Error('no-root-private-readback-unavailable');
    var privateState = JSON.parse(inspected.stdout.toString());
    if (
      privateState.schema !== 1 ||
      !Array.isArray(privateState.present) ||
      !Array.isArray(privateState.blocked) ||
      privateState.present.length ||
      privateState.blocked.length
    )
      throw Error('no-root-private-cleanup-required');
  }
  if (final)
    fs.readdirSync('/tmp').forEach(function (name) {
      if (
        /^cytv-(?:product|coordinator|system-updater|c1-root|root-tail)-[a-f0-9]{32}$/.test(
          name
        )
      ) {
        var fd = openDir('/tmp/' + name);
        if (fs.readdirSync(at(fd)).length) throw Error('support-stage-remains');
      }
    });
  var settings = rpc('com.webos.settingsservice/getSystemSettings', {
    category: 'general',
    keys: ['defaultApps']
  });
  var home = settings.settings.defaultApps.home,
    stockOnly =
      record.profileless_cleanup_eligible === true &&
      object(record.routes) &&
      record.routes.mode === 'stock-settings' &&
      record.routes.home === 'com.webos.app.home' &&
      home === record.routes.home,
    profiles,
    never =
      record.routing_never_applied === true &&
      record.routes &&
      record.routes.mode === 'never-applied';
  if (typeof home !== 'string' || !home || apps.indexOf(home) !== -1)
    throw Error('owned-route-remains');
  try {
    profiles = rpc('com.webos.service.systemprofile/getProfiles', {
      names: ['defaultApps', 'idleApp'],
      subscribe: false
    }).profiles;
    if (!object(profiles)) throw Error('cleanup-readback-malformed');
  } catch (error) {
    if (!never && !(stockOnly && error.systemprofile_missing === true))
      throw error;
  }
  if (profiles) {
    if (stockOnly) throw Error('route-changed');
    var routes = [
      home,
      profiles.defaultApps.categories.home,
      profiles.idleApp.appId
    ];
    if (
      routes.some(function (route) {
        return (
          typeof route !== 'string' || !route || apps.indexOf(route) !== -1
        );
      })
    )
      throw Error('owned-route-remains');
    if (!never && JSON.stringify(routes) !== JSON.stringify(record.routes))
      throw Error('route-changed');
  }
  if (never && home !== record.routes.home) throw Error('route-changed');
  [
    'services.d',
    'roles.d',
    'client-permissions.d',
    'api-permissions.d',
    'manifests.d',
    'groups.d'
  ].forEach(function (folder) {
    var path = '/var/luna-service2-dev/' + folder;
    if (!exists(path)) return;
    var fd = openDir(path);
    if (
      fs.readdirSync(at(fd)).some(function (name) {
        return apps.some(function (app) {
          return name.indexOf(app + '.') === 0;
        });
      })
    )
      throw Error('owned-registration-remains');
  });
  ['root', 'root-updater', 'system-updater'].forEach(
    function (component, index) {
      var path = '/var/lib/clean-your-tv-' + component;
      if (!exists(path)) return;
      var fd = openDir(path),
        keep =
          index === 0
            ? ['deploy.json', 'provision.lock']
            : ['bootstrap.json', 'daemon.lock', 'worker.lock'];
      if (
        fs.readdirSync(at(fd)).some(function (name) {
          return keep.indexOf(name) === -1;
        })
      )
        throw Error('private-member-remains');
    }
  );
  var activities = rpc('com.palm.activitymanager/list', {
    details: true,
    subscribers: true,
    current: false,
    internal: false
  }).activities;
  if (
    !Array.isArray(activities) ||
    activities.some(function (item) {
      return (
        !item ||
        item.name === 'com.cleanyourtv.root.preview.service.recovery' ||
        apps.some(function (app) {
          return (
            String((item.callback || {}).method || '').indexOf(
              'luna://' +
                app +
                (app === 'com.gathin.tvhome' ? '.renewal/' : '.service/')
            ) === 0
          );
        })
      );
    })
  )
    throw Error('owned-activity-remains');
  var inputs = rpc('com.webos.service.eim/getAllInputStatus', {}).devices;
  if (
    !Array.isArray(inputs) ||
    inputs.some(function (item) {
      return (
        item.id === 'com.gathin.tvhome' || item.appId === 'com.gathin.tvhome'
      );
    })
  )
    throw Error('owned-input-remains');
  fs.readdirSync('/proc')
    .filter(function (n) {
      return (
        /^[0-9]+$/.test(n) &&
        Number(n) !== process.pid &&
        !(
          process.argv[4] === '-' &&
          record.runtime_cleanup.parent_pid === process.ppid &&
          Number(n) === process.ppid
        )
      );
    })
    .forEach(function (pid) {
      var args;
      try {
        args = fs
          .readFileSync('/proc/' + pid + '/cmdline')
          .toString()
          .split('\0');
      } catch (e) {
        if (e.code === 'ENOENT') return;
        throw e;
      }
      try {
        args.push(fs.readlinkSync('/proc/' + pid + '/exe'));
      } catch (e) {
        if (e.code !== 'ENOENT') throw e;
      }
      var prefixes = [
        runtime + '/',
        '/var/lib/clean-your-tv-root/',
        '/var/lib/clean-your-tv-root-updater/',
        '/var/lib/clean-your-tv-system-updater/',
        '/tmp/clean-your-tv-root-gate/'
      ];
      apps.forEach(function (app) {
        prefixes.push(
          '/media/developer/apps/usr/palm/applications/' + app + '/'
        );
        prefixes.push(
          '/media/developer/apps/usr/palm/services/' +
            app +
            (app === 'com.gathin.tvhome' ? '.renewal/' : '.service/')
        );
      });
      (record.archives || []).forEach(function (item) {
        prefixes.push(item.path + '/');
      });
      if (
        args.some(function (arg) {
          return prefixes.some(function (prefix) {
            return arg === prefix.slice(0, -1) || arg.indexOf(prefix) === 0;
          });
        })
      )
        throw Error('owned-process-still-used');
    });
}
function retire(path, inventory, pin, removeRoot) {
  if (!exists(path)) return;
  var root = openDir(path),
    info = fs.fstatSync(root),
    plan = [];
  if (pin && (info.dev !== pin.dev || info.ino !== pin.ino))
    throw Error('cleanup-root-changed');
  function scan(fd, prefix) {
    fs.readdirSync(at(fd))
      .sort()
      .forEach(function (name) {
        var relative = prefix + name,
          full = at(fd, name),
          info = fs.lstatSync(full);
        if (info.isSymbolicLink()) {
          if (
            info.uid !== uid ||
            !inventory ||
            !Object.prototype.hasOwnProperty.call(inventory, relative)
          )
            throw Error('unsafe-cleanup-member');
          plan.push({ fd: fd, name: name, info: info, dir: false });
          return;
        }
        owned(info, info.isDirectory());
        if (info.isDirectory()) {
          if (
            inventory &&
            !Object.keys(inventory).some(function (n) {
              return n.indexOf(relative + '/') === 0;
            })
          )
            throw Error('unknown-runtime-directory');
          if (
            !inventory &&
            !prefix &&
            ['root', 'root-updater'].indexOf(name) === -1
          )
            throw Error('unknown-support-directory');
          var child = fs.openSync(
            full,
            C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW
          );
          opened.push(child);
          if (!identity(info, fs.fstatSync(child)))
            throw Error('cleanup-member-changed');
          scan(child, relative + '/');
          plan.push({ fd: fd, name: name, info: info, dir: true });
        } else {
          if (!inventory && !prefix) throw Error('unknown-support-member');
          if (inventory) {
            if (!Object.prototype.hasOwnProperty.call(inventory, relative))
              throw Error('unknown-runtime-member');
            var file = fs.openSync(
              full,
              C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK
            );
            try {
              if (!identity(info, fs.fstatSync(file)))
                throw Error('runtime-member-changed');
            } finally {
              fs.closeSync(file);
            }
          }
          plan.push({ fd: fd, name: name, info: info, dir: false });
        }
      });
  }
  scan(root, '');
  plan.forEach(function (item) {
    if (!identity(item.info, fs.lstatSync(at(item.fd, item.name))))
      throw Error('cleanup-member-changed');
  });
  plan.forEach(function (item) {
    var path = at(item.fd, item.name);
    if (!identity(item.info, fs.lstatSync(path)))
      throw Error('cleanup-member-changed');
    (item.dir ? fs.rmdirSync : fs.unlinkSync)(path);
    fs.fsyncSync(item.fd);
  });
  if (removeRoot) {
    var slash = path.lastIndexOf('/'),
      parent = openDir(path.slice(0, slash), true),
      name = path.slice(slash + 1);
    if (!identity(fs.fstatSync(root), fs.lstatSync(at(parent, name))))
      throw Error('cleanup-root-changed');
    fs.rmdirSync(at(parent, name));
    fs.fsyncSync(parent);
  }
}
try {
  if (!/^[a-f0-9]{32}$/.test(id)) throw Error('invalid-cleanup-selector');
  directory = openDir(state);
  try {
    record = json(directory, 'clean-removal-' + id + '.json');
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  if (
    typeof removal !== 'string' ||
    !/^[a-f0-9]{32}$/.test(removal) ||
    (record && record.removal !== removal)
  )
    throw Error('different-removal-intent');
  if (mode === 'inspect') {
    process.stdout.write(
      JSON.stringify({
        operation: id,
        removal: removal,
        state: record && record.runtime_cleanup ? 'tail-ready' : 'not-ready'
      })
    );
  } else {
    var lock = Number(process.argv[5]);
    if (!Number.isInteger(lock) || lock < 3)
      throw Error('original-lock-required');
    var info = fs.fstatSync(lock);
    owned(info, false);
    if (!identity(info, fs.lstatSync(at(directory, 'ownership.lock'))))
      throw Error('original-lock-changed');
    if (exists('/var/lib/clean-your-tv-python'))
      inheritedLock(
        process.argv[6],
        '/var/lib/clean-your-tv-python/.install.lock'
      );
    else if (Number(process.argv[6]) !== -1 && Number(process.argv[6]) !== 4)
      throw Error('unexpected-promotion-lock');
    inheritedLock(process.argv[7], at(directory, 'worker.lock'));
    lease = json(directory, 'operation.json');
    if (
      !lease ||
      Object.keys(lease).sort().join(',') !==
        'id,journal,owner,schema,stage,terminal' ||
      lease.schema !== 1 ||
      typeof lease.id !== 'string' ||
      !/^[a-f0-9]{32}$/.test(lease.id) ||
      ['private-cleanup', 'verified-clean'].indexOf(lease.stage) === -1 ||
      lease.terminal !== false
    )
      throw Error('unknown-ownership-receipt');
    if (
      !record ||
      record.schema !== 1 ||
      record.protocol !== 'clean-removal-v1' ||
      record.operation !== id ||
      record.lease !== lease.id ||
      typeof record.removal !== 'string' ||
      !/^[a-f0-9]{32}$/.test(record.removal) ||
      lease.owner !== 'clean-removal' ||
      lease.journal !== 'product-' + id + '.json' ||
      ['private-cleanup', 'verified-clean'].indexOf(record.stage) === -1 ||
      record.state !==
        (record.stage === 'verified-clean'
          ? 'complete'
          : 'recovery_required') ||
      !Array.isArray(record.done) ||
      [
        'original-writers-fenced',
        'controls-restored',
        'package-removal',
        'private-cleanup'
      ].some(function (stage) {
        return record.done.indexOf(stage) === -1;
      }) ||
      !record.result ||
      record.result.removed !== true ||
      record.result.applications_services_startup_removed !== true ||
      typeof record.result.private_cleanup_verified !== 'boolean'
    )
      throw Error('original-removal-required');
    packageReceipts();
    var cleanup = record.runtime_cleanup;
    if (
      !cleanup ||
      cleanup.root !== runtime ||
      !cleanup.files ||
      typeof cleanup.files !== 'object' ||
      Array.isArray(cleanup.files)
    )
      throw Error('runtime-cleanup-proof-required');
    Object.keys(cleanup.files).forEach(function (name) {
      if (
        !/^(?:[a-zA-Z0-9_.+-]+\/)*[a-zA-Z0-9_.+-]+$/.test(name) ||
        name.split('/').some(function (p) {
          return p === '.' || p === '..';
        }) ||
        !/^[a-f0-9]{64}$/.test(cleanup.files[name])
      )
        throw Error('invalid-runtime-inventory');
    });
    if (
      cleanup.promotion_required === true &&
      !exists('/var/lib/clean-your-tv-python/.install.lock')
    )
      throw Error('original-promotion-lock-missing');
    var gates = record.tail_stages || [];
    if (!Array.isArray(gates)) throw Error('invalid-tail-stages');
    (process.argv[4] === '-' ? [] : process.argv[4].split(',')).forEach(
      function (path) {
        if (!/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(path))
          throw Error('invalid-tail-stage');
        if (
          !exists(path) ||
          gates.some(function (entry) {
            return entry.path === path;
          })
        )
          return;
        var fd = openDir(path),
          info = fs.fstatSync(fd);
        gates.push({ path: path, dev: info.dev, ino: info.ino });
      }
    );
    record.tail_stages = gates;
    write(directory, 'clean-removal-' + id + '.json', record);
    // The parent is allowed to wait for its own child tail with the same flock.
    // Other users of this private runtime prevent retirement.
    absent(false);
    (record.support_stages || []).forEach(function (stage) {
      if (!/^\/tmp\/cytv-product-[a-f0-9]{32}$/.test(stage.path))
        throw Error('invalid-support-stage');
      retire(stage.path, null, stage);
    });
    retire(runtime, cleanup.files, null, true);
    retire(
      bootRoot,
      { 'session.lock': true, 'session.json': true, 'normal.json': true },
      null,
      true
    );
    gates.forEach(function (entry) {
      if (!/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(entry.path))
        throw Error('invalid-tail-stage');
      if (!exists(entry.path)) return;
      var gatefd = openDir(entry.path),
        info = fs.fstatSync(gatefd),
        names = fs.readdirSync(at(gatefd));
      if (
        info.dev !== entry.dev ||
        info.ino !== entry.ino ||
        names.some(function (name) {
          return name !== 'gate';
        })
      )
        throw Error('unknown-tail-stage');
      if (names.length) {
        var executable = fs.lstatSync(at(gatefd, 'gate'));
        owned(executable, false);
        fs.unlinkSync(at(gatefd, 'gate'));
        fs.fsyncSync(gatefd);
      }
    });
    absent(true);
    record.stage = 'verified-clean';
    record.state = 'complete';
    record.current = true;
    record.reason = 'removal-verified';
    record.result.private_cleanup_verified = true;
    record.result.verified_clean = true;
    cleanup.files = {};
    delete cleanup.parent_pid;
    write(directory, 'clean-removal-' + id + '.json', record);
    lease.stage = 'verified-clean';
    write(directory, 'operation.json', lease);
    process.stdout.write(
      JSON.stringify({
        operation: id,
        removal: removal,
        state: 'complete',
        stage: 'verified-clean',
        current: true,
        reason: 'removal-verified',
        result: record.result
      })
    );
  }
} catch (error) {
  if (mode === 'inspect' && error.code === 'ENOENT')
    process.stdout.write(
      JSON.stringify({ operation: id, removal: removal, state: 'not-ready' })
    );
  else {
    var known =
      'boot-session-remains cleanup-member-changed cleanup-readback-malformed cleanup-readback-unavailable cleanup-root-changed different-removal-intent incomplete-removal-receipts invalid-cleanup-selector invalid-runtime-inventory invalid-support-stage invalid-tail-stage invalid-tail-stages no-root-private-cleanup-required no-root-private-readback-unavailable original-lock-changed original-lock-required original-promotion-lock-missing original-removal-required oversized-cleanup-record owned-activity-remains owned-input-remains owned-private-registration-remains owned-process-still-used owned-registration-remains owned-route-remains package-absence-unverified package-remains private-member-remains restart-required route-changed runtime-cleanup-proof-required runtime-member-changed startup-remains support-stage-remains unexpected-promotion-lock unknown-ownership-receipt unknown-runtime-directory unknown-runtime-member unknown-support-directory unknown-support-member unknown-tail-stage unsafe-cleanup-directory unsafe-cleanup-member'.split(
        ' '
      );
    var diagnostic =
      known.indexOf(error.message) !== -1
        ? error.message
        : 'cleanup-guard-failed';
    process.stderr.write('CYTV_CLEAN_TAIL: ' + diagnostic + '\n');
    process.stdout.write(
      JSON.stringify({
        operation: id,
        removal: removal,
        state: 'recovery_required',
        stage: 'private-cleanup',
        current: false,
        reason: 'private-cleanup-incomplete',
        cleanup_error: diagnostic
      })
    );
    process.exitCode = 1;
  }
} finally {
  opened.reverse().forEach(function (fd) {
    try {
      fs.closeSync(fd);
    } catch (e) {}
  });
}
