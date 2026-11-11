// Real controller/policies with virtual time; only TV hardware, filesystem and Luna are substituted.
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm'),
  E = require('node:events'),
  path = require('node:path');
const source = path.resolve(process.env.HELPER_CONTROLLER_ROOT || 'native/app');
const dir =
  '/media/developer/apps/usr/palm/applications/com.local.nativehome/state/';
function controller({
  blocked = false,
  watchdog = false,
  automatic = true,
  setupGeneration,
  homeInitiallyOff = false,
  deferStart = false,
  inputQuery,
  luna,
  foreground
} = {}) {
  let now = 1000,
    seq = 0,
    watch,
    exit,
    stopReads = 0;
  const timers = new Map(),
    files = new Map(),
    workers = [],
    cleanups = [],
    logs = [],
    launches = [];
  if (blocked) files.set(dir + 'blocked', 'stopped');
  if (watchdog) files.set(dir + 'watchdog', 'stopped');
  if (setupGeneration) files.set(dir + 'stop-generation', setupGeneration);
  if (homeInitiallyOff)
    files.set(dir + 'home-control.json', '{"enabled":false}');
  const schedule = (fn, ms, repeat = 0) => {
    const id = ++seq;
    timers.set(id, { fn, at: now + ms, repeat });
    return id;
  };
  function advance(ms) {
    const end = now + ms;
    while (true) {
      let next;
      for (const x of timers)
        if (x[1].at <= end && (!next || x[1].at < next[1].at)) next = x;
      if (!next) break;
      const [id, t] = next;
      now = t.at;
      if (t.repeat) t.at += t.repeat;
      else timers.delete(id);
      t.fn();
    }
    now = end;
  }
  const fakefs = {
    existsSync: (p) => files.has(p),
    writeFileSync: (p, s) => files.set(p, s),
    unlinkSync: (p) => files.delete(p),
    chmodSync() {},
    renameSync: (a, b) => {
      files.set(b, files.get(a));
      files.delete(a);
    },
    appendFileSync: (p, s) => logs.push(JSON.parse(s)),
    readFileSync(p) {
      if (p === dir + 'control.json') stopReads++;
      if (files.has(p)) return files.get(p);
      throw Object.assign(Error('absent'), { code: 'ENOENT' });
    }
  };
  function Service() {
    this.activityManager = { create() {} };
    this.call = (uri, p, cb) => {
      if (uri.endsWith('/launch')) launches.push(p.id);
      if (luna && luna(uri, p, cb)) return;
      cb({
        payload: { returnValue: true, state: { enabled: true, schema: 3 } }
      });
    };
  }
  const cp = {
    spawn(file, args) {
      assert(file.endsWith('/relay'));
      const c = new E();
      c.stdout = new E();
      c.stderr = new E();
      c.stdin = new E();
      c.writes = [];
      c.kills = [];
      c.ack = true;
      c.args = args;
      c.stdin.write = (b) => {
        c.writes.push(b);
        if (b === 'P' && c.ack) c.stdout.emit('data', Buffer.from('P\n'));
      };
      c.stdin.end = () => {};
      c.kill = (s) => {
        c.kills.push(s);
        return true;
      };
      (args[0] === 'cleanup' ? cleanups : workers).push(c);
      return c;
    }
  };
  const context = {
    Buffer,
    console,
    Date: { now: () => now },
    require(n) {
      if (n === 'fs') return fakefs;
      if (n === 'child_process') return cp;
      if (n === '/usr/lib/node_modules/webos-service') return Service;
      if (n === './home-control')
        return require('./storage-fixture.cjs').homeControl(fakefs);
      if (n === './state-permissions')
        return require('./storage-fixture.cjs').create(fakefs, (d, l, init) => {
          if (init) files.set(dir + 'control.json', '{}');
          return true;
        });
      if (n === './app-inventory')
        return (
          inputQuery ||
          (() => {
            throw Error('unexpected inventory query');
          })
        );
      if (n === './screen-watch')
        return (d, l, fg, reset, power) => {
          watch = { fg, reset, power };
          return {
            close: reset,
            foreground:
              foreground ||
              function (done) {
                done(null);
              }
          };
        };
      return require(path.join(source, n));
    },
    process: {
      argv: [
        'node',
        'native.js',
        JSON.stringify({
          nativeHomeAuto: automatic,
          nativeHomeSetup: setupGeneration
        })
      ],
      pid: 1,
      getuid: () => 5431,
      hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1e6],
      on() {},
      exit(c) {
        exit = c;
      }
    },
    setTimeout: (f, ms) => schedule(f, ms),
    clearTimeout: (id) => timers.delete(id),
    setInterval: (f, ms) => schedule(f, ms, ms),
    clearInterval: (id) => timers.delete(id)
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(source, 'native.js'), 'utf8'),
    context
  );
  if (exit === undefined && !deferStart) {
    advance(automatic && !setupGeneration ? 0 : 1000);
    workers[0].stdout.emit('data', Buffer.from('READY\n'));
  }
  function close(
    code = 20,
    signal = null,
    worker = workers.at(-1),
    reason = code
  ) {
    if (reason !== null)
      worker.stdout.emit('data', Buffer.from('EXIT ' + reason + '\n'));
    if (code === 20) files.set(dir + 'watchdog', 'stopped');
    worker.emit('exit', code, signal);
    worker.emit('close', code, signal);
  }
  function command(cmd) {
    files.set(dir + 'control.json', JSON.stringify({ cmd }));
  }
  function cleanup(code = 0, signal = null) {
    const c = cleanups.at(-1);
    assert(c, 'cleanup must precede recovery');
    c.emit('exit', code, signal);
    c.emit('close', code, signal);
  }
  return {
    advance,
    files,
    workers,
    cleanups,
    logs,
    launches,
    close,
    cleanup,
    command,
    foreground: (id) => watch.fg(id),
    reset: () => watch.reset(),
    power: (p) => watch.power(p),
    get exit() {
      return exit;
    },
    get stopReads() {
      return stopReads;
    }
  };
}
const blocked = (c) => c.files.has(dir + 'blocked');
test('setup enables Home and preserves its bound generation across a guarded relay retry', () => {
  const token = 'I' + '1'.repeat(32);
  const c = controller({ setupGeneration: token, homeInitiallyOff: true });
  assert.equal(
    JSON.parse(c.files.get(dir + 'home-control.json')).enabled,
    true
  );
  assert.deepEqual(Array.from(c.workers[0].args), ['setup', token]);
  c.close(20); // The real C relay writes only a transient watchdog fence.
  c.cleanup();
  c.advance(1500);
  assert.equal(c.workers.length, 2);
  c.workers[1].stdout.emit('data', Buffer.from('READY\n'));
  assert.equal(c.files.get(dir + 'stop-generation'), token);
  assert(c.workers[1].writes.includes('E'));
  const cancelled = 'S' + '2'.repeat(32);
  c.files.set(dir + 'stop-generation', cancelled);
  const launches = c.launches.length;
  c.workers[1].stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(
    c.launches.length,
    launches,
    'changed generation must fence post-READY Home'
  );
  c.advance(400);
  assert(c.workers[1].writes.includes('Q'));
  c.close(29);
  c.cleanup();
  assert.equal(c.files.get(dir + 'stop-generation'), cancelled);
  assert(blocked(c));
});
test('setup generation survives confirmed power-removal wake without becoming a Stop', () => {
  const token = 'I' + '3'.repeat(32),
    c = controller({ setupGeneration: token });
  c.power({ state: 'Prepare Power Off' });
  c.close(32);
  c.power({ state: 'Active', processing: false, onOff: 'on' });
  c.advance(1500);
  assert.equal(c.workers.length, 2);
  c.workers[1].stdout.emit('data', Buffer.from('READY\n'));
  assert.equal(c.files.get(dir + 'stop-generation'), token);
  assert(!blocked(c));
});
test('setup generation survives controller-owned watchdog SIGKILL and bounded retry', () => {
  const token = 'I' + '4'.repeat(32),
    c = controller({ setupGeneration: token });
  const w = c.workers[0];
  w.ack = false;
  c.advance(2800);
  assert.deepEqual(w.kills, ['SIGKILL']);
  assert.equal(c.files.get(dir + 'stop-generation'), token);
  c.close(null, 'SIGKILL', w, null);
  c.cleanup();
  c.advance(1500);
  assert.equal(c.workers.length, 2);
  c.workers[1].stdout.emit('data', Buffer.from('READY\n'));
  assert.equal(c.files.get(dir + 'stop-generation'), token);
  assert(!blocked(c));
});
test('setup retry exhaustion publishes a permanent Stop instead of reusing its generation', () => {
  const token = 'I' + '5'.repeat(32),
    c = controller({ setupGeneration: token });
  for (let i = 0; i < 5; i++) {
    c.close(20);
    c.cleanup();
    c.advance(1500);
    c.workers.at(-1).stdout.emit('data', Buffer.from('READY\n'));
    assert.equal(c.files.get(dir + 'stop-generation'), token);
  }
  c.close(20);
  c.cleanup();
  c.advance(3000);
  assert.equal(c.workers.length, 6);
  assert.match(c.files.get(dir + 'stop-generation'), /^S[a-f0-9]{32}$/);
  assert.notEqual(c.files.get(dir + 'stop-generation'), token);
  assert(blocked(c));
});
test('single CARD emergency returns to LG after cleanup without requiring cross-app close', () => {
  let closes = 0;
  const c = controller({
    luna: (uri, p, cb) => {
      if (uri.endsWith('/closeByAppId')) {
        closes++;
        cb({ payload: { returnValue: false } });
        return true;
      }
    }
  });
  c.close(27);
  assert(
    !c.launches.includes('com.webos.app.home'),
    'relay cleanup must precede LG'
  );
  c.cleanup();
  assert.equal(
    c.launches.at(-1),
    'com.webos.app.home',
    'cross-app close permission is not required to background a CARD'
  );
  assert.equal(closes, 0);
  assert(blocked(c));
  c.advance(300);
  assert.equal(c.exit, 27);
  assert(
    c.logs.some(
      (x) =>
        x.event === 'terminal-ui-requested' &&
        x.homeClosed === false &&
        x.lgLaunchAccepted === true
    )
  );
});
test('ordinary CARD Home does not wait for overlay foreground context', () => {
  let queries = 0;
  const c = controller({ foreground: () => queries++ }),
    before = c.launches.length;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(
    queries,
    0,
    'CARD presentation does not depend on SSAP underlay context'
  );
  assert.equal(c.launches.length, before + 1);
  assert.equal(c.launches.at(-1), 'com.gathin.tvhome');
});
test('ordinary CARD context changes and emergency background it without cross-app close', () => {
  let closes = 0;
  const c = controller({
    luna: (uri) => {
      if (uri.endsWith('/closeByAppId')) closes++;
    }
  });
  c.foreground('com.gathin.tvhome');
  c.foreground('com.webos.app.hdmi3');
  c.reset();
  c.power({ onOff: 'off', state: 'Suspend' });
  assert.equal(
    closes,
    0,
    'the platform owns CARD background/standby visibility'
  );
  c.close(27);
  c.cleanup();
  assert.equal(
    closes,
    0,
    'emergency normally activates LG without killing the CARD'
  );
  c.advance(300);
  assert.equal(c.exit, 27);
});
test('emergency waits for relay cleanup and LG acknowledgement before exiting', () => {
  let lg;
  const c = controller({
    luna: (uri, p, cb) => {
      if (uri.endsWith('/launch') && p.id === 'com.webos.app.home') {
        lg = cb;
        return true;
      }
    }
  });
  c.close(27);
  assert(
    !c.launches.includes('com.webos.app.home'),
    'LG must wait for input cleanup'
  );
  c.cleanup();
  assert(blocked(c));
  assert.equal(c.exit, undefined, 'pending LG request must settle');
  lg({ payload: { returnValue: true } });
  assert.equal(c.launches.at(-1), 'com.webos.app.home');
  c.advance(300);
  assert.equal(c.exit, 27);
  assert.equal(c.workers.length, 1);
});
test('terminal EXIT fences buffered Home before worker close', () => {
  const c = controller(),
    w = c.workers[0],
    before = c.launches.length;
  w.stdout.emit('data', Buffer.from('EXIT 27\nHOME\nREADY\n'));
  w.stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(
    c.launches.length,
    before,
    'terminal relay output cannot launch another owned Home'
  );
});
test('terminal EXIT fences a legacy presentation RPC reply arriving before worker close', () => {
  let reply;
  const c = controller({ foreground: (done) => (reply = done) }),
    w = c.workers[0];
  const channel =
    '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/';
  c.files.set(
    channel + 'home-request.json',
    JSON.stringify({
      id: 'a'.repeat(32),
      expires: 6000,
      method: 'presentationContext'
    })
  );
  c.advance(400);
  const count = c.launches.length;
  w.stdout.emit('data', Buffer.from('EXIT 27\n'));
  reply('com.webos.app.hdmi3');
  assert.equal(
    c.launches.length,
    count,
    'a legacy context query cannot launch after terminal EXIT'
  );
  assert(
    !c.files.has(channel + 'home-response.json'),
    'terminal context reply cannot escape'
  );
});
test('late CARD launch acknowledgement after a foreground change does not close Home', () => {
  let held,
    hold = false,
    closes = 0;
  const c = controller({
    luna: (uri, p, cb) => {
      if (hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
        held = cb;
        return true;
      }
      if (uri.endsWith('/closeByAppId')) closes++;
    }
  });
  hold = true;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  c.foreground('com.gathin.tvhome');
  c.foreground('com.webos.app.hdmi3');
  held({ payload: { returnValue: true } });
  assert.equal(closes, 0);
  assert.equal(c.exit, undefined);
});
test('emergency drains an in-flight Home launch before normally activating LG', () => {
  let held,
    hold = false;
  const calls = [];
  const c = controller({
    luna: (uri, p, cb) => {
      if (uri.endsWith('/launch')) calls.push(p.id);
      if (uri.endsWith('/closeByAppId')) calls.push('close');
      if (hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
        held = cb;
        return true;
      }
    }
  });
  hold = true;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  c.close(27);
  c.cleanup();
  assert.equal(c.exit, undefined);
  assert(!c.launches.includes('com.webos.app.home'));
  held({ payload: { returnValue: true } });
  c.advance(50);
  assert.equal(calls.at(-1), 'com.webos.app.home');
  assert(!calls.includes('close'));
  c.advance(300);
  assert.equal(c.exit, 27);
});
test('Stop drains an initial Home launch before any relay exists', () => {
  let held;
  const order = [];
  const c = controller({
    deferStart: true,
    luna: (uri, p, cb) => {
      if (uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
        held = cb;
        return true;
      }
      if (uri.endsWith('/closeByAppId')) order.push('close');
      if (uri.endsWith('/launch') && p.id === 'com.webos.app.home')
        order.push('LG');
    }
  });
  c.advance(0);
  c.command('stop');
  c.advance(400);
  assert.equal(c.exit, undefined);
  assert.deepEqual(order, [], 'close/LG must not race initial launch');
  held({ payload: { returnValue: true } });
  c.advance(50);
  assert.deepEqual(order, ['LG']);
  c.advance(300);
  assert.equal(c.exit, 0);
  assert.equal(c.workers.length, 0);
  assert(blocked(c));
});
for (const reply of [false, null, 'timeout'])
  test('CARD emergency never depends on cross-app close ' + reply, () => {
    let closes = 0;
    const c = controller({
      luna: (uri, p, cb) => {
        if (uri.endsWith('/closeByAppId')) {
          closes++;
          if (reply !== 'timeout')
            cb({ payload: reply === null ? {} : { returnValue: reply } });
          return true;
        }
      }
    });
    c.close(27);
    c.cleanup();
    c.advance(10000);
    assert.equal(c.exit, 27);
    assert(blocked(c));
    assert.equal(closes, 0);
    assert(!c.logs.some((x) => x.event === 'terminal-ui-failed'));
    assert(c.launches.includes('com.webos.app.home'));
    assert(
      c.logs.some(
        (x) => x.event === 'terminal-ui-requested' && x.homeClosed === false
      )
    );
  });
