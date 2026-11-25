// Exercise the real controller with asynchronous Luna replies and a virtual clock.
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('fs'),
  vm = require('vm'),
  E = require('events');
const HOME = 'com.gathin.tvhome',
  LG = 'com.webos.app.home',
  COVER = 'com.webos.app.cpcover';
function controller({
  automatic = true,
  blocked = false,
  initialControl = null,
  startedAt = 1000,
  pid = 1,
  startupForeground = (done) => done(LG),
  deferStartup = false
} = {}) {
  let now = startedAt,
    seq = 0,
    worker,
    watch,
    receiveWindows,
    requestId = 0,
    currentForeground;
  const timers = new Map(),
    files = new Map(),
    calls = [],
    logs = [];
  const dir =
    '/media/developer/apps/usr/palm/applications/com.local.nativehome/state/';
  if (blocked) files.set(dir + 'blocked', 'stopped');
  files.set(dir + 'apps.json', '["com.example.video"]');
  function schedule(fn, ms, repeat) {
    const id = ++seq;
    timers.set(id, { fn, at: now + ms, repeat });
    return id;
  }
  function advance(ms) {
    const end = now + ms;
    while (true) {
      let found;
      for (const entry of timers)
        if (entry[1].at <= end && (!found || entry[1].at < found[1].at))
          found = entry;
      if (!found) break;
      const [id, t] = found;
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
    renameSync: (a, b) => {
      files.set(b, files.get(a));
      files.delete(a);
    },
    chmodSync() {},
    unlinkSync: (p) => files.delete(p),
    appendFileSync: (p, s) => logs.push(JSON.parse(s)),
    readFileSync(p) {
      if (files.has(p)) return files.get(p);
      const e = Error('missing');
      e.code = 'ENOENT';
      throw e;
    }
  };
  function Service() {
    this.activityManager = { create() {} };
    this.call = (uri, p, cb) => {
      if (uri.endsWith('/launch')) {
        calls.push({
          id: p.id,
          at: now,
          reply: (ok = true) => cb({ payload: { returnValue: ok } })
        });
        return;
      }
      cb({
        payload: { returnValue: true, state: { enabled: true, schema: 3 } }
      });
    };
  }
  const context = {
    Buffer,
    Date: { now: () => now },
    require(n) {
      if (n === './home-control')
        return require('./storage-fixture.cjs').homeControl(fakefs);
      if (n === './state-permissions')
        return require('./storage-fixture.cjs').create(
          fakefs,
          (d, log, initialize) => {
            if (initialize)
              files.set(dir + 'control.json', initialControl || '{}');
            return true;
          }
        );
      if (n === 'fs') return fakefs;
      if (n === 'child_process')
        return {
          spawn() {
            worker = new E();
            worker.stdout = new E();
            worker.stderr = new E();
            worker.stdin = new E();
            worker.stdin.write = (c) => {
              if (c === 'P') worker.stdout.emit('data', Buffer.from('P\n'));
            };
            worker.stdin.end = () => {};
            worker.kill = () => {
              throw Error('unexpected watchdog');
            };
            return worker;
          }
        };
      if (n === '/usr/lib/node_modules/webos-service') return Service;
      if (n === './screen-watch')
        return (d, l, fg, reset, power) => {
          watch = {
            fg(id) {
              currentForeground = id;
              fg(id);
            },
            reset() {
              currentForeground = null;
              reset();
            },
            power,
            log: l
          };
          return {
            close: reset,
            foreground(done) {
              if (currentForeground === undefined) startupForeground(done);
              else done(currentForeground);
            },
            setForegroundDiagnostics(callback) {
              receiveWindows = callback;
            }
          };
        };
      return require('../native/app/' + n.slice(2));
    },
    process: {
      argv: ['node', 'app', JSON.stringify({ nativeHomeAuto: automatic })],
      pid: pid,
      getuid: () => 5431,
      hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1e6],
      on() {},
      exit(code) {
        throw { exit: code };
      }
    },
    setTimeout: (fn, ms) => schedule(fn, ms, 0),
    clearTimeout: (id) => timers.delete(id),
    setInterval: (fn, ms) => schedule(fn, ms, ms),
    clearInterval: (id) => timers.delete(id)
  };
  try {
    vm.runInNewContext(
      fs.readFileSync('native/app/native.js', 'utf8'),
      context
    );
  } catch (e) {
    if (e.exit === 0) return { calls, files, dir, blockedExit: true };
    throw e;
  }
  advance(automatic ? 0 : 1000);
  if (!deferStartup) {
    if (calls[0]) calls[0].reply();
    worker.stdout.emit('data', Buffer.from('READY\n'));
  }
  function resume() {
    watch.power({ state: 'Suspend' });
    watch.fg(COVER);
    watch.power({ state: 'Active' });
    // The current foreground query sees the source as the cover clears.
    // The subscription can still lag behind that query.
    currentForeground = 'com.webos.app.hdmi1';
    advance(400);
  }
  function rpc(method, enabled) {
    files.set(
      dir + 'home-request.json',
      JSON.stringify({
        id: (++requestId).toString(16).padStart(32, '0'),
        method,
        enabled,
        expires: now + 5000
      })
    );
    advance(400);
  }
  return {
    calls,
    logs,
    files,
    dir,
    advance,
    resume,
    rpc,
    fg: (id) => watch.fg(id),
    watchLog: (x) => watch.log(x),
    receiveWindows: () => receiveWindows,
    command(cmd, options = {}) {
      files.set(
        dir + 'control.json',
        JSON.stringify({
          cmd,
          nonce: (++requestId).toString(16).padStart(32, '0'),
          ...options
        })
      );
      advance(400);
    },
    power: (p) => watch.power(p),
    reset: () => watch.reset(),
    worker: () => worker,
    homeCalls: () => calls.filter((c) => c.id === HOME)
  };
}
test('LG Home arriving while resume launch is in flight is retried without another foreground event', () => {
  const c = controller();
  c.resume();
  c.advance(400);
  c.fg(LG);
  c.advance(800);
  assert.equal(c.homeCalls().length, 2, 'do not launch concurrently');
  c.calls[1].reply();
  c.advance(4800);
  assert.equal(c.homeCalls().length, 2, 'wait five seconds after reply');
  c.advance(400);
  assert.equal(c.homeCalls().length, 3);
  c.calls[2].reply();
  c.advance(5200);
  assert.equal(c.homeCalls().length, 4);
  c.calls[3].reply();
  c.advance(40000);
  assert.equal(c.homeCalls().length, 4, 'at most two retries');
});
test('LG Home must remain foreground for 1.5 seconds, including duplicate reports', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.advance(5200);
  c.fg(LG);
  c.advance(800);
  c.fg(LG);
  c.advance(400);
  assert.equal(c.homeCalls().length, 2);
  c.advance(400);
  assert.equal(c.homeCalls().length, 3);
});
test('blank and cpcover break continuous LG Home dwell', () => {
  for (const gap of ['', COVER]) {
    const c = controller();
    c.resume();
    c.calls[1].reply();
    c.advance(5200);
    c.fg(LG);
    c.advance(1200);
    c.fg(gap);
    c.advance(400);
    c.fg(LG);
    c.advance(1200);
    assert.equal(c.homeCalls().length, 2);
    c.advance(400);
    assert.equal(c.homeCalls().length, 3);
  }
});
test('successful return to Home suppresses retries but late LG takeover is recovered', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.fg(HOME);
  c.advance(6000);
  assert.equal(c.homeCalls().length, 2);
  c.fg(LG);
  c.advance(1600);
  assert.equal(c.homeCalls().length, 3);
});
test('a real app cancels recovery even if LG Home appears later', () => {
  const c = controller();
  c.resume();
  c.fg('netflix');
  c.calls[1].reply();
  c.fg(LG);
  c.advance(20000);
  assert.equal(c.homeCalls().length, 2);
});
test('a real app before the first resume tick cancels the pending launch', () => {
  const c = controller();
  c.power({ state: 'Suspend' });
  c.fg(COVER);
  c.power({ state: 'Active' });
  c.fg('netflix');
  c.advance(400);
  assert.equal(c.homeCalls().length, 1);
});
test('power off cancels recovery', () => {
  for (const p of [
    { onOff: 'off', state: 'Active' },
    { state: 'Suspend' },
    { state: 'Active Standby' }
  ]) {
    const c = controller();
    c.resume();
    c.calls[1].reply();
    c.fg(LG);
    c.power(p);
    c.advance(20000);
    assert.equal(c.homeCalls().length, 2);
  }
});
test('disabling Home control cancels recovery even after re-enabling it', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.fg(LG);
  c.rpc('setHomeControl', false);
  c.rpc('setHomeControl', true);
  c.advance(20000);
  assert.equal(c.homeCalls().length, 2);
});
test('a physical Back hold does not launch LG Home through the Helper', () => {
  const c = controller();
  c.worker().stdout.emit('data', Buffer.from('BACK_DOWN\nLGHOME\nBACK_UP\n'));
  assert.equal(c.calls.filter((call) => call.id === LG).length, 0);
});

