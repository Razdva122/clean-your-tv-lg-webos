const fs = require('fs'),
  vm = require('vm'),
  a = require('node:assert/strict'),
  E = require('events');
// Opt-in Stay on input at power-on (home-preference keepSource). Automatic boot
// already preserves a non-Home foreground; this covers standby wake.
const state =
    '/media/developer/apps/usr/palm/applications/com.local.nativehome/state',
  preference = state + '/home-control.json';
function run(saved, bootForeground, scenario) {
  let now = 1000,
    interval,
    watch,
    worker,
    foreground = bootForeground;
  const calls = [],
    logs = [],
    timeouts = [],
    files = {};
  if (saved !== undefined) files[preference] = JSON.stringify(saved);
  function Service() {
    this.register = () => {};
    this.activityManager = { create() {} };
    this.call = (uri, p, cb) => {
      if (uri.endsWith('/launch')) calls.push(p.id);
      cb({
        payload: { returnValue: true, state: { enabled: true, schema: 3 } }
      });
    };
  }
  const fakefs = {
    existsSync: (p) => p in files,
    writeFileSync(p, d) {
      if (/\/(home-control|home-(request|response))\.json$/.test(p))
        files[p] = String(d);
    },
    chmodSync() {},
    unlinkSync(p) {
      delete files[p];
    },
    readFileSync: (p) =>
      p in files
        ? files[p]
        : p.endsWith('/apps.json')
          ? '["com.example.video"]'
          : '{}',
    appendFileSync: (p, s) => logs.push(JSON.parse(s))
  };
  const child = () => {
    let c = new E();
    c.pid = 12;
    c.stdout = new E();
    c.stderr = new E();
    c.stdin = new E();
    c.stdin.write = (command) => {
      if (command === 'P') c.stdout.emit('data', Buffer.from('P\n'));
    };
    c.stdin.end = () => {};
    return c;
  };
  const context = {
    console,
    Buffer,
    require(name) {
      if (name === './home-control')
        return require('./storage-fixture.cjs').homeControl(fakefs);
      if (name === './state-permissions')
        return require('./storage-fixture.cjs').create(fakefs);
      if (name === 'fs') return fakefs;
      if (name === 'child_process')
        return {
          spawn() {
            return (worker = child());
          }
        };
      if (name === '/usr/lib/node_modules/webos-service') return Service;
      if (name === './screen-watch')
        return (d, l, fg, reset, power) => {
          watch = {
            fg(id) {
              foreground = id;
              fg(id);
            },
            reset,
            power,
            foreground(id) {
              foreground = id;
            }
          };
          return {
            close() {},
            foreground(done) {
              if (watch.nextForeground) {
                const read = watch.nextForeground;
                watch.nextForeground = null;
                read(done);
              } else done(foreground);
            }
          };
        };
      return require('../native/app/' + name.slice(2));
    },
    process: {
      argv: ['node', 'app', '{"nativeHomeAuto":true}'],
      pid: 1,
      getuid: () => 5431,
      hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1e6],
      on() {},
      exit() {
        throw Error('unexpected exit');
      }
    },
    setTimeout(fn, ms) {
      timeouts.push({ fn, ms });
      return 1;
    },
    clearTimeout() {},
    setInterval(fn) {
      interval = fn;
      return 2;
    },
    clearInterval() {}
  };
  vm.runInNewContext(
    fs.readFileSync(
      require('path').join(__dirname, '../native/app/native.js'),
      'utf8'
    ),
    context
  );
  timeouts.find((t) => t.ms === 0).fn();
  worker.stdout.emit('data', Buffer.from('READY\n'));
  scenario({
    watch,
    calls,
    logs,
    files,
    tick: () => interval(),
    advance: (ms) => (now += ms)
  });
}
const on = { enabled: true, keepSource: true },
  homeLaunches = (calls) =>
    calls.filter((id) => id === 'com.gathin.tvhome').length;

// Automatic boot is unchanged: a source in front stays, LG Home gets Home.
for (const [id, expected] of [
  ['com.webos.app.hdmi1', 0],
  ['com.webos.app.home', 1]
])
  for (const saved of [on, undefined])
    run(saved, id, (t) => a.equal(homeLaunches(t.calls), expected));

function wake(saved, id, afterActive) {
  let extra, logs;
  run(saved, 'com.webos.app.home', (t) => {
    t.watch.fg('com.gathin.tvhome');
    t.watch.power({ state: 'Active' });
    t.tick();
    const before = homeLaunches(t.calls);
    t.watch.power({ state: 'Active Standby' });
    t.watch.fg(id);
    t.watch.power({ state: 'Active' });
    if (afterActive) afterActive(t);
    else {
      for (let i = 0; i < 5; i++) {
        t.advance(400);
        t.tick();
      }
    }
    extra = homeLaunches(t.calls) - before;
    logs = t.logs;
  });
  return { extra, logs };
}
// With the preference, waking on an input source keeps it.
for (const id of [
  'com.webos.app.hdmi2',
  'com.webos.app.livetv',
  'com.webos.app.externalinput.av1'
]) {
  const r = wake(on, id);
  a.equal(r.extra, 0, id);
  a.ok(
    r.logs.some((l) => l.event === 'resume-preserved-source' && l.id === id)
  );
}
// A startup cover at the first read must not hide an input that arrives later.
for (const id of ['com.webos.app.hdmi2', 'com.webos.app.livetv']) {
  const r = wake(on, 'com.webos.app.cpcover', (t) => {
    t.advance(400);
    t.tick();
    t.watch.fg(id);
    t.advance(400);
    t.tick();
  });
  a.equal(r.extra, 0, 'do not launch over a late input: ' + id);
  a.ok(
    r.logs.some((l) => l.event === 'resume-preserved-source' && l.id === id)
  );
}

