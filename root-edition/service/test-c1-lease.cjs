'use strict';
var assert = require('assert'),
  crypto = require('crypto'),
  fs = require('fs');
var install = fs.existsSync(__dirname + '/c1-lease.js')
  ? require('./c1-lease')
  : null;
assert.strictEqual(
  typeof install,
  'function',
  'C1 broker must register the private method'
);
var ROOT = '/var/lib/clean-your-tv-root',
  binary = Buffer.from('native helper fixture');
function fixture(uid, initialChange, diskDirectory) {
  var callbacks = [],
    timers = [],
    cancel,
    handler,
    homeHandler,
    clock = 0,
    calls = [],
    files = {},
    metadata = {},
    replies = [];
  var admission = {
    model: 'OLED55C1PUB',
    firmware: '03.50.10',
    webos: '6.4.0',
    target_sha256: 'b'.repeat(64),
    target: { dev: 1, ino: 2, size: 52, mtime_ns: 123 }
  };
  var marker = {
    schema: 2,
    backend: 'c1-native-gate',
    experimental: true,
    routing: 'compositor-keyfilter-v1',
    native_sha256: crypto.createHash('sha256').update(binary).digest('hex'),
    admission: admission
  };
  files[ROOT + '/home-backend.json'] = Buffer.from(JSON.stringify(marker));
  files[ROOT + '/runtime/c1-keyfilter-guard'] = binary;
  function stat(path) {
    if (metadata[path] instanceof Error) throw metadata[path];
    var isfile = !!files[path];
    return Object.assign(
      {
        uid: 0,
        mode: isfile ? (path.endsWith('.json') ? 0o600 : 0o700) : 0o700,
        nlink: 1,
        size: isfile ? files[path].length : 0,
        ino: 1,
        dev: 1,
        isDirectory: function () {
          return !isfile;
        },
        isFile: function () {
          return isfile;
        }
      },
      metadata[path] || {}
    );
  }
  var realFds = {},
    fileIndex = 0,
    positions = {};
  var fakefs = {
    constants: require('fs').constants,
    lstatSync: stat,
    openSync: function (p, flags) {
      if (!files[p]) throw Error('missing');
      positions[p] = 0;
      if (diskDirectory) {
        var file = diskDirectory + '/lease-' + ++fileIndex;
        fs.writeFileSync(file, files[p]);
        var fd = fs.openSync(file, flags);
        realFds[fd] = p;
        return fd;
      }
      return p;
    },
    fstatSync: function (fd) {
      return stat(realFds[fd] || fd);
    },
    readFileSync: function (p) {
      if (typeof p === 'number') return fs.readFileSync(p);
      return files[p];
    },
    readSync: function (fd, buffer, offset, length, position) {
      if (typeof fd === 'number')
        return fs.readSync(fd, buffer, offset, length, position);
      var start = positions[fd] || 0;
      var size = files[fd].copy(
        buffer,
        offset,
        start,
        start + Math.min(length, 17)
      );
      positions[fd] = start + size;
      return size;
    },
    closeSync: function (fd) {
      if (typeof fd === 'number') fs.closeSync(fd);
    }
  };
  var opts = {
    now: function () {
      return clock;
    },
    fs: fakefs,
    getuid: function () {
      return uid === undefined ? 0 : uid;
    },
    setTimeout: function (fn, ms) {
      var t = { fn: fn, ms: ms, clear: false };
      timers.push(t);
      return t;
    },
    clearTimeout: function (t) {
      t.clear = true;
    },
    execFile: function (path, args, options, cb) {
      calls.push({ path: path, args: args, options: options });
      callbacks.push(cb);
      return { kill: function () {} };
    }
  };
  var service = { activityManager: { shared: true } },
    aliasCount = 0;
  opts.createService = function (name, manager, settings) {
    assert.strictEqual(name, 'com.webos.cleanyourtv.root.lease');
    assert.strictEqual(
      manager,
      service.activityManager,
      'alias must share primary activity manager'
    );
    assert.strictEqual(settings.noBuiltinMethods, true);
    aliasCount++;
    return {
      register: function (name, fn, onCancel) {
        assert(['c1Lease', 'c1Home'].includes(name));
        if (name === 'c1Home') {
          homeHandler = fn;
          assert.strictEqual(onCancel, undefined);
        } else {
          handler = fn;
          cancel = onCancel;
        }
      }
    };
  };
  if (initialChange) initialChange(files, metadata);
  install(service, opts);
  function message(token, caller) {
    return {
      uniqueToken: token || 'one',
      isSubscription: true,
      payload: { subscribe: true },
      ls2Message: {
        applicationID: function () {
          return '';
        },
        senderServiceName: function () {
          return caller || 'com.webos.surfacemanager';
        }
      },
      respond: function (v) {
        replies.push(v);
      }
    };
  }
  return {
    opts: opts,
    files: files,
    metadata: metadata,
    calls: calls,
    callbacks: callbacks,
    timers: timers,
    replies: replies,
    advance: function (ms) {
      clock += ms;
    },
    home: function (payload, caller, response) {
      var m = message('home', caller);
      m.isSubscription = false;
      m.payload = payload || { token: 'a'.repeat(32) };
      if (response) m.respond = response;
      homeHandler(m);
    },
    aliasCount: aliasCount,
    subscribe: function (m) {
      if (handler) handler(m || message());
    },
    message: message,
    cancel: function (m) {
      cancel(m);
    },
    tick: function (ms) {
      var t = timers.find(function (t) {
        return !t.clear && t.ms === ms;
      });
      assert(t, 'missing timer ' + ms);
      t.clear = true;
      t.fn();
    },
    reply: function (v, idx) {
      callbacks[idx === undefined ? callbacks.length - 1 : idx](
        null,
        JSON.stringify(v)
      );
    }
  };
}
function native(token) {
  return {
    returnValue: true,
    backend: 'c1-native-gate',
    routing: 'compositor-keyfilter-v1',
    state: 'armed',
    mounted: false,
    healthy: true,
    stock_verified: false,
    stopped: false,
    token: token || 'a'.repeat(32),
    guardian_pid: 99,
    reason: '',
    profiles: null
  };
}
var f = fixture();
if (process.argv[2]) {
  var disk = fixture(undefined, undefined, process.argv[2]);
  assert.strictEqual(
    disk.aliasCount,
    1,
    'real descriptor reads must establish lease authority'
  );
  disk.subscribe();
  assert.strictEqual(disk.calls.length, 1);
  disk.reply(native());
  assert.strictEqual(disk.replies.at(-1).healthy, true);
}
assert.strictEqual(f.calls.length, 0, 'module load never starts native');
f.subscribe();
assert.strictEqual(f.calls.length, 1);
assert.strictEqual(f.calls[0].args.length, 1);
assert.strictEqual(f.calls[0].args[0], '--lease');
assert.strictEqual(f.calls[0].path, ROOT + '/runtime/c1-keyfilter-guard');
assert(f.calls[0].options.timeout <= 1000);
f.reply(native());
assert.strictEqual(f.replies.at(-1).healthy, true);
assert.strictEqual(f.replies.at(-1).sequence, 1);
f.tick(400);
f.reply(native());
assert.strictEqual(f.replies.at(-1).sequence, 2);
f.cancel(f.message());
var count = f.calls.length;
f.timers
  .filter(function (t) {
    return !t.clear;
  })
  .forEach(function (t) {
    t.fn();
  });