test('a stock foreground transition during held Back stays with webOS', () => {
  const c = controller();
  c.fg('com.example.video');
  const launchCount = c.homeCalls().length;
  c.worker().stdout.emit('data', Buffer.from('BACK_DOWN\n'));
  c.advance(1200);
  c.fg(LG);
  c.worker().stdout.emit('data', Buffer.from('BACK_UP\n'));
  c.advance(12000);
  assert.equal(c.homeCalls().length, launchCount);
});

test('the explicit LG Home action still cancels resume recovery', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.rpc('openLGHome');
  assert.equal(c.calls.at(-1).id, LG);
  c.calls.at(-1).reply();
  c.fg(LG);
  c.advance(20000);
  assert.equal(c.homeCalls().length, 2);
});

test('guard expires after 30 seconds; duplicate Active does not extend it', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.advance(28000);
  c.power({ state: 'Active' });
  c.advance(2000);
  c.fg(LG);
  c.advance(8000);
  assert.equal(c.homeCalls().length, 2);
});
test('timeout settles a launch and late reply cannot bypass retry cooldown', () => {
  const c = controller();
  c.resume();
  c.fg(LG);
  c.advance(3200);
  c.calls[1].reply();
  c.advance(4400);
  assert.equal(c.homeCalls().length, 2);
  c.advance(400);
  assert.equal(c.homeCalls().length, 3);
});
test('screen watcher reset prevents retrying stale foreground data', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.fg(LG);
  c.reset();
  c.advance(6000);
  assert.equal(c.homeCalls().length, 2);
  c.fg(LG);
  c.advance(1200);
  assert.equal(c.homeCalls().length, 2);
  c.advance(400);
  assert.equal(c.homeCalls().length, 3);
});
test('new standby cycle gets a fresh bounded recovery window', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply();
  c.advance(32000);
  c.resume();
  c.calls[2].reply();
  c.fg(LG);
  c.advance(5200);
  assert.equal(c.homeCalls().length, 4);
});
test('automatic helper respects blocked marker; manual Home Helper still recovers', () => {
  const stopped = controller({ blocked: true });
  assert.equal(stopped.blockedExit, true);
  assert.equal(stopped.calls.length, 0);
  const manual = controller({ automatic: false, blocked: true });
  assert.equal(manual.files.has(manual.dir + 'blocked'), false);
  assert.equal(manual.calls[0].id, HOME);
});
test('restored Home skips the initial launch but still recovers a late LG takeover', () => {
  const c = controller();
  c.power({ state: 'Suspend' });
  c.fg(HOME);
  c.power({ state: 'Active' });
  c.advance(6000);
  assert.equal(c.homeCalls().length, 1);
  c.fg(LG);
  c.advance(1600);
  assert.equal(c.homeCalls().length, 2);
});
test('failed launch replies retain bounded recovery', () => {
  const c = controller();
  c.resume();
  c.calls[1].reply(false);
  c.fg(LG);
  c.advance(5200);
  assert.equal(c.homeCalls().length, 3);
  c.calls[2].reply(false);
  c.advance(5200);
  assert.equal(c.homeCalls().length, 4);
  c.calls[3].reply(false);
  c.advance(10000);
  assert.equal(c.homeCalls().length, 4);
});
test('disabled Home routing never arms recovery on resume', () => {
  const c = controller();
  c.rpc('setHomeControl', false);
  c.resume();
  c.fg(LG);
  c.advance(20000);
  assert.equal(c.homeCalls().length, 1);
});