// LG Home can appear briefly while webOS switches to the actual input.
{
  const r = wake(on, 'com.webos.app.home', (t) => {
    t.advance(400);
    t.tick();
    t.watch.fg('com.webos.app.hdmi2');
    t.advance(400);
    t.tick();
  });
  a.equal(r.extra, 0, 'do not launch during a brief LG Home transition');
  a.ok(r.logs.some((l) => l.event === 'resume-preserved-source'));
}

// The app-exit redirect must also wait while firmware wakes from standby.
run(on, 'com.gathin.tvhome', (t) => {
  t.watch.power({ state: 'Active' });
  t.watch.fg('com.example.video');
  t.watch.power({ state: 'Active Standby' });
  t.watch.fg('com.webos.app.home');
  t.watch.power({ state: 'Active' });
  t.watch.fg('com.webos.app.hdmi2');
  t.advance(400);
  t.tick();
  a.equal(
    homeLaunches(t.calls),
    0,
    'the app-exit redirect must not cover HDMI'
  );
  a.ok(t.logs.some((l) => l.event === 'resume-preserved-source'));
});

// A fresh foreground query supersedes an input cached before wake.
a.equal(
  wake(on, 'com.webos.app.hdmi2', (t) => {
    t.watch.foreground('com.example.video');
    t.advance(400);
    t.tick();
  }).extra,
  1,
  'launch Home when the current app supersedes the cached HDMI'
);

// A newer subscription update wins over an in-flight query reply.
{
  const r = wake(on, 'com.webos.app.cpcover', (t) => {
    let reply;
    t.watch.nextForeground = (done) => {
      reply = done;
    };
    t.advance(400);
    t.tick();
    t.watch.fg('com.webos.app.hdmi2');
    reply('com.webos.app.home');
  });
  a.equal(r.extra, 0);
  a.ok(
    r.logs.some(
      (l) =>
        l.event === 'resume-preserved-source' && l.id === 'com.webos.app.hdmi2'
    )
  );
}

// A reply after another standby transition must not trigger a wake launch.
a.equal(
  wake(on, 'com.webos.app.cpcover', (t) => {
    let reply;
    t.watch.nextForeground = (done) => {
      reply = done;
    };
    t.advance(400);
    t.tick();
    t.watch.power({ state: 'Active Standby' });
    reply('com.example.video');
  }).extra,
  0
);

// Without a confirmed screen, expire without launching over a possible input.
for (const unknown of [null, 'com.webos.app.cpcover']) {
  const r = wake(on, 'com.webos.app.home', (t) => {
    t.watch.foreground(unknown);
    for (let i = 0; i < 30; i++) {
      t.advance(400);
      t.tick();
    }
  });
  a.equal(r.extra, 0);
  a.ok(r.logs.some((l) => l.event === 'resume-foreground-unavailable'));
}

// LG Home and ordinary apps still open Home on wake.
for (const id of [
  'com.webos.app.home',
  'com.example.video',
  'com.webos.app.hdmi'
])
  a.equal(wake(on, id).extra, 1, id);
// Default and explicit off keep the previous wake behavior.
for (const saved of [
  undefined,
  { enabled: true },
  { enabled: true, keepSource: false }
])
  for (const id of ['com.webos.app.hdmi2', 'com.webos.app.livetv'])
    a.equal(wake(saved, id).extra, 1, JSON.stringify(saved) + ' ' + id);
// Home control off: no wake launch either way.
a.equal(
  wake({ enabled: false, keepSource: true }, 'com.webos.app.home').extra,
  0
);

// Settings: homeStatus reports the preference and setKeepSource persists it in
// the existing home-preference record without changing routing.
{
  let n = 0;
  run(undefined, 'com.webos.app.home', (t) => {
    function rpc(method, extra) {
      const id = (++n).toString(16).padStart(32, '0');
      t.files[state + '/home-request.json'] = JSON.stringify(
        Object.assign({ id, method, expires: Date.now() + 5000 }, extra)
      );
      t.tick();
      const r = JSON.parse(t.files[state + '/home-response.json']);
      a.equal(r.id, id);
      return r;
    }
    let r = rpc('homeStatus');
    a.equal(r.keepSource, false);
    a.equal(r.enabled, true);
    r = rpc('setKeepSource', { enabled: true });
    a.deepEqual([r.returnValue, r.enabled, r.keepSource], [true, true, true]);
    a.deepEqual(JSON.parse(t.files[preference]), on);
    a.equal(rpc('homeStatus').keepSource, true);
    a.ok(t.logs.some((l) => l.event === 'keep-source' && l.enabled === true));
    // Changing Home routing retains the preference.
    a.equal(rpc('setHomeControl', { enabled: false }).enabled, false);
    a.deepEqual(JSON.parse(t.files[preference]), {
      enabled: false,
      keepSource: true
    });
    a.equal(rpc('setHomeControl', { enabled: true }).enabled, true);
    a.equal(rpc('setKeepSource', { enabled: 'false' }).returnValue, false);
    a.equal(rpc('homeStatus').keepSource, true);
    a.equal(rpc('setKeepSource', { enabled: false }).keepSource, false);
    // Off is stored as the original record shape.
    a.equal(t.files[preference], '{"enabled":true}');
  });
}
console.log(
  'PASS: Stay on input at power-on keeps HDMI/Live TV on wake, opens Home otherwise, default unchanged'
);