test('timed-out Home launch cannot race a final LG launch or replay after a late reply', () => {
  let late,
    hold = false;
  const c = controller({
    luna: (uri, p, cb) => {
      if (hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
        late = cb;
        return true;
      }
    }
  });
  hold = true;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  c.close(27);
  c.cleanup();
  c.advance(10000);
  assert.equal(c.exit, 27);
  assert(!c.launches.includes('com.webos.app.home'));
  const count = c.launches.length;
  late({ payload: { returnValue: true } });
  c.advance(1000);
  assert.equal(c.launches.length, count);
  assert(c.logs.some((x) => x.event === 'terminal-ui-failed'));
  assert(blocked(c));
});
test('a later accepted Home launch does not erase an older unresolved SAM request', () => {
  let hold = false,
    late;
  const c = controller({
    luna: (uri, p, cb) => {
      if (hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
        hold = false;
        late = cb;
        return true;
      }
    }
  });
  hold = true;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  c.advance(3000);
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  c.close(27);
  c.cleanup();
  c.advance(10000);
  assert.equal(c.exit, 27);
  assert(
    !c.launches.includes('com.webos.app.home'),
    'an earlier unknown SAM outcome remains a terminal race'
  );
  const count = c.launches.length;
  late({ payload: { returnValue: true } });
  assert.equal(c.launches.length, count);
  assert(blocked(c));
});
test('explicit Stop waits for LG acknowledgement with the latch retained', () => {
  let lg;
  const c = controller({
    luna: (uri, p, cb) => {
      if (uri.endsWith('/launch') && p.id === 'com.webos.app.home') {
        lg = cb;
        return true;
      }
    }
  });
  c.command('stop');
  c.advance(400);
  c.close(0);
  c.cleanup();
  assert.equal(c.exit, undefined);
  assert(blocked(c));
  lg({ payload: { returnValue: true } });
  c.advance(300);
  assert.equal(c.exit, 0);
  assert.equal(c.launches.at(-1), 'com.webos.app.home');
});
test('relay Stop code 22 cleans input then backgrounds CARD via normal LG activation', () => {
  let closes = 0;
  const c = controller({
    luna: (uri) => {
      if (uri.endsWith('/closeByAppId')) closes++;
    }
  });
  c.close(22);
  assert(!c.launches.includes('com.webos.app.home'));
  c.cleanup();
  c.advance(300);
  assert.equal(c.exit, 0);
  assert(blocked(c));
  assert.equal(closes, 0);
  assert.equal(c.launches.at(-1), 'com.webos.app.home');
});
for (const reply of [false, null, 'timeout'])
  test(
    'terminal LG launch ' +
      reply +
      ' is bounded without claiming accepted restoration',
    () => {
      const c = controller({
        luna: (uri, p, cb) => {
          if (uri.endsWith('/launch') && p.id === 'com.webos.app.home') {
            if (reply !== 'timeout')
              cb({ payload: reply === null ? {} : { returnValue: reply } });
            return true;
          }
        }
      });
      c.close(27);
      c.cleanup();
      c.advance(10000);
      assert.equal(c.exit, 27);
      assert(blocked(c));
      assert(c.logs.some((x) => x.event === 'terminal-ui-failed'));
      assert(!c.logs.some((x) => x.event === 'terminal-ui-requested'));
    }
  );