test('app exit retries a late LG takeover with the same bounded recovery', () => {
  const c = controller();
  c.fg('com.example.video');
  c.fg(LG);
  assert.equal(c.homeCalls().length, 2);
  c.calls[1].reply();
  c.fg(HOME);
  c.fg(LG);
  c.advance(4800);
  assert.equal(c.homeCalls().length, 2);
  c.advance(400);
  assert.equal(c.homeCalls().length, 3);
  c.calls[2].reply();
  c.advance(5200);
  assert.equal(c.homeCalls().length, 4);
  c.calls[3].reply();
  c.advance(40000);
  assert.equal(c.homeCalls().length, 4);
});
test('new Back input cancels app-exit recovery so an intentional LG visit stays open', () => {
  const c = controller();
  c.fg('com.example.video');
  c.fg(LG);
  c.calls[1].reply();
  c.fg(HOME);
  c.worker().stdout.emit('data', Buffer.from('BACK_DOWN\n'));
  c.advance(800);
  c.fg(LG);
  c.worker().stdout.emit('data', Buffer.from('BACK_UP\n'));
  c.advance(12000);
  assert.equal(c.homeCalls().length, 2);
});

test('diagnostics captures Home, launch acknowledgement and foreground without changing routing', () => {
  const c = controller();
  c.fg(HOME);
  c.advance(2000);
  assert.equal(
    c.logs.some((x) => x.event === 'home-diagnostic'),
    false
  );
  c.command('diagnostics-start');
  assert.equal(c.logs.at(-1).event, 'home-diagnostic');
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  c.calls.at(-1).reply();
  c.fg(LG);
  c.advance(2000);
  const records = c.logs.filter((x) => x.event === 'home-diagnostic');
  assert.match(records[0].session, /^[a-f0-9]{32}$/);
  assert(records.every((x) => x.session === records[0].session));
  assert(records.some((x) => x.trigger === 'home' && x.homeSequence === 1));
  assert(records.some((x) => x.trigger === 'launch-request' && x.id === HOME));
  assert(
    records.some((x) => x.trigger === 'launch-result' && x.returnValue === true)
  );
  assert(
    records.some((x) => x.trigger === 'foreground' && x.foreground === LG)
  );
  assert(
    records.some(
      (x) =>
        x.trigger === 'sample' && x.foreground === LG && x.foregroundAgeMs > 0
    )
  );
  assert.equal(
    c.homeCalls().length,
    2,
    'diagnostics must not add launches or recovery'
  );
  c.advance(60000);
  assert(
    c.logs.some((x) => x.event === 'home-diagnostic' && x.trigger === 'expired')
  );
  const count = c.logs.filter((x) => x.event === 'home-diagnostic').length;
  c.advance(10000);
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  c.calls.at(-1).reply();
  assert.equal(
    c.logs.filter((x) => x.event === 'home-diagnostic').length,
    count
  );
});
test('diagnostics reports unavailable monitoring, clears stale foreground, stops and restarts', () => {
  const c = controller();
  c.fg(HOME);
  c.reset();
  c.watchLog({
    event: 'screen-watch-unavailable',
    reason: 'state-permissions'
  });
  c.command('diagnostics-start');
  let last = c.logs.at(-1);
  assert.equal(last.foreground, null);
  assert.equal(last.foregroundAgeMs, null);
  assert.equal(last.monitor, 'screen-watch-unavailable');
  assert.equal(last.monitorReason, 'state-permissions');
  c.command('diagnostics-stop');
  assert.equal(c.logs.at(-1).trigger, 'stopped');
  const count = c.logs.length;
  c.advance(2000);
  assert.equal(c.logs.length, count);
  c.command('diagnostics-start');
  assert.equal(c.logs.at(-1).trigger, 'started');
  c.watchLog({ event: 'screen-watch-connected' });
  c.fg(HOME);
  assert.equal(c.logs.at(-1).monitorReason, null);
  assert.equal(c.logs.at(-1).foreground, HOME);
});