assert.strictEqual(f.calls.length, count, 'no pulses after cancel');
f = fixture();
f.subscribe(f.message('bad', 'com.attacker'));
assert.strictEqual(f.calls.length, 0);
assert.strictEqual(f.replies.at(-1).returnValue, false);
f = fixture();
var bad = f.message();
bad.payload.command = '--restore';
f.subscribe(bad);
assert.strictEqual(f.calls.length, 0);
[
  function (f) {
    delete f.files[ROOT + '/home-backend.json'];
  },
  function (f) {
    f.files[ROOT + '/runtime/c1-keyfilter-guard'] = Buffer.from('tampered');
  },
  function (f) {
    f.metadata[ROOT + '/runtime'] = { mode: 0o777 };
  },
  function (f) {
    f.metadata[ROOT + '/home-backend.json'] = { uid: 1000 };
  },
  function (f) {
    var path = ROOT + '/home-backend.json';
    f.metadata[path] = { size: f.files[path].length - 1 };
  },
  function (f) {
    var path = ROOT + '/home-backend.json';
    f.metadata[path] = { size: f.files[path].length + 1 };
  },
  function (f) {
    f.metadata[ROOT + '/c1-keyfilter'] = { mode: 0o755 };
  },
  function (f) {
    var m = JSON.parse(f.files[ROOT + '/home-backend.json']);
    m.schema = 1;
    f.files[ROOT + '/home-backend.json'] = Buffer.from(JSON.stringify(m));
  }
].forEach(function (change) {
  var a = fixture();
  change(a);
  a.subscribe();
  assert.strictEqual(a.calls.length, 0);
  assert.strictEqual(a.replies.at(-1).healthy, false);
});
f = fixture();
f.subscribe();
f.reply(native());
f.metadata[ROOT + '/runtime/c1-keyfilter-guard'] = { uid: 1 };
f.tick(400);
assert.strictEqual(f.calls.length, 1);
assert.strictEqual(
  f.replies.at(-1).healthy,
  false,
  'lost root authority revokes'
);
f = fixture();
f.subscribe();
f.tick(350);
assert.strictEqual(f.replies.at(-1).healthy, false);
var length = f.replies.length;
f.reply(native());
assert.strictEqual(
  f.replies.length,
  length,
  'late child cannot revive timed out lease'
);
[
  Object.assign(native(), { mounted: true }),
  Object.assign(native(), { stopped: true }),
  Object.assign(native(), { guardian_pid: 0 }),
  Object.assign(native(), { routing: 'legacy' }),
  Object.assign(native(), { state: 'stopped' })
].forEach(function (value) {
  var a = fixture();
  a.subscribe();
  a.reply(value);
  assert.strictEqual(a.replies.at(-1).healthy, false);
});
f = fixture();
f.subscribe();
f.reply(native());
f.tick(400);
f.reply(native('b'.repeat(32)));
assert.strictEqual(
  f.replies.at(-1).healthy,
  false,
  'attempt changes revoke subscription'
);
f = fixture();
f.subscribe();
f.cancel(f.message());
f.subscribe(f.message('two'));
f.reply(native(), 0);
assert.strictEqual(
  f.replies.length,
  0,
  'old child cannot publish into new subscriber generation'
);
f.reply(native(), 1);
assert.strictEqual(f.replies.at(-1).healthy, true);
f = fixture();
f.subscribe();
f.reply(
  Object.assign(native(), {
    state: 'stock',
    healthy: false,
    stock_verified: true,
    guardian_pid: 0
  })
);
assert.strictEqual(f.replies.at(-1).returnValue, true);
assert.strictEqual(f.replies.at(-1).healthy, false);
f.tick(400);
f.reply(native());
assert.strictEqual(
  f.replies.at(-1).healthy,
  true,
  'pending bootstrap must reach ready'
);
f.tick(400);
f.reply(
  Object.assign(native(), {
    state: 'stock',
    healthy: false,
    stock_verified: true,
    guardian_pid: 0
  })
);
assert.strictEqual(
  f.replies.at(-1).returnValue,
  false,
  'postarmed readiness loss ends stream'
);
f = fixture(1000);
f.subscribe();
assert.strictEqual(f.calls.length, 0, 'nonroot cannot start lease');
f = fixture();
f.subscribe();
f.subscribe(f.message('two'));
f.subscribe(f.message('three'));
assert.strictEqual(
  f.replies.at(-1).returnValue,
  false,
  'subscriber count bounded'
);
f.cancel(f.message());
f.reply(native());
assert.strictEqual(
  f.replies.at(-1).healthy,
  true,
  'remaining subscriber retains live pulse'
);
f.cancel(f.message('two'));
var pending = f.timers.filter(function (t) {
  return !t.clear;
});
assert.strictEqual(pending.length, 0);
f = fixture();
var broken = f.message();
broken.respond = function () {
  throw Error('subscriber gone');
};
f.subscribe(broken);
f.reply(native());
assert.strictEqual(
  f.timers.filter(function (t) {
    return !t.clear;
  }).length,
  0,
  'failed delivery stops pulses'
);
f = fixture();
f.subscribe();
f.reply(Object.assign(native(), { unexpected: true }));
assert.strictEqual(
  f.replies.at(-1).healthy,
  false,
  'unknown native fields rejected'
);
f = fixture();
var silent = f.message();
silent.respond = function () {
  return false;
};
f.subscribe(silent);
f.reply(native());
assert.strictEqual(
  f.timers.filter(function (t) {
    return !t.clear;
  }).length,
  0,
  'LS2 respond false must stop pulses'
);
[null, undefined, 'com.webos.surfacemanager'].forEach(function (applicationID) {
  var a = fixture();
  var nativeMessage = a.message();
  nativeMessage.ls2Message.applicationID = function () {
    return applicationID;
  };
  a.subscribe(nativeMessage);
  assert.strictEqual(
    a.calls.length,
    1,
    'authenticated senderServiceName is authoritative regardless of applicationID'
  );
});
assert.strictEqual(
  fixture(1000).aliasCount,
  0,
  'nonroot service does not register alias'
);
assert.strictEqual(
  fixture(undefined, function (files) {
    delete files[ROOT + '/home-backend.json'];
  }).aliasCount,
  0,
  'normal Root does not register alias'
);
f = fixture();
f.subscribe();
f.advance(351);
f.reply(native());
assert.strictEqual(
  f.replies.at(-1).healthy,
  false,
  'elapsed deadline rejects late callback before timer dispatch'
);
f = fixture();
f.subscribe();
f.reply(native());
f.home();
assert.strictEqual(f.calls.at(-1).args.length, 2);
assert.strictEqual(f.calls.at(-1).args[0], '--home');
assert.strictEqual(f.calls.at(-1).args[1], 'a'.repeat(32));
assert(f.calls.at(-1).options.timeout >= 2300);
var beforeHome = f.calls.length;
f.tick(400);
assert.strictEqual(
  f.calls.length,
  beforeHome + 1,
  'lease polls continue during independent Home barrier'
);
f.reply(native(), 1);
assert.strictEqual(f.replies.at(-1).returnValue, true);
assert.strictEqual(f.replies.at(-1).token, 'a'.repeat(32));
f = fixture();
f.subscribe();
f.reply(native());
f.home({ token: 'a'.repeat(32), command: '--restore' });
assert.strictEqual(f.calls.length, 1, 'home has no arbitrary args');
f.home(undefined, 'com.attacker');
assert.strictEqual(f.calls.length, 1);
f.home({ token: 'b'.repeat(32) });
assert.strictEqual(f.calls.length, 1, 'token must match current stream');
f = fixture();
f.subscribe();
f.reply(native());
f.home();
f.callbacks.at(-1)(
  null,
  JSON.stringify(
    Object.assign(native(), {
      returnValue: false,
      healthy: false,
      stopped: true,
      state: 'stopped'
    })
  )
);
assert.strictEqual(
  f.replies.at(-1).returnValue,
  false,
  'native stopped Home failure reaches Qt'
);
assert.strictEqual(
  f.timers.filter(function (t) {
    return !t.clear;
  }).length,
  0,
  'failed Home revokes leases'
);
f = fixture();
f.subscribe();
f.reply(native());
f.home();
f.tick(2500);
assert.strictEqual(f.replies.at(-1).returnValue, false);
var afterTimeout = f.replies.length;
f.reply(native(), 1);
assert.strictEqual(
  f.replies.length,
  afterTimeout,
  'late Home cannot complete retired request'
);
f = fixture();
f.subscribe();
f.reply(native());
f.home();
f.advance(2501);
f.reply(native(), 1);
assert.strictEqual(
  f.replies.at(-1).returnValue,
  false,
  'monotonic deadline rejects late Home callback before timer'
);
f = fixture();
f.subscribe();
f.reply(native());
f.home(undefined, undefined, function () {
  return false;
});
f.reply(native());
assert.strictEqual(
  f.replies.at(-1).healthy,
  false,
  'lost Home response revokes routing'
);
assert.strictEqual(
  f.timers.filter(function (t) {
    return !t.clear;
  }).length,
  0
);
var registered = {},
  serviceManagers = [];