test('cleanup failure during emergency never restarts input and remains recorded', () => {
  const c = controller();
  c.close(27);
  c.cleanup(11);
  c.advance(10000);
  assert.equal(c.exit, 27);
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
  assert(c.logs.some((x) => x.event === 'cleanup' && x.code === 11));
  assert(!c.launches.includes('com.webos.app.home'));
  assert(!c.logs.some((x) => x.event === 'terminal-ui-requested'));
  assert(
    c.logs.some(
      (x) =>
        x.event === 'terminal-ui-failed' && x.reason === 'input-cleanup-failed'
    )
  );
});
test('watchdog timeout cleans input, waits, restarts and routes Home without clearing an emergency latch', () => {
  const c = controller(),
    old = c.workers[0];
  c.power({ state: 'Suspend' });
  c.close();
  assert.equal(c.exit, undefined);
  assert(!blocked(c));
  assert.equal(c.workers.length, 1);
  c.advance(2000);
  assert.equal(c.workers.length, 1, 'wait for cleanup');
  c.cleanup();
  c.advance(1499);
  assert.equal(c.workers.length, 1);
  c.advance(1);
  assert.equal(c.workers.length, 2);
  assert(c.files.has(dir + 'watchdog'), 'latch stays until READY');
  const w = c.workers[1];
  w.stdout.emit('data', Buffer.from('READY\n'));
  assert(!c.files.has(dir + 'watchdog'));
  assert(w.writes.includes('E'));
  const n = c.launches.length;
  old.stdout.emit('data', Buffer.from('HOME\n'));
  old.emit('close', 20, null);
  assert.equal(c.launches.length, n, 'late events from old relay ignored');
  w.stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(c.launches.at(-1), 'com.gathin.tvhome');
});
test('Stop during cleanup cancels recovery and latches stop', () => {
  const c = controller();
  c.close();
  c.command('stop');
  c.advance(400);
  c.cleanup();
  c.advance(3000);
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
  assert.notEqual(c.exit, undefined);
});
test('Stop just before retry is read before spawning, even between polling ticks', () => {
  const c = controller();
  c.close();
  c.cleanup();
  c.advance(1400);
  c.command('stop');
  c.advance(100);
  assert.equal(c.workers.length, 1);
  assert(blocked(c));
});
test('Stop before the initial launch cancels startup', () => {
  const c = controller({ automatic: false, deferStart: true });
  c.command('stop');
  c.advance(3000);
  assert.equal(c.workers.length, 0);
  assert(blocked(c));
});
test('only five watchdog recoveries are allowed per ten minutes', () => {
  const c = controller();
  for (let i = 0; i < 5; i++) {
    c.close();
    c.cleanup();
    c.advance(1500);
    c.workers.at(-1).stdout.emit('data', Buffer.from('READY\n'));
  }
  c.close();
  if (c.cleanups.length > 5) c.cleanup();
  c.advance(3000);
  assert.equal(c.workers.length, 6);
  assert(blocked(c));
  assert.notEqual(c.exit, undefined);
});
test('old recoveries expire from the rolling window', () => {
  const c = controller();
  for (let i = 0; i < 5; i++) {
    c.close();
    c.cleanup();
    c.advance(1500);
    c.workers.at(-1).stdout.emit('data', Buffer.from('READY\n'));
  }
  c.advance(600000);
  c.close();
  c.cleanup();
  c.advance(1500);
  assert.equal(c.workers.length, 7);
  assert(!blocked(c));
});
test('watchdog SIGKILL is retried only after the actual child closes', () => {
  const c = controller(),
    w = c.workers[0];
  w.ack = false;
  c.advance(2800);
  assert.deepEqual(w.kills, ['SIGKILL']);
  assert(c.files.has(dir + 'watchdog'));
  w.emit('exit', null, 'SIGKILL');
  c.advance(800);
  assert.equal(c.cleanups.length, 0);
  w.emit('close', null, 'SIGKILL');
  c.cleanup();
  c.advance(1500);
  assert.equal(c.workers.length, 2);
});
for (const [code, signal] of [
  [0, null],
  [23, null],
  [24, null],
  [27, null],
  [28, null],
  [30, null],
  [31, null],
  [null, 'SIGTERM'],
  [null, 'SIGKILL']
])
  test('non-watchdog exit ' + code + '/' + signal + ' remains blocked', () => {
    const c = controller();
    c.close(code, signal);
    if (c.cleanups.length) c.cleanup();
    c.advance(3000);
    assert(blocked(c));
    assert.equal(c.workers.length, 1);
  });