test('the original diagnostic session records standby wake and the next app', () => {
  const c = controller();
  c.fg(HOME);
  c.command('diagnostics-start');
  c.power({ state: 'Suspend' });
  c.advance(12000);
  c.fg(COVER);
  c.power({ state: 'Active' });
  c.fg(LG);
  c.advance(1600);
  c.homeCalls().at(-1).reply();
  c.fg(HOME);
  c.fg('youtube.leanback.v4');
  c.advance(60000);

  const records = c.logs.filter((record) => record.event === 'home-diagnostic');
  assert.equal(records[0].trigger, 'started');
  assert.equal(records.at(-1).trigger, 'expired');
  assert(records.every((record) => record.session === records[0].session));
  assert(
    records.some(
      (record) => record.trigger === 'launch-request' && record.id === HOME
    )
  );
  assert(
    records.some(
      (record) =>
        record.trigger === 'foreground' &&
        record.foreground === 'youtube.leanback.v4'
    )
  );
});

test('restored recording observes startup before the first Home activation', () => {
  const request = {
    cmd: 'diagnostics-start',
    nonce: 'a'.repeat(32),
    expires: 180000
  };
  const c = controller({ initialControl: JSON.stringify(request) });
  const records = c.logs.filter((record) => record.event === 'home-diagnostic');
  assert.equal(records[0].trigger, 'resumed');
  assert(
    records.some(
      (record) => record.trigger === 'launch-request' && record.id === HOME
    )
  );
  assert(records.every((record) => record.session === request.nonce));
  c.fg('youtube.leanback.v4');
  c.advance(62000);
  assert(c.logs.some((record) => record.trigger === 'expired'));
});

