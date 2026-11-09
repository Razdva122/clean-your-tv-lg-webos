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
    var raw = Buffer.alloc(info.size),
      offset = 0;
    while (offset < raw.length) {
      var count = fs.readSync(file, raw, offset, raw.length - offset, offset);
      if (count <= 0) throw Error('cleanup-member-changed');
      offset += count;
    }
    if (fs.fstatSync(file).size !== info.size)
      throw Error('cleanup-member-changed');
    return raw;
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
    var raw = Buffer.from(JSON.stringify(value)),
      offset = 0;
    while (offset < raw.length) {
      var count = fs.writeSync(file, raw, offset, raw.length - offset, null);
      if (count <= 0) throw Error('cleanup-member-changed');
      offset += count;
    }
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
// Yield between children on legacy TV libuv; keep Luna stdin open until exit.
function childRead(command, args, timeout) {
  return new Promise(function (resolve, reject) {
    setImmediate(function () {
      var child,
        timer,
        chunks = [],
        size = 0,
        failure;
      try {
        child = cp.spawn(command, args, { stdio: ['pipe', 'pipe', 'pipe'] });
      } catch (_) {
        reject(Error('cleanup-readback-unavailable'));
        return;
      }
      function stop(reason) {
        if (!failure) failure = Error(reason);
        child.kill('SIGKILL');
      }
      timer = setTimeout(function () {
        stop('cleanup-readback-unavailable');
      }, timeout);
      child.on('error', function () {
        failure = Error('cleanup-readback-unavailable');
      });
      child.stdin.on('error', function () {
        failure = Error('cleanup-readback-unavailable');
      });
      child.stdout.on('data', function (chunk) {
        size += chunk.length;
        if (size > 2097152) {
          stop('cleanup-readback-malformed');
          return;
        }
        if (!failure) chunks.push(chunk);
      });
      child.stderr.on('data', function (chunk) {
        size += chunk.length;
        if (size > 2097152) stop('cleanup-readback-malformed');
      });
      child.on('close', function (code, signal) {
        clearTimeout(timer);
        if (failure || code !== 0 || signal)
          reject(failure || Error('cleanup-readback-unavailable'));
        else resolve(Buffer.concat(chunks).toString());
      });
    });
  });
}
async function rpc(method, payload) {
  var raw = await childRead(
    '/usr/bin/luna-send',
    ['-n', '1', 'luna://' + method, JSON.stringify(payload)],
    15000
  );
  var value;
  try {
    value = JSON.parse(raw);
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
function unownedRouting() {
  var evidence = [
    'profile-trial.json',
    'persistent-intent.json',
    'persistent-binding.json',
    'boot-continuation.json',
    'profile-candidate.stage',
    'home-backend.json',
    'c1-gate',
    'c1-keyfilter'
  ];
  if (record.profileless_cleanup_eligible !== true) return false;
  var backup = json(directory, 'routing-backup-' + id + '.json');
  return (
    object(backup) &&
    !Object.keys(backup).some(function (name) {
      return evidence.indexOf(name.split('/')[0]) !== -1;
    }) &&
    !evidence.some(function (name) {
      return exists('/var/lib/clean-your-tv-root/' + name);
    }) &&
    !exists('/var/webos-profile/override/clean-your-tv-root.json')
  );
}
function routingUntouched() {
  var deploy = record.fenced_components && record.fenced_components.deploy;
  if (
    record.routing_never_applied !== true ||
    record.profileless_cleanup_eligible !== true ||
    !object(deploy) ||
    !(
      [
        'prepared',
        'install-submitting',
        'install-accepted',
        'install-observed',
        'payload-verified',
        'personalization-complete'
      ].indexOf(deploy.stage) !== -1 ||
      /^provision-(?:apply|resume_pending|refresh|finalize)-(?:starting|complete)$/.test(
        deploy.stage
      )
    )
  )
    return false;
  return unownedRouting();
}
async function compositorStock() {
  if (
    [
      '/media/developer/cleanyourtv',
      '/var/lib/tvweb/home-takeover',
      '/var/lib/luma-home',
      '/var/lib/webosbrew/homechooser'
    ].some(exists)
  )
    throw Error('route-changed');
  var bindingRoot = '/home/root/.config/lginputhook';
  if (exists(bindingRoot + '/keybinds.json')) {
    var bindingsRaw = read(openDir(bindingRoot), 'keybinds.json');
    var bindings = JSON.parse(bindingsRaw.toString());
    if (
      bindingsRaw.length > 65536 ||
      !object(bindings) ||
      Object.prototype.hasOwnProperty.call(bindings, '773')
    )
      throw Error('route-changed');
  }
  var proof = record.routes,
    home = '/usr/bin/com.webos.app.home',
    app = '/usr/palm/applications/com.webos.app.home';
  if (
    !unownedRouting() ||
    !object(proof.target) ||
    !/^[a-f0-9]{64}$/.test(proof.target_sha256)
  )
    throw Error('route-changed');
  var before = fs.lstatSync(home),
    raw = read(openDir('/usr/bin'), 'com.webos.app.home');
  if (
    !before.isFile() ||
    !(before.mode & 73) ||
    before.dev !== proof.target.dev ||
    before.ino !== proof.target.ino ||
    before.size !== proof.target.size ||
    raw.length < 52 ||
    raw.slice(0, 7).toString('hex') !== '7f454c46010101' ||
    raw[18] !== 40 ||
    raw[19] !== 0 ||
    nodeCrypto.createHash('sha256').update(raw).digest('hex') !==
      proof.target_sha256 ||
    !identity(before, fs.lstatSync(home))
  )
    throw Error('route-changed');
  var manifest = JSON.parse(read(openDir(app), 'appinfo.json').toString());
  if (
    manifest.id !== 'com.webos.app.home' ||
    manifest.type !== 'native' ||
    [home, 'file://' + home].indexOf(manifest.main) === -1
  )
    throw Error('route-changed');
  var mounts = fs.readFileSync('/proc/self/mountinfo', 'utf8'),
    systemImage = false;
  if (!mounts || mounts.length > 1048576) throw Error('route-changed');
  mounts
    .trim()
    .split('\n')
    .forEach(function (line) {
      var fields = line.split(/\s+/),
        separator = fields.indexOf('-');
      if (separator < 6 || fields.length !== separator + 4)
        throw Error('route-changed');
      var target = fields[4].replace(/\\([0-7]{3})/g, function (_, octal) {
        return String.fromCharCode(parseInt(octal, 8));
      });
      if (
        target === '/' ||
        ![home, app].some(function (path) {
          return path === target || path.indexOf(target + '/') === 0;
        })
      )
        return;
      var mmc = /^179:([0-9]+)$/.exec(fields[2]);
      if (
        target !== '/usr' ||
        systemImage ||
        fields[3] !== '/' ||
        !mmc ||
        Number(mmc[1]) >= 256 ||
        fields[separator + 1] !== 'squashfs' ||
        !/^\/dev\/mmcblk[0-9]+p[0-9]+$/.test(fields[separator + 2]) ||
        ![fields[5], fields[separator + 3]].every(function (options) {
          options = options.split(',');
          return options.indexOf('ro') !== -1 && options.indexOf('rw') === -1;
        }) ||
        before.dev !== 179 * 256 + Number(mmc[1]) ||
        fs.lstatSync(app).dev !== before.dev
      )
        throw Error('route-changed');
      systemImage = true;
    });
  try {
    await rpc('com.webos.service.systemprofile/getProfiles', {
      names: ['defaultApps', 'idleApp'],
      subscribe: false
    });
    throw Error('route-changed');
  } catch (error) {
    if (error.systemprofile_missing !== true) throw error;
  }
  var chain = (
    await rpc('com.webos.service.config/getConfigs', {
      configNames: ['com.webos.surfacemanager.keyFilters']
    })
  ).configs;
  chain = chain && chain['com.webos.surfacemanager.keyFilters'];
  if (
    !Array.isArray(chain) ||
    !chain.length ||
    chain.length > 128 ||
    JSON.stringify(chain).length > 16384 ||
    chain.filter(function (entry) {
      return (
        object(entry) &&
        /\/systemUi\.js$/.test(entry.file) &&
        entry.handler === 'handleSystemKeys'
      );
    }).length !== 1
  )
    throw Error('route-changed');
  chain.forEach(function (entry) {
    if (
      !object(entry) ||
      typeof entry.file !== 'string' ||
      !/^\/usr\/lib\/(?:qt5\/)?qml\/KeyFilters\/[A-Za-z0-9_-]+\.js$/.test(
        entry.file
      ) ||
      typeof entry.handler !== 'string' ||
      !/^[A-Za-z_$][A-Za-z0-9_$]{0,127}$/.test(entry.handler)
    )
      throw Error('route-changed');
    var path = fs.realpathSync(entry.file),
      slash = path.lastIndexOf('/');
    if (
      !/^\/usr\/lib\/(?:qt5\/)?qml\/KeyFilters\/[A-Za-z0-9_-]+\.js$/.test(
        path
      ) ||
      path.slice(slash + 1) !==
        entry.file.slice(entry.file.lastIndexOf('/') + 1)
    )
      throw Error('route-changed');
    var script = read(openDir(path.slice(0, slash)), path.slice(slash + 1));
    if (
      script.length > 262144 ||
      (/\/systemUi\.js$/.test(path) &&
        (script.toString().indexOf('Qt.Key_Super_L') === -1 ||
          !/function\s+handleSystemKeys\s*\(/.test(script.toString())))
    )
      throw Error('route-changed');
  });
}
async function absent(final) {
  if (final && exists(bootRoot)) throw Error('boot-session-remains');
  var inventory;
  try {
    inventory = (await rpc('com.webos.applicationManager/dev/listApps', {}))
      .apps;
  } catch (error) {
    if (error.message !== 'cleanup-readback-unavailable') throw error;
    inventory = (await rpc('com.webos.applicationManager/listApps', {})).apps;
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
    var inspected;
    try {
      inspected = await childRead(
        '/usr/bin/node',
        [
          '-e',
          privateCleanupSource,
          JSON.stringify({
            action: 'inventory',
            staging_ids: record.cleanup_staging_ids || []
          })
        ],
        90000
      );
    } catch (_) {
      throw Error('no-root-private-readback-unavailable');
    }
    var privateState = JSON.parse(inspected);
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
        var fd = openDir('/tmp/' + name),
          info = fs.fstatSync(fd);
        if (
          /^cytv-system-updater-[a-f0-9]{32}$/.test(name) &&
          (record.retained_temporary_stages || []).some(function (entry) {
            return (
              object(entry) &&
              Object.keys(entry).length === 3 &&
              entry.path === '/tmp/' + name &&
              entry.dev === info.dev &&
              entry.ino === info.ino
            );
          })
        )
          return;
        if (fs.readdirSync(at(fd)).length) throw Error('support-stage-remains');
      }
    });
  // No Home consumer setting is required when the fenced original operation
  // never reached routing and both original inverse and current paths agree.
  if (object(record.routes) && record.routes.mode === 'stock-compositor') {
    await compositorStock();
  } else if (!(
    object(record.routes) &&
    record.routes.mode === 'never-applied' &&
    Object.keys(record.routes).length === 1 &&
    routingUntouched()
  )) {
    var settings = await rpc('com.webos.settingsservice/getSystemSettings', {
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
      profiles = (
        await rpc('com.webos.service.systemprofile/getProfiles', {
          names: ['defaultApps', 'idleApp'],
          subscribe: false
        })
      ).profiles;
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
  }
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
  var activityRequest = {
    details: true,
    subscribers: true,
    current: false,
    internal: false
  };
  var activityReply;
  try {
    activityReply = await rpc('com.palm.activitymanager/list', activityRequest);
  } catch (error) {
    if (error.message !== 'cleanup-readback-unavailable') throw error;
    activityReply = await rpc(
      'com.palm.activitymanager/getActivityInfo',
      activityRequest
    );
  }
  var activities = activityReply.activities;
  if (
    !Array.isArray(activities) ||
    activities.some(function (item) {
      return (
        !object(item) ||
        (item.callback !== undefined && !object(item.callback)) ||
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
  var inputs = (await rpc('com.webos.service.eim/getAllInputStatus', {}))
    .devices;
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
      (record.retained_temporary_stages || []).forEach(function (entry) {
        if (
          object(entry) &&
          /^\/tmp\/cytv-system-updater-[a-f0-9]{32}$/.test(entry.path)
        )
          prefixes.push(entry.path + '/');
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
function retire(path, inventory, pin, removeRoot, scratch) {
  if (scratch && !/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(path))
    throw Error('invalid-tail-stage');
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
            (!scratch &&
              (!inventory ||
                !Object.prototype.hasOwnProperty.call(inventory, relative)))
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
            !scratch &&
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
          if (!inventory && !scratch && !prefix)
            throw Error('unknown-support-member');
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
function finalizeFence() {
  var final = record.final_fence || nodeCrypto.randomBytes(16).toString('hex');
  if (!/^[a-f0-9]{32}$/.test(final) || final === record.lease)
    throw Error('unknown-ownership-receipt');
  record.final_fence = final;
  record.final_original_lease = record.lease;
  record.stage = 'private-cleanup';
  record.state = 'recovery_required';
  record.current = false;
  write(directory, 'clean-removal-' + id + '.json', record);
  lease.id = final;
  lease.stage = 'final-fence-pending';
  write(directory, 'operation.json', lease);
  record.stage = 'verified-clean';
  record.state = 'complete';
  record.current = true;
  record.reason = 'removal-verified';
  write(directory, 'clean-removal-' + id + '.json', record);
  lease.stage = 'verified-clean';
  write(directory, 'operation.json', lease);
}
// The saved host goal names whole private scratch directories, not file states.
// Their contents are inert; confinement and ownership, not filenames, gate cleanup.
function retireHostStages() {
  var stages = process.argv[4] === '-' ? [] : process.argv[4].split(',');
  if (
    stages.length > 128 ||
    stages.some(function (stage) {
      return !/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(stage);
    })
  )
    throw Error('invalid-tail-stages');
  stages.forEach(function (stage) {
    retire(stage, null, null, true, true);
  });
}
function completion() {
  return {
    operation: id,
    removal: removal,
    state: 'complete',
    stage: 'verified-clean',
    current: true,
    reason: 'removal-verified',
    result: record.result
  };
}
(async function main() {
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
    } else if (mode === 'stock-proof') {
      // Read-only helper for the coordinator while it owns the original mutex.
      // It grants no deletion/lease authority and cannot turn an install into success.
      if (
        !record ||
        record.schema !== 1 ||
        record.operation !== id ||
        record.protocol !== 'clean-removal-v1' ||
        !object(record.routes) ||
        record.routes.mode !== 'stock-compositor'
      )
        throw Error('original-removal-required');
      await compositorStock();
      process.stdout.write(JSON.stringify({ routes: record.routes }));
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
      var predecessor =
        lease.owner === 'clean-removal' &&
        lease.journal === 'product-' + id + '.json';
      if (
        mode === 'verify' &&
        lease.owner === 'no-root' &&
        /^no-root-[a-f0-9]{32}\.json$/.test(lease.journal) &&
        lease.stage === 'reserved'
      ) {
        var successor = json(directory, lease.journal);
        predecessor =
          successor &&
          successor.schema === 1 &&
          successor.protocol === 'no-root-root-handoff-v1' &&
          successor.lease === lease.id &&
          successor.predecessor &&
          successor.predecessor.operation === id &&
          successor.predecessor.removal === removal &&
          successor.predecessor.lease ===
            (record.final_fence || record.lease) &&
          successor.predecessor.lease !== lease.id;
      }
      if (
        !lease ||
        Object.keys(lease).sort().join(',') !==
          'id,journal,owner,schema,stage,terminal' ||
        lease.schema !== 1 ||
        typeof lease.id !== 'string' ||
        !/^[a-f0-9]{32}$/.test(lease.id) ||
        (['private-cleanup', 'verified-clean', 'final-fence-pending'].indexOf(
          lease.stage
        ) === -1 &&
          !(mode === 'verify' && predecessor && lease.stage === 'reserved')) ||
        lease.terminal !== false
      )
        throw Error('unknown-ownership-receipt');
      if (
        !record ||
        record.schema !== 1 ||
        record.protocol !== 'clean-removal-v1' ||
        record.operation !== id ||
        (record.final_fence &&
          (record.final_original_lease !== record.lease ||
            !/^[a-f0-9]{32}$/.test(record.final_fence) ||
            record.final_fence === record.lease)) ||
        (record.lease !== lease.id &&
          record.final_fence !== lease.id &&
          !(mode === 'verify' && predecessor && lease.owner === 'no-root')) ||
        typeof record.removal !== 'string' ||
        !/^[a-f0-9]{32}$/.test(record.removal) ||
        !predecessor ||
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
      if (
        mode === 'verify' ||
        mode === 'finalize' ||
        record.final_fence === lease.id ||
        record.stage === 'verified-clean'
      ) {
        var pendingFinal =
          mode === 'finish' &&
          record.final_fence === lease.id &&
          lease.stage === 'final-fence-pending';
        if (
          (!pendingFinal &&
            lease.stage !== 'verified-clean' &&
            lease.owner !== 'no-root') ||
          (!pendingFinal && record.stage !== 'verified-clean') ||
          (!pendingFinal && record.current !== true) ||
          record.result.private_cleanup_verified !== true ||
          record.result.verified_clean !== true ||
          !record.runtime_cleanup ||
          Object.keys(record.runtime_cleanup.files || {}).length ||
          exists(runtime)
        )
          throw Error('original-removal-required');
        // Admission is a current readback, never another cleanup attempt.
        // Keep all original lock inodes and receipts untouched.
        retireHostStages();
        await absent(true);
        if (
          pendingFinal ||
          ((mode === 'finalize' || mode === 'finish') && !record.final_fence)
        )
          finalizeFence();
        process.stdout.write(
          JSON.stringify(
            mode === 'finish'
              ? completion()
              : {
                  operation: id,
                  removal: removal,
                  lease: record.final_fence || record.lease,
                  state: 'verified-clean'
                }
          )
        );
      } else {
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
        await absent(false);
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
          retire(entry.path, null, entry, true, true);
        });
        await absent(true);
        record.result.private_cleanup_verified = true;
        record.result.verified_clean = true;
        cleanup.files = {};
        delete cleanup.parent_pid;
        finalizeFence();
        process.stdout.write(JSON.stringify(completion()));
      }
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
})();