test('triple Home wins a race with a watchdog kill', () => {
  const c = controller();
  c.workers[0].ack = false;
  c.advance(2800);
  c.files.set(dir + 'blocked', 'stopped');
  c.close(27);
  if (c.cleanups.length) c.cleanup();
  c.advance(3000);
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
test('a terminal EXIT 27 survives signaled close and awaits cleanup, owned launch and LG', () => {
  let owned,
    lg,
    hold = false;
  const c = controller({
      luna: (uri, p, cb) => {
        if (hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome') {
          owned = cb;
          return true;
        }
        if (uri.endsWith('/launch') && p.id === 'com.webos.app.home') {
          lg = cb;
          return true;
        }
      }
    }),
    w = c.workers[0];
  hold = true;
  w.stdout.emit('data', Buffer.from('HOME\n'));
  w.ack = false;
  w.stdout.emit('data', Buffer.from('EXIT 27\n'));
  c.advance(2800);
  assert.deepEqual(w.kills, []);
  c.close(null, 'SIGKILL', w, null);
  assert.equal(c.cleanups.length, 1, 'signal still requires relay cleanup');
  assert.equal(c.exit, undefined);
  c.cleanup();
  assert.equal(
    c.exit,
    undefined,
    'signaled exit cannot skip owned launch acknowledgement'
  );
  assert(!c.launches.includes('com.webos.app.home'));
  owned({ payload: { returnValue: true } });
  c.advance(50);
  assert.equal(c.launches.at(-1), 'com.webos.app.home');
  assert.equal(c.exit, undefined, 'LG request also must settle');
  lg({ payload: { returnValue: true } });
  c.advance(300);
  assert.equal(c.exit, 27);
  assert(
    c.logs.some(
      (x) =>
        x.event === 'worker-exit' && x.code === null && x.signal === 'SIGKILL'
    ),
    'actual OS outcome remains diagnostic evidence'
  );
  assert.equal(c.workers.length, 1);
  assert(blocked(c));
});
for (const cleanupCode of [0, 11])
  test(
    'reported emergency with signaled close and cleanup ' +
      cleanupCode +
      ' remains bounded on unknown owned launch',
    () => {
      let hold = false;
      const c = controller({
        luna: (uri, p) =>
          hold && uri.endsWith('/launch') && p.id === 'com.gathin.tvhome'
      });
      hold = true;
      c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
      c.close(null, 'SIGKILL', c.workers[0], 27);
      c.cleanup(cleanupCode);
      assert.equal(c.exit, undefined);
      c.advance(10000);
      assert.equal(c.exit, 27);
      assert(blocked(c));
      assert.equal(c.workers.length, 1);
      assert(!c.launches.includes('com.webos.app.home'));
      assert(!c.logs.some((x) => x.event === 'terminal-ui-requested'));
      assert(
        c.logs.some(
          (x) =>
            x.event === 'terminal-ui-failed' &&
            x.reason ===
              (cleanupCode ? 'input-cleanup-failed' : 'home-launch-unknown')
        )
      );
    }
  );
for (const exitCode of [0, 20, 25])
  test(
    'reported emergency retains its latch when OS exit code becomes ' +
      exitCode,
    () => {
      const c = controller();
      c.close(exitCode, null, c.workers[0], 27);
      assert(
        blocked(c),
        'reported emergency must stay blocked independently of OS code'
      );
      c.cleanup();
      c.advance(10000);
      assert.equal(c.exit, 27);
      assert.equal(c.workers.length, 1);
      assert.equal(c.launches.at(-1), 'com.webos.app.home');
    }
  );
test('Stop racing with watchdog exit cannot recover', () => {
  const c = controller();
  c.command('stop');
  c.close();
  if (c.cleanups.length) c.cleanup();
  c.advance(3000);
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
test('emergency marker during recovery is never removed', () => {
  const c = controller();
  c.close();
  c.cleanup();
  c.files.set(dir + 'blocked', 'stopped');
  c.advance(1500);
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
for (const result of ['failure', 'error', 'timeout'])
  test(
    'cleanup ' + result + ' stops and blocks instead of grabbing input again',
    () => {
      const c = controller();
      c.close();
      assert(c.cleanups.length);
      if (result === 'failure') c.cleanup(11);
      if (result === 'error') c.cleanups[0].emit('error', Error('spawn'));
      c.advance(5000);
      assert(blocked(c));
      assert.equal(c.workers.length, 1);
      assert.notEqual(c.exit, undefined);
    }
  );
for (const latch of ['blocked', 'watchdog'])
  test(
    'automatic launch respects ' + latch + '; explicit manual launch clears it',
    () => {
      const c = controller({ [latch]: true });
      assert.equal(c.workers.length, 0);
      assert.equal(c.exit, 0);
      const m = controller({ [latch]: true, automatic: false });
      assert(!m.files.has(dir + latch));
      assert.equal(m.workers.length, 1);
    }
  );
test('disabled Home remains disabled after recovery', () => {
  const c = controller();
  c.files.set(
    dir + 'home-request.json',
    JSON.stringify({
      id: 'a'.repeat(32),
      method: 'setHomeControl',
      enabled: false,
      expires: 6000
    })
  );
  c.advance(400);
  c.close();
  c.cleanup();
  c.advance(1500);
  const w = c.workers.at(-1);
  w.stdout.emit('data', Buffer.from('READY\n'));
  assert(w.writes.includes('D'));
  const n = c.launches.length;
  w.stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(c.launches.length, n);
});
for (const phase of ['kill', 'exit'])
  test(
    'buffered READY/Home after ' +
      phase +
      ' cannot clear orphan latch or route Home',
    () => {
      const c = controller();
      c.close();
      c.cleanup();
      c.advance(1500);
      const w = c.workers.at(-1);
      w.ack = false;
      if (phase === 'kill') c.advance(3200);
      else w.emit('exit', 20, null);
      const n = c.launches.length;
      w.stdout.emit('data', Buffer.from('READY\nHOME\n'));
      assert(c.files.has(dir + 'watchdog'));
      assert.equal(c.launches.length, n);
      if (phase === 'exit') {
        c.advance(2800);
        assert.deepEqual(w.kills, [], 'exited child is never killed');
      }
    }
  );
test('Stop after killing a relay before READY still releases its potentially held keys', () => {
  const c = controller();
  c.close();
  c.cleanup();
  c.advance(1500);
  const w = c.workers.at(-1);
  w.ack = false;
  c.advance(3200);
  c.command('stop');
  c.close(null, 'SIGKILL', w, null);
  assert.equal(
    c.cleanups.length,
    2,
    'forced exit always needs cleanup, even without READY'
  );
  assert.equal(c.exit, undefined);
  c.cleanup();
  assert(blocked(c));
  assert.equal(c.workers.length, 2);
  assert.equal(c.launches.at(-1), 'com.webos.app.home');
  assert.equal(c.exit, undefined, 'accepted LG launch settles before exit');
  c.advance(300);
  assert.notEqual(c.exit, undefined);
});
test('exhausted retries still clean a killed replacement before READY', () => {
  const c = controller();
  for (let i = 0; i < 5; i++) {
    c.close();
    c.cleanup();
    c.advance(1500);
    if (i < 4) c.workers.at(-1).stdout.emit('data', Buffer.from('READY\n'));
  }
  const w = c.workers.at(-1);
  w.ack = false;
  c.advance(3200);
  assert.deepEqual(w.kills, ['SIGKILL']);
  c.close(null, 'SIGKILL', w, null);
  assert.equal(c.cleanups.length, 6);
  assert.equal(c.exit, undefined);
  c.cleanup();
  assert.equal(c.exit, 20);
  assert(blocked(c));
  assert.equal(c.workers.length, 6);
});

test('paired metadata channel coalesces reads, leaves Home independent and ignores replies after Stop', async () => {
  let resolve,
    reads = 0;
  const c = controller({
    inputQuery: (options) => {
      reads++;
      assert.deepEqual(JSON.parse(JSON.stringify(options)), {
        inputs: true,
        timeout: 3000
      });
      return new Promise((r) => (resolve = r));
    }
  });
  const own =
    '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/';
  const request = (id, method = 'inputStatus') =>
    c.files.set(
      own + 'input-request.json',
      JSON.stringify({ id: id.repeat(32), method, expires: 6000 })
    );
  request('a');
  c.advance(400);
  await new Promise((r) => setImmediate(r));
  request('b');
  c.advance(400);
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 1, 'concurrent read requests share one paired socket');
  c.files.set(
    own + 'home-request.json',
    JSON.stringify({ id: 'd'.repeat(32), method: 'homeStatus', expires: 6000 })
  );
  c.advance(400);
  assert.equal(
    JSON.parse(c.files.get(own + 'home-response.json')).enabled,
    true,
    'Home settings must work while metadata is pending'
  );
  const n = c.launches.length;
  c.workers[0].stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(c.launches.length, n + 1, 'metadata cannot block physical Home');
  resolve([{ appId: 'com.webos.app.hdmi3', connected: true }]);
  await new Promise((r) => setImmediate(r));
  assert.equal(
    JSON.parse(c.files.get(own + 'input-response.json')).devices[0].connected,
    true
  );
  assert.equal(
    JSON.parse(c.files.get(own + 'input-response.json')).id,
    'b'.repeat(32)
  );
  request('e', 'setHomeControl');
  c.advance(400);
  assert.equal(reads, 1, 'metadata channel cannot mutate Home');
  request('c');
  c.advance(400);
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 2, 'responses are not cached');
  const previous = c.files.get(own + 'input-response.json');
  c.command('stop');
  c.advance(400);
  assert(blocked(c));
  resolve([{ appId: 'com.webos.app.hdmi3', connected: false }]);
  await new Promise((r) => setImmediate(r));
  assert.equal(
    c.files.get(own + 'input-response.json'),
    previous,
    'late metadata cannot publish after Stop'
  );
  assert(blocked(c));
});
test('input read rejection returns a generic failure and releases the read slot', async () => {
  let reads = 0;
  const c = controller({
    inputQuery: () => {
      reads++;
      return Promise.reject(Error('PRIVATE pairing path'));
    }
  });
  for (const id of ['a', 'b']) {
    c.files.set(
      '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/input-request.json',
      JSON.stringify({
        id: id.repeat(32),
        method: 'inputStatus',
        expires: 6000
      })
    );
    c.advance(400);
    await new Promise((r) => setImmediate(r));
    const response = JSON.parse(
      c.files.get(
        '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/input-response.json'
      )
    );
    assert.equal(response.returnValue, false);
    assert(!JSON.stringify(response).includes('PRIVATE'));
  }
  assert.equal(reads, 2);
  assert(!blocked(c));
});

test('catalog broker reads through the unprivileged controller independently of inputs and Home', async () => {
  let resolve,
    reads = 0;
  const c = controller({
    inputQuery: (options) => {
      reads++;
      assert.deepEqual(JSON.parse(JSON.stringify(options)), { timeout: 3000 });
      return new Promise((r) => (resolve = r));
    }
  });
  const own =
    '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/';
  function request(id, extra = {}) {
    c.files.set(
      own + 'catalog-request.json',
      JSON.stringify({
        id: id.repeat(32),
        method: 'listApps',
        expires: 6000,
        ...extra
      })
    );
    c.advance(400);
  }
  request('a');
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 1);
  request('b');
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 1, 'in-flight catalog reads coalesce');
  c.files.set(
    own + 'home-request.json',
    JSON.stringify({ id: 'd'.repeat(32), method: 'homeStatus', expires: 6000 })
  );
  c.advance(400);
  assert.equal(
    JSON.parse(c.files.get(own + 'home-response.json')).enabled,
    true
  );
  resolve([{ id: 'org.example', title: 'Example' }]);
  await new Promise((r) => setImmediate(r));
  assert.equal(
    JSON.parse(c.files.get(own + 'catalog-response.json')).apps[0].id,
    'org.example'
  );
  assert.equal(
    JSON.parse(c.files.get(own + 'catalog-response.json')).id,
    'b'.repeat(32)
  );
  request('c', { method: 'setHomeControl', enabled: false });
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 1, 'catalog channel cannot mutate Home');
  request('e');
  await new Promise((r) => setImmediate(r));
  assert.equal(reads, 2);
  const previous = c.files.get(own + 'catalog-response.json');
  c.command('stop');
  c.advance(400);
  resolve([{ id: 'late', title: 'Late' }]);
  await new Promise((r) => setImmediate(r));
  assert.equal(c.files.get(own + 'catalog-response.json'), previous);
  assert(blocked(c));
});
test('catalog broker denial stays generic, releases its slot and never starts Helper', async () => {
  let reads = 0;
  const c = controller({
    inputQuery: () => {
      reads++;
      return Promise.reject(Error('PRIVATE key path'));
    }
  });
  const own =
    '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/';
  for (const id of ['a', 'b']) {
    c.files.set(
      own + 'catalog-request.json',
      JSON.stringify({ id: id.repeat(32), method: 'listApps', expires: 6000 })
    );
    c.advance(400);
    await new Promise((r) => setImmediate(r));
    const r = JSON.parse(c.files.get(own + 'catalog-response.json'));
    assert.equal(r.returnValue, false);
    assert(!JSON.stringify(r).includes('PRIVATE'));
  }
  assert.equal(reads, 2);
  assert.equal(c.workers.length, 1);
  assert(!blocked(c));
});

for (const terminal of ['EXIT 27\n', 'EXIT 30\n'])
  test(
    'catalog reply cannot escape terminal relay output ' + terminal.trim(),
    async () => {
      let resolve,
        reads = 0;
      const c = controller({
        inputQuery: () => {
          reads++;
          return new Promise((r) => (resolve = r));
        }
      });
      const own =
        '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control/';
      c.files.set(
        own + 'catalog-request.json',
        JSON.stringify({
          id: 'a'.repeat(32),
          method: 'listApps',
          expires: 6000
        })
      );
      c.advance(400);
      await new Promise((r) => setImmediate(r));
      assert.equal(reads, 1);
      c.workers[0].stdout.emit('data', Buffer.from(terminal));
      resolve([{ id: 'late', title: 'Late' }]);
      await new Promise((r) => setImmediate(r));
      assert(!c.files.has(own + 'catalog-response.json'));
      c.files.set(
        own + 'catalog-request.json',
        JSON.stringify({
          id: 'b'.repeat(32),
          method: 'listApps',
          expires: 6000
        })
      );
      c.advance(400);
      await new Promise((r) => setImmediate(r));
      assert.equal(
        reads,
        1,
        'terminal relay must not begin another catalog query'
      );
    }
  );

for (const state of [
  'Request Power Off',
  'Request Suspend',
  'Prepare Power Off'
])
  test(
    'confirmed evdev removal during ' +
      state +
      ' exits without persistent stop',
    () => {
      const c = controller();
      c.power({ state });
      assert(c.workers[0].writes.includes('T'));
      c.close(32);
      assert.equal(
        c.exit,
        undefined,
        'controller must survive same-boot standby'
      );
      assert(!blocked(c));
      assert.equal(
        c.cleanups.length,
        0,
        'closed vanished devices need no second cleanup'
      );
      assert.equal(
        c.workers.length,
        1,
        'do not restart against suspended input'
      );
    }
  );
for (const kind of [
  'no-power',
  'expired',
  'active',
  'signal',
  'missing-report',
  'emergency',
  'stop'
])
  test('power-removal exception refuses ' + kind, () => {
    const c = controller();
    if (kind !== 'no-power') c.power({ state: 'Prepare Power Off' });
    if (kind === 'expired') c.advance(15001);
    if (kind === 'active')
      c.power({ state: 'Active', processing: false, onOff: 'on' });
    if (kind === 'emergency') c.files.set(dir + 'blocked', 'explicit-stop');
    if (kind === 'stop') c.command('stop');
    c.close(
      32,
      kind === 'signal' ? 'SIGTERM' : null,
      c.workers[0],
      kind === 'missing-report' ? null : 32
    );
    if (c.cleanups.length) c.cleanup();
    assert(blocked(c));
    assert.equal(c.workers.length, 1);
  });
test('ordinary cleanup failure remains blocked even during power-off', () => {
  const c = controller();
  c.power({ state: 'Prepare Power Off' });
  c.close(31);
  c.cleanup();
  assert(blocked(c));
});

test('same-boot wake starts one new relay only after fresh Active and retains Home routing', () => {
  const c = controller();
  c.power({ state: 'Prepare Power Off' });
  c.close(32);
  c.launches.length = 0;
  c.advance(60000);
  assert.equal(c.workers.length, 1);
  assert.equal(c.exit, undefined);
  c.power({ state: 'Active', processing: true, onOff: 'on' });
  c.advance(1600);
  assert.equal(c.workers.length, 1);
  c.power({ state: 'Active', processing: false, onOff: 'on' });
  c.power({ state: 'Active', processing: false, onOff: 'on' });
  c.advance(1499);
  assert.equal(c.workers.length, 1);
  c.advance(1);
  assert.equal(c.workers.length, 2);
  c.workers[1].stdout.emit('data', Buffer.from('READY\n'));
  c.advance(400);
  assert(c.workers[1].writes.includes('E'));
  assert(c.launches.includes('com.gathin.tvhome'));
  assert(!blocked(c));
});
for (const kind of [
  'stop',
  'blocked',
  'watchdog',
  'off-again',
  'processing-again'
])
  test('wake while waiting for input respects ' + kind, () => {
    const c = controller();
    c.power({ state: 'Request Suspend' });
    c.close(32);
    c.power({ state: 'Active', processing: false, onOff: 'on' });
    if (kind === 'stop') c.command('stop');
    if (kind === 'blocked') c.files.set(dir + 'blocked', 'explicit-stop');
    if (kind === 'watchdog') c.files.set(dir + 'watchdog', 'stopped');
    if (kind === 'off-again') c.power({ state: 'Prepare Power Off' });
    if (kind === 'processing-again')
      c.power({ state: 'Active', processing: true, onOff: 'on' });
    c.advance(2000);
    assert.equal(c.workers.length, 1);
    if (kind === 'stop' || kind === 'blocked') assert(blocked(c));
    if (kind === 'watchdog') assert(c.files.has(dir + 'watchdog'));
  });

test('Home Off stays disabled after power-removal wake', () => {
  const c = controller();
  c.files.set(
    dir + 'home-request.json',
    JSON.stringify({
      id: 'a'.repeat(32),
      method: 'setHomeControl',
      enabled: false,
      expires: 6000
    })
  );
  c.advance(400);
  c.power({ state: 'Suspend' });
  c.close(32);
  c.launches.length = 0;
  c.power({ state: 'Active', onOff: 'on', processing: false });
  c.advance(1500);
  const w = c.workers[1];
  w.stdout.emit('data', Buffer.from('READY\nHOME\n'));
  c.advance(400);
  assert(w.writes.includes('D'));
  assert.equal(c.launches.length, 0);
  assert(!blocked(c));
});

test('power hint reaches a wake replacement before READY and removal waits for another wake', () => {
  const c = controller();
  c.power({ state: 'Suspend' });
  c.close(32);
  c.power({ state: 'Active', processing: false, onOff: 'on' });
  c.advance(1500);
  const w = c.workers[1];
  c.power({ state: 'Prepare Power Off' });
  assert(
    w.writes.includes('T'),
    'startup must receive the same bounded power hint'
  );
  c.close(32, null, w);
  assert(!blocked(c));
  assert.equal(c.exit, undefined);
  c.advance(2000);
  assert.equal(c.workers.length, 2);
  c.power({ state: 'Active', processing: false, onOff: 'on' });
  c.advance(1500);
  assert.equal(c.workers.length, 3);
});
test('mismatched relay exit logs safe original numeric facts before terminal cleanup', () => {
  const c = controller();
  c.close(99, null, c.workers[0], 20);
  const snapshot = c.logs.find((x) => x.event === 'contract-snapshot');
  const e = snapshot && { contract: snapshot.contract.events[0] };
  assert(e, 'unexpected lifecycle needs canonical diagnostic evidence');
  assert.equal(e.contract.actual.os_code, 99);
  assert.equal(e.contract.actual.reported_code, 20);
  c.cleanup();
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
test('unknown power processing retains truthy wake delay and emits metadata only', () => {
  const c = controller();
  c.power({ state: 'Suspend' });
  c.close(32);
  c.power({
    state: 'Active',
    processing: 'private-processing-marker',
    onOff: 'on'
  });
  c.advance(2000);
  assert.equal(c.workers.length, 1);
  const snapshot = c.logs.find((x) => x.event === 'contract-snapshot');
  const e = snapshot && { contract: snapshot.contract.events[0] };
  assert(e, 'unknown firmware value needs safe metadata');
  assert.equal(e.contract.field, 'processing');
  assert.equal(e.contract.actual.type, 'string');
  assert.equal(e.contract.actual.length, 25);
  assert(!JSON.stringify(e).includes('private-processing-marker'));
});

test('known terminal relay faults retain numeric outcome and cleanup failure safely', () => {
  const c = controller();
  c.close(31, null, c.workers[0], 31);
  let snapshots = c.logs.filter((x) => x.event === 'contract-snapshot');
  let events = snapshots[snapshots.length - 1].contract.events;
  assert(
    events.some((e) => e.actual.os_code === 31 && e.actual.reported_code === 31)
  );
  c.cleanup(11);
  snapshots = c.logs.filter((x) => x.event === 'contract-snapshot');
  events = snapshots[snapshots.length - 1].contract.events;
  assert(
    events.some((e) => e.operation === 'cleanup' && e.actual.os_code === 11)
  );
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
test('failed diagnostic emitter cannot prevent terminal input cleanup', () => {
  const c = controller();
  c.logs.push = function () {
    throw Error('PRIVATE');
  };
  c.close(31, null, c.workers[0], 31);
  c.cleanup();
  assert(blocked(c));
  assert.equal(c.workers.length, 1);
});