test('standby longer than one minute keeps the wake recording bounded', () => {
  const c = controller({
    initialControl: JSON.stringify({
      cmd: 'diagnostics-start',
      nonce: 'b'.repeat(32),
      expires: 180000
    })
  });
  c.power({ state: 'Suspend' });
  c.advance(80000);
  assert.equal(
    c.logs.some((record) => record.trigger === 'expired'),
    false
  );
  c.power({ state: 'Active' });
  c.advance(400);
  c.homeCalls().at(-1).reply();
  c.fg('youtube.leanback.v4');
  c.advance(61000);
  const records = c.logs.filter((record) => record.event === 'home-diagnostic');
  assert(
    records.some(
      (record) => record.trigger === 'power' && record.powerState === 'Active'
    )
  );
  assert(records.some((record) => record.foreground === 'youtube.leanback.v4'));
  assert.equal(records.at(-1).trigger, 'expired');
});

test('one diagnostic request spans two Helper processes and expires once', () => {
  const request = {
    cmd: 'diagnostics-start',
    nonce: 'c'.repeat(32),
    expires: 180000
  };
  const before = controller({
    initialControl: JSON.stringify(request),
    pid: 11
  });
  before.fg(HOME);
  before.power({ state: 'Suspend' });
  before.reset();
  before.watchLog({ event: 'screen-watch-disconnected' });
  before.advance(4000);

  const after = controller({
    initialControl: before.files.get(before.dir + 'control.json'),
    startedAt: 85000,
    pid: 22
  });
  after.fg(HOME);
  after.fg('youtube.leanback.v4');
  after.advance(61000);
  const records = before.logs
    .concat(after.logs)
    .filter((record) => record.event === 'home-diagnostic');
  assert(records.every((record) => record.session === request.nonce));
  assert.deepEqual(
    [...new Set(records.map((record) => record.controllerPid))],
    [11, 22]
  );
  assert(
    records.some(
      (record) =>
        record.trigger === 'launch-request' && record.controllerPid === 22
    )
  );
  assert(
    records.some(
      (record) =>
        record.foreground === 'youtube.leanback.v4' &&
        record.controllerPid === 22
    )
  );
  assert.equal(
    records.filter((record) => record.trigger === 'expired').length,
    1
  );
});

