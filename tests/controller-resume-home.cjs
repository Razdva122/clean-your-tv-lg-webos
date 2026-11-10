// Exercise the real controller with asynchronous Luna replies and a virtual clock.
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('fs'),
  vm = require('vm'),
  E = require('events');
const HOME = 'com.gathin.tvhome',
  LG = 'com.webos.app.home',
  COVER = 'com.webos.app.cpcover';
function controller({ automatic = true, blocked = false } = {}) {
  let now = 1000,
    seq = 0,
    worker,
    watch,
    requestId = 0;
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
            if (initialize) files.set(dir + 'control.json', '{}');
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
          watch = { fg, reset, power, log: l };
          return { close: reset };
        };
      return require('../native/app/' + n.slice(2));
    },
    process: {
      argv: ['node', 'app', JSON.stringify({ nativeHomeAuto: automatic })],
      pid: 1,
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
  calls[0].reply();
  worker.stdout.emit('data', Buffer.from('READY\n'));
  function resume() {
    watch.power({ state: 'Suspend' });
    watch.fg(COVER);
    watch.power({ state: 'Active' });
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
    command(cmd) {
      files.set(
        dir + 'control.json',
        JSON.stringify({
          cmd,
          nonce: (++requestId).toString(16).padStart(32, '0')
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
test('explicit LG visit cancels resume recovery for both controls', () => {
  for (const source of ['remote', 'settings']) {
    const c = controller();
    c.resume();
    c.calls[1].reply();
    if (source === 'remote')
      c.worker().stdout.emit('data', Buffer.from('LGHOME\n'));
    else c.rpc('openLGHome');
    assert.equal(c.calls.at(-1).id, LG);
    c.calls.at(-1).reply();
    c.fg(LG);
    c.advance(20000);
    assert.equal(c.homeCalls().length, 2);
  }
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