require('vm').runInNewContext(
  fs.readFileSync(__dirname + '/service.js', 'utf8'),
  {
    process: process,
    __dirname: __dirname,
    require: function (name) {
      if (name === 'webos-service')
        return function () {
          this.activityManager = {};
          this.register = function (n, f) {
            registered[n] = f;
          };
        };
      if (name === './c1-lease')
        return function (main, options) {
          assert.strictEqual(typeof options.createService, 'function');
          options.createService(
            'com.webos.cleanyourtv.root.lease',
            main.activityManager,
            { noBuiltinMethods: true }
          );
          serviceManagers.push(main.activityManager);
        };
      if (name === './handlers') {
        var h = function () {
          return {};
        };
        h.audio = function () {};
        return h;
      }
      return require(name);
    }
  }
);
assert.strictEqual(
  registered.c1Lease,
  undefined,
  'main service must not expose lease method'
);
assert.strictEqual(
  serviceManagers.length,
  1,
  'real service supplies alias factory independently of recovery handlers'
);
function schema3(files, model, sdk) {
  var m = JSON.parse(files[ROOT + '/home-backend.json']);
  m.schema = 3;
  m.admission.model = model;
  m.admission.webos = sdk;
  m.admission.firmware = '23.25.55';
  files[ROOT + '/home-backend.json'] = Buffer.from(JSON.stringify(m));
}
['55NANO77SRA', 'OLED55C37LA', '55UP7000PUA', '60UJ6050-UA'].forEach(
  function (model) {
    var a = fixture(undefined, function (files) {
      schema3(files, model, '9.2.2');
    });
    a.subscribe();
    assert.strictEqual(a.calls.length, 1, 'schema3 is model-independent');
    a.reply(native());
    assert.strictEqual(a.replies.at(-1).healthy, true);
  }
);
['3.9.0', '4.4.3', '5.6.2', '10.3.1', '12.0.0'].forEach(function (sdk) {
  var a = fixture(undefined, function (files) {
    schema3(files, 'capability-admitted', sdk);
  });
  a.subscribe();
  assert.strictEqual(
    a.calls.length,
    1,
    'recorded SDK must not substitute for capability admission'
  );
  a.reply(native());
  assert.strictEqual(a.replies.at(-1).healthy, true);
});
var unsupported = fixture(undefined, function (files) {
  schema3(files, '55NANO77SRA', 'invalid');
});
assert.strictEqual(
  unsupported.aliasCount,
  0,
  'malformed observation is not admitted'
);
var disguised = fixture(undefined, function (files) {
  schema3(files, '55NANO77SRA', '9.2.2');
  var m = JSON.parse(files[ROOT + '/home-backend.json']);
  m.schema = 2;
  files[ROOT + '/home-backend.json'] = Buffer.from(JSON.stringify(m));
});
assert.strictEqual(
  disguised.aliasCount,
  0,
  'schema2 retains C1-only admission'
);
console.log('C1 and experimental compositor lease broker tests passed');