test('an expired restored request never reopens diagnostic recording', () => {
  const c = controller({
    initialControl: JSON.stringify({
      cmd: 'diagnostics-start',
      nonce: 'd'.repeat(32),
      expires: 999
    })
  });
  c.advance(1000);
  assert.equal(
    c.logs.some((record) => record.event === 'home-diagnostic'),
    false
  );
});

test('installer TTL is converted to a TV-clock deadline once before acknowledgement', () => {
  const c = controller({ startedAt: 10000000 });
  c.command('diagnostics-start', { durationMs: 180000 });
  const request = JSON.parse(c.files.get(c.dir + 'control.json'));
  assert.equal(request.durationMs, undefined);
  assert.equal(request.expires, 10180400);
  const records = c.logs.filter((record) => record.event === 'home-diagnostic');
  assert.equal(records[0].trigger, 'started');
  c.advance(2000);
  assert.equal(
    c.logs.filter((record) => record.trigger === 'started').length,
    1
  );
});

test('monitor loss retains wake capture when the power subscription disconnects first', () => {
  const c = controller();
  c.command('diagnostics-start', { durationMs: 180000 });
  c.reset();
  c.watchLog({ event: 'screen-watch-disconnected' });
  c.advance(80000);
  assert.equal(
    c.logs.some((record) => record.trigger === 'expired'),
    false
  );
  c.fg('youtube.leanback.v4');
  c.advance(61000);
  assert(
    c.logs.some(
      (record) =>
        record.trigger === 'foreground' &&
        record.foreground === 'youtube.leanback.v4'
    )
  );
  assert.equal(
    c.logs.filter((record) => record.trigger === 'expired').length,
    1
  );
});

test('completed capture does not resume after Helper restarts without SSH', () => {
  const before = controller({ pid: 11 });
  before.command('diagnostics-start', { durationMs: 180000 });
  before.advance(61000);
  assert(before.logs.some((record) => record.trigger === 'expired'));

  const after = controller({
    initialControl: before.files.get(before.dir + 'control.json'),
    startedAt: 85000,
    pid: 22
  });
  assert.equal(
    after.logs.some((record) => record.event === 'home-diagnostic'),
    false
  );
});

test('late automatic Helper startup preserves YouTube despite stale Home subscription', () => {
  const c = controller({
    startupForeground: (done) => done('youtube.leanback.v4')
  });
  assert.equal(c.homeCalls().length, 0);
  c.advance(12000);
  assert.equal(c.homeCalls().length, 0);
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(c.homeCalls().length, 1);
});

test('startup keeps autolaunch for LG Home and cpcover and retains an already visible Home', () => {
  for (const [id, expected] of [
    [LG, 1],
    [COVER, 1],
    [HOME, 0]
  ]) {
    const c = controller({ startupForeground: (done) => done(id) });
    assert.equal(c.homeCalls().length, expected, id);
    assert(c.worker(), 'input worker starts');
  }
});

test('startup waits for a fresh reply when the paired screen connection is not ready', () => {
  let query = 0;
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => done(++query < 3 ? null : LG)
  });
  assert.equal(c.homeCalls().length, 0);
  c.advance(1000);
  assert.equal(c.homeCalls().length, 1);
});

test('startup stops waiting after a bounded unknown foreground without stealing an app', () => {
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => done(null)
  });
  c.advance(13000);
  assert.equal(c.homeCalls().length, 0);
  assert(c.worker(), 'Home input stays available');
});

test('Stop during the startup query prevents a late automatic launch', () => {
  let reply;
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => {
      reply = done;
    }
  });
  c.files.set(c.dir + 'control.json', JSON.stringify({ cmd: 'stop' }));
  c.advance(400);
  reply(LG);
  assert.equal(c.homeCalls().length, 0);
});

test('a new foreground app during a delayed startup reply wins over the old reply', () => {
  let reply;
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => {
      reply = done;
    }
  });
  c.fg('youtube.leanback.v4');
  reply(LG);
  assert.equal(c.homeCalls().length, 0);
});

test('a stale Home subscription during startup cannot override a fresh YouTube reply', () => {
  let reply;
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => {
      reply = done;
    }
  });
  c.fg(LG);
  reply('youtube.leanback.v4');
  assert.equal(c.homeCalls().length, 0);
});

test('explicit manual startup keeps its requested Home launch without an automatic query', () => {
  let queries = 0;
  const c = controller({
    automatic: false,
    startupForeground: () => {
      queries++;
    }
  });
  assert.equal(c.homeCalls().length, 1);
  assert.equal(queries, 0);
});

test('monitor reset during an automatic query retires its old launch', () => {
  let reply;
  const c = controller({
    deferStartup: true,
    startupForeground: (done) => {
      reply = done;
    }
  });
  c.reset();
  reply(LG);
  assert.equal(c.homeCalls().length, 0);
  assert(c.worker(), 'Home input stays available after monitor reset');
});

test('foreground windows are timestamped and limited to the diagnostic session', () => {
  const c = controller();
  assert.equal(c.receiveWindows(), undefined);
  c.command('diagnostics-start');
  const receive = c.receiveWindows();
  const windows = [
    { appId: 'youtube.leanback.v4', windowType: '_WEBOS_WINDOW_TYPE_CARD' },
    { appId: 'com.webos.app.fullhome', windowType: '_WEBOS_WINDOW_TYPE_HOME' }
  ];
  receive([
    { ...windows[0], windowId: 'not-exported' },
    windows[1],
    { appId: '192.0.2.5 / invalid', windowType: '_WEBOS_WINDOW_TYPE_CARD' }
  ]);
  const record = c.logs.at(-1);
  assert.equal(record.trigger, 'foreground-windows');
  assert.equal(record.time, c.logs.find((x) => x.trigger === 'started').time);
  assert.deepEqual(record.windows, windows);
  assert.equal(c.homeCalls().length, 1);
  c.advance(61000);
  assert.equal(c.receiveWindows(), null);
  receive(windows);
  assert.equal(c.logs.at(-1).trigger, 'expired');

  const restored = controller({
    initialControl: JSON.stringify({
      cmd: 'diagnostics-start',
      nonce: 'b'.repeat(32),
      expires: 180000
    }),
    startedAt: 85000
  });
  restored.receiveWindows()(windows);
  assert.equal(restored.logs.at(-1).trigger, 'foreground-windows');
  assert.equal(restored.logs.at(-1).session, 'b'.repeat(32));
  restored.command('diagnostics-stop');
  assert.equal(restored.receiveWindows(), null);
});

function irPress(c) {
  c.worker().stdout.emit('data', Buffer.from('IRHOME\n'));
}
test('IR Home starts immediately when LG Home arrives during the delay', () => {
  const c = controller();
  c.fg('com.example.video');
  irPress(c);
  c.advance(300);
  c.fg(LG);
  assert.equal(c.homeCalls().length, 2);
  c.homeCalls()[1].reply();
  c.fg(HOME);
  c.advance(500);
  assert.equal(c.homeCalls().length, 2, 'cancel the original delay');
});
test('IR Home recovers the reported late LG takeover with bounded retries', () => {
  const c = controller();
  c.fg('youtube.leanback.v4');
  irPress(c);
  c.advance(802);
  c.advance(725);
  c.homeCalls()[1].reply();
  c.advance(1509);
  c.fg(HOME);
  c.advance(2118);
  c.fg(LG);
  c.advance(599);
  assert.equal(c.homeCalls().length, 2);
  c.advance(401);
  assert.equal(c.homeCalls().length, 3);
  c.homeCalls()[2].reply();
  c.fg(HOME);
  c.advance(400);
  c.fg(LG);
  c.advance(1000);
  assert.equal(c.homeCalls().length, 4, 'at most two guard retries');
  c.homeCalls()[3].reply();
  c.advance(20000);
  assert.equal(c.homeCalls().length, 4);
});
test('IR Home waits for a cold launch and accepts a delayed successful reply', () => {
  const c = controller();
  c.fg('youtube.leanback.v4');
  irPress(c);
  c.advance(700);
  c.fg(LG);
  c.advance(7000);
  assert.equal(c.homeCalls().length, 2, 'no concurrent relaunch');
  assert(!c.logs.some((x) => x.event === 'launch-timeout'));
  c.homeCalls()[1].reply();
  c.fg(HOME);
  c.advance(20000);
  assert.equal(c.homeCalls().length, 2);
});
test('manual Home timeout keeps the worker alive and allows a new press', () => {
  const c = controller();
  let ended = false;
  c.worker().stdin.end = () => {
    ended = true;
  };
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  c.advance(15100);
  assert.equal(ended, false);
  assert(c.logs.some((x) => x.event === 'home-launch-failed'));
  c.homeCalls()[1].reply();
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  assert.equal(c.homeCalls().length, 3);
});
test('IR guard cancels on user navigation, lifecycle changes and explicit stock Home', () => {
  for (const action of [
    (c) => c.fg('com.example.other'),
    (c) => c.worker().stdout.emit('data', Buffer.from('BACK_DOWN\n')),
    (c) => c.rpc('openLGHome'),
    (c) => {
      c.rpc('setHomeControl', false);
      c.rpc('setHomeControl', true);
    },
    (c) => c.power({ state: 'Suspend' }),
    (c) => c.reset(),
    (c) => c.worker().stdout.emit('data', Buffer.from('IR_LOST\n'))
  ]) {
    const c = controller();
    c.fg('youtube.leanback.v4');
    irPress(c);
    c.advance(700);
    c.homeCalls()[1].reply();
    c.fg(HOME);
    action(c);
    c.fg(LG);
    c.advance(12000);
    assert.equal(c.homeCalls().length, 2, action.toString());
  }
});
test('Magic Home does not arm the IR recovery guard', () => {
  const c = controller();
  c.fg('youtube.leanback.v4');
  c.worker().stdout.emit('data', Buffer.from('HOME\n'));
  c.homeCalls()[1].reply();
  c.fg(HOME);
  c.fg(LG);
  c.advance(12000);
  assert.equal(c.homeCalls().length, 2);
});
test('IR cold-load retry waits six seconds after request and expires at ten seconds', () => {
  const c = controller();
  c.fg('youtube.leanback.v4');
  irPress(c);
  c.advance(700);
  c.homeCalls()[1].reply();
  c.fg(LG);
  c.advance(5900);
  assert.equal(c.homeCalls().length, 2);
  c.advance(500);
  assert.equal(c.homeCalls().length, 3);
  c.homeCalls()[2].reply();
  c.advance(15000);
  assert.equal(c.homeCalls().length, 3, 'expiry prevents another cold retry');
});
test('IR recovery cancels when an in-flight request outlives emergency release', () => {
  const c = controller();
  c.fg('youtube.leanback.v4');
  irPress(c);
  c.advance(700);
  c.worker().stdout.emit('data', Buffer.from('EXIT 27\n'));
  c.homeCalls()[1].reply();
  c.fg(LG);
  c.advance(12000);
  assert.equal(c.homeCalls().length, 2);
});
